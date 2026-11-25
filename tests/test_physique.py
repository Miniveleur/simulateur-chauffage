import numpy as np
import pytest

from simulateur_chauffage import physique


def test_decaler_sans_bouclage():
    t = np.arange(6.0).reshape(2, 3)
    est = physique.decaler(t, (0, 1), -1.0)
    assert est.tolist() == [[1, 2, -1], [4, 5, -1]]
    nord = physique.decaler(t, (1, 0), -1.0)
    assert nord.tolist() == [[3, 4, 5], [-1, -1, -1]]


def test_diffusion_conserve_l_energie(grille):
    rng = np.random.default_rng(0)
    t = rng.normal(20, 3, grille.forme)
    somme = physique.somme_ecarts_voisins(t, physique.liaisons_voisins(grille.air))
    assert abs(somme[grille.air].sum()) < 1e-9
    assert (somme[~grille.air] == 0).all()


def test_champ_uniforme_ne_bouge_pas(grille):
    t = np.full(grille.forme, 18.0)
    liaisons = physique.liaisons_voisins(grille.air)
    nouveau = physique.avancer_temperature(t, liaisons, 1.0, 0.25, np.zeros(grille.forme), 1000.0)
    assert np.allclose(nouveau, 18.0)


def test_pas_de_flux_a_travers_un_obstacle():
    air = np.array([[True, False, True]])
    liaisons = physique.liaisons_voisins(air)
    somme = physique.somme_ecarts_voisins(np.array([[10.0, 0.0, 30.0]]), liaisons)
    assert somme.tolist() == [[0.0, 0.0, 0.0]]


def test_conductance_totale_vaut_hS(grille):
    g = physique.conductance_facade(grille, 2.0, 10.0)
    assert g.sum() == pytest.approx(20.0)
    assert (g[~grille.facade] == 0).all()


def test_occupants_100W_par_personne(grille):
    assert physique.puissance_occupants(grille, 3).sum() == pytest.approx(300.0)


def test_radiateurs_eteints_ne_chauffent_pas(grille):
    assert physique.puissance_radiateurs(grille, 1500, False).sum() == 0
    assert physique.puissance_radiateurs(grille, 1500, True).sum() == 1500


def _evolution_damier(dt_relatif, nb_pas=400):
    """Fait évoluer un damier (mode le plus instable) avec dt = dt_relatif * limite théorique."""
    air = np.ones((10, 10), dtype=bool)
    liaisons = physique.liaisons_voisins(air)
    a, pas = 0.01, 0.2
    limite = physique.pas_de_temps_stable(a, pas, 0.0, 1.0) / physique.MARGE_STABILITE
    t = 20 + (np.indices(air.shape).sum(axis=0) % 2 - 0.5)
    for _ in range(nb_pas):
        t = physique.avancer_temperature(t, liaisons, dt_relatif * limite, a / pas ** 2, np.zeros(air.shape), 1.0)
    return np.ptp(t)


def test_schema_stable_sous_la_limite():
    assert _evolution_damier(physique.MARGE_STABILITE) < 1.0


def test_schema_instable_au_dessus_de_la_limite():
    """Contrôle que la limite calculée est bien la vraie : 10 % au-dessus, ça diverge."""
    assert _evolution_damier(1.1) > 1e3


def test_pertes_loi_de_newton():
    g = np.array([[5.0, 0.0]])
    p = physique.puissance_pertes(np.array([[20.0, 20.0]]), g, -10.0)
    assert p.tolist() == [[150.0, 0.0]]


def test_fenetre_perd_plus_que_le_mur(piece):
    from dataclasses import replace

    from simulateur_chauffage.piece import construire_grille

    grille = construire_grille(replace(piece, poids_fenetre=4.0))
    g = physique.conductance_facade(grille, 2.0, 10.0)
    assert g.sum() == pytest.approx(20.0)
    assert g[grille.fenetre].min() == pytest.approx(4 * g[grille.facade & ~grille.fenetre].max())


def test_pas_de_temps_sans_diffusion_ni_pertes():
    assert physique.pas_de_temps_stable(0.0, 0.2, 0.0, 1000.0) == float("inf")


def test_deux_radiateurs_dans_la_meme_maille(grille):
    from dataclasses import replace

    double = replace(grille, radiateurs=grille.radiateurs * 2)
    assert physique.puissance_radiateurs(double, 1000, True).sum() == 2000
