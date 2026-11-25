import math

import numpy as np
import pytest

from simulateur_chauffage.physique import capacite_maille
from simulateur_chauffage.piece import construire_grille
from simulateur_chauffage.profils import PROFILS, profil_constant
from simulateur_chauffage.resultats import ecart_bilan_pct, resume_cycle
from simulateur_chauffage.simulation import INTERVALLE_ENREGISTREMENT, PAS_MAX, Parametres, Simulation


def capacite_totale(grille, parametres):
    return capacite_maille(grille, parametres.inertie) * grille.nb_mailles_air


def test_bilan_energie_ferme(grille):
    sim = Simulation(grille, Parametres(), PROFILS["Montagne 1800 m, temps clair"])
    sim.avancer(6 * 3600)
    assert abs(ecart_bilan_pct(sim)) < 1e-8


def test_refroidissement_exponentiel(grille):
    """Sans chauffage et avec un brassage fort, la pièce suit T = Text + (T0 - Text) exp(-hS t / C)."""
    p = Parametres(puissance_radiateur=0, occupants=0, diffusivite=0.05, temperature_initiale=20, consigne=5)
    sim = Simulation(grille, p, profil_constant(0.0))
    tau = capacite_totale(grille, p) / (p.h * p.surface_facade)
    duree = tau
    sim.avancer(duree)
    assert sim.temperature_moyenne == pytest.approx(20 * math.exp(-duree / tau), rel=0.02)


def test_temps_de_chauffe_proche_du_modele_global(grille):
    """Montée en température à pleine puissance : comparaison avec le modèle à une seule température."""
    p = Parametres(puissance_radiateur=1500, occupants=0, diffusivite=0.05, temperature_initiale=10, consigne=20)
    sim = Simulation(grille, p, profil_constant(0.0))
    sim.avancer(3 * 3600)
    hs, c = p.h * p.surface_facade, capacite_totale(grille, p)
    t_inf = 0.0 + p.puissance_radiateur / hs
    attendu = -c / hs * math.log((t_inf - 20) / (t_inf - 10))
    assert sim.instant_consigne_atteinte == pytest.approx(attendu, rel=0.05)


def test_thermostat_tient_la_bande(grille):
    p = Parametres()
    sim = Simulation(grille, p, profil_constant(-10.0))
    sim.avancer(8 * 3600)
    apres = np.array(sim.historique.t_moyenne)[np.array(sim.historique.temps) > sim.instant_consigne_atteinte]
    assert apres.min() > p.consigne - p.hysteresis - 0.05
    assert apres.max() < p.consigne + p.hysteresis + 0.05


def test_equilibre_avec_occupants_seuls(grille):
    """Régime établi sans chauffage : apports = pertes, donc 100 W = hS (Tfacade - Text)."""
    p = Parametres(puissance_radiateur=0, occupants=1, temperature_initiale=5, consigne=0, inertie=1)
    sim = Simulation(grille, p, profil_constant(0.0))
    sim.avancer(24 * 3600)
    assert sim.historique.puissance_pertes[-1] == pytest.approx(100.0, rel=0.01)


def test_pas_de_temps_et_enregistrement(grille):
    sim = Simulation(grille, Parametres(), profil_constant(0.0))
    sim.avancer(3600)
    assert 0 < sim.dt <= PAS_MAX
    assert sim.temps == pytest.approx(3600)
    ecarts = np.diff(sim.historique.temps)
    assert ecarts.min() >= INTERVALLE_ENREGISTREMENT - 1e-6
    assert ecarts.max() < INTERVALLE_ENREGISTREMENT + sim.dt + 1e-6


def test_resume_cycle(grille):
    sim = Simulation(grille, Parametres(), PROFILS["Redoux"])
    sim.avancer(24 * 3600)
    resume = resume_cycle(sim, 24 * 3600, "Test")
    assert resume["energie_consommee_kwh"] == pytest.approx(sim.bilan.radiateurs / 3.6e6)
    assert resume["puissance_moyenne_w"] == pytest.approx(resume["energie_consommee_kwh"] * 1000 / 24)
    assert resume["nb_demarrages"] >= 1
    assert resume["temps_atteinte_tc_min"] > 0


def test_consigne_jamais_atteinte(grille):
    sim = Simulation(grille, Parametres(puissance_radiateur=0, occupants=0), profil_constant(-10))
    sim.avancer(3600)
    assert resume_cycle(sim, 3600)["temps_atteinte_tc_min"] is None


def test_chambre_type_24h_rapide(chambre_type):
    """Ordre de grandeur réaliste pour la chambre type sur un jour froid."""
    sim = Simulation(construire_grille(chambre_type), Parametres(), PROFILS["Montagne 1800 m, temps clair"])
    sim.avancer(24 * 3600)
    kwh = sim.bilan.radiateurs / 3.6e6
    assert 5 < kwh < 20


def test_resultat_peu_sensible_au_maillage(chambre_type):
    """Diviser le pas par deux change peu l'énergie consommée (convergence du maillage)."""
    from dataclasses import replace

    energies = []
    for pas in (0.4, 0.2):
        grille = construire_grille(replace(chambre_type, pas=pas))
        sim = Simulation(grille, Parametres(), PROFILS["Montagne 1800 m, couvert"])
        sim.avancer(6 * 3600)
        energies.append(sim.bilan.radiateurs)
    assert energies[0] == pytest.approx(energies[1], rel=0.03)


def test_series_coherentes_avec_le_bilan(grille):
    """L'intégrale des puissances enregistrées redonne l'énergie du résumé."""
    sim = Simulation(grille, Parametres(), profil_constant(-10.0))
    sim.avancer(6 * 3600)
    h = sim.historique
    integrale = np.sum(np.diff(h.temps) * np.array(h.puissance_radiateurs[1:]))
    assert integrale == pytest.approx(sim.bilan.radiateurs, rel=1e-9)
    pertes = np.sum(np.diff(h.temps) * np.array(h.puissance_pertes[1:]))
    assert pertes == pytest.approx(sim.bilan.pertes, rel=1e-9)


def test_enregistrement_chaque_minute_ronde(grille):
    sim = Simulation(grille, Parametres(), profil_constant(0.0))
    sim.avancer(3600)
    assert np.allclose(sim.historique.temps, np.arange(61) * 60.0)


def test_etat_final_enregistre(grille):
    sim = Simulation(grille, Parametres(), profil_constant(0.0))
    sim.avancer(90)
    sim.cloturer()
    assert sim.historique.temps[-1] == pytest.approx(90)
    assert sim.historique.t_moyenne[-1] == sim.temperature_moyenne


def test_resultat_independant_du_pas_de_temps(grille):
    energies = []
    for diviseur in (1, 4):
        sim = Simulation(grille, Parametres(), profil_constant(-5.0))
        sim.dt /= diviseur
        sim.avancer(4 * 3600)
        energies.append(sim.bilan.radiateurs)
    assert energies[0] == pytest.approx(energies[1], rel=0.02)


def test_parametres_nuls(grille):
    p = Parametres(h=0.0, diffusivite=0.0, puissance_radiateur=0.0, occupants=0)
    sim = Simulation(grille, p, profil_constant(-10.0))
    sim.avancer(600)
    assert sim.temperature_moyenne == pytest.approx(p.temperature_initiale)


def test_duree_nulle_refusee(grille):
    sim = Simulation(grille, Parametres(), profil_constant(0.0))
    with pytest.raises(ValueError):
        resume_cycle(sim, 0)
