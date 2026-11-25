"""Boucle de simulation : physique, thermostat, profil de Text et enregistrement."""

import math
from dataclasses import asdict, dataclass, field

import numpy as np

from . import physique
from .regulation import ThermostatTOR

PAS_MAX = 10.0  # s, pour que le thermostat réagisse assez souvent
INTERVALLE_ENREGISTREMENT = 60.0  # s
EPSILON_TEMPS = 1e-6  # s


@dataclass
class Parametres:
    """Paramètres réglables d'une simulation (valeurs par défaut réalistes)."""

    puissance_radiateur: float = 1000.0  # W par radiateur
    consigne: float = 20.0  # Tc (°C)
    hysteresis: float = 0.5  # °C
    temperature_initiale: float = 16.0  # °C
    h: float = 2.0  # W/(m2.K), coefficient global façade (mur + fenêtre)
    surface_facade: float = 10.0  # m2
    occupants: int = 1
    diffusivite: float = 0.01  # m2/s, diffusivité effective du milieu équivalent
    inertie: float = 5.0  # capacité réelle / capacité de l'air seul

    def en_dict(self):
        return asdict(self)


@dataclass
class Bilan:
    """Énergies cumulées depuis le début (J) et durée de chauffe (s)."""

    radiateurs: float = 0.0
    occupants: float = 0.0
    pertes: float = 0.0
    duree_chauffe: float = 0.0


@dataclass
class Historique:
    """Séries enregistrées toutes les minutes.

    Les puissances et la fraction de marche sont des moyennes sur la minute
    qui se termine à l'instant indiqué. L'intégrale des puissances redonne
    donc exactement l'énergie du bilan.
    """

    temps: list = field(default_factory=list)
    t_ext: list = field(default_factory=list)
    t_moyenne: list = field(default_factory=list)
    t_min: list = field(default_factory=list)
    t_max: list = field(default_factory=list)
    fraction_marche: list = field(default_factory=list)
    puissance_radiateurs: list = field(default_factory=list)
    puissance_pertes: list = field(default_factory=list)
    energie_radiateurs: list = field(default_factory=list)

    def colonnes(self):
        return asdict(self)


def pas_divisant(dt_max, intervalle):
    """Plus grand pas <= dt_max qui divise exactement l'intervalle."""
    return intervalle / math.ceil(intervalle / dt_max)


class Simulation:
    def __init__(self, grille, parametres, profil):
        self.grille = grille
        self.parametres = parametres
        self.profil = profil
        self.temps = 0.0
        self.bilan = Bilan()
        self.historique = Historique()
        self.instant_consigne_atteinte = None
        self._preparer_constantes()
        self.temperature = np.full(grille.forme, float(parametres.temperature_initiale))
        self.thermostat = ThermostatTOR(parametres.consigne, parametres.hysteresis)
        self._demarrer()

    def _preparer_constantes(self):
        p, g = self.parametres, self.grille
        self.capacite = physique.capacite_maille(g, p.inertie)
        self.conductance = physique.conductance_facade(g, p.h, p.surface_facade)
        self.liaisons = physique.liaisons_voisins(g.air)
        self.coef_diffusion = p.diffusivite / g.pas ** 2
        self.apport_occupants = physique.puissance_occupants(g, p.occupants)
        self.dt = self._calculer_pas_de_temps()

    def _calculer_pas_de_temps(self):
        dt_stable = physique.pas_de_temps_stable(
            self.parametres.diffusivite, self.grille.pas, self.conductance.max(),
            self.capacite, physique.nombre_voisins_max(self.liaisons),
        )
        return pas_divisant(min(dt_stable, PAS_MAX), INTERVALLE_ENREGISTREMENT)

    def _demarrer(self):
        """État initial : thermostat, consigne déjà atteinte ou non, premier point."""
        self.thermostat.initialiser(self.temperature_moyenne)
        self._verifier_consigne()
        self._dernier_enregistrement = (0.0, Bilan())
        self._enregistrer_point(self._puissances_instantanees())

    # Grandeurs courantes

    @property
    def temperature_moyenne(self):
        return physique.temperature_moyenne(self.temperature, self.grille.air)

    @property
    def t_ext(self):
        return self.profil.temperature(self.temps)

    def energie_stockee(self):
        """Énergie gagnée par l'air depuis le début (J)."""
        return physique.energie_stockee(self.temperature, self.grille.air, self.capacite,
                                        self.parametres.temperature_initiale)

    # Avancement

    def avancer(self, duree):
        """Avance la simulation de ``duree`` secondes."""
        fin = self.temps + duree
        while self.temps < fin - EPSILON_TEMPS:
            self.pas(min(self.dt, fin - self.temps))

    def pas(self, dt):
        """Un pas de temps : thermostat, bilan, nouvelle température, enregistrement."""
        allume = self.thermostat.mettre_a_jour(self.temperature_moyenne)
        radiateurs, pertes = self._cartes_puissance(allume)
        self._cumuler_bilan(radiateurs.sum(), pertes.sum(), dt, allume)
        sources = radiateurs + self.apport_occupants - pertes
        self.temperature = physique.avancer_temperature(
            self.temperature, self.liaisons, dt, self.coef_diffusion, sources, self.capacite)
        self.temps += dt
        self._verifier_consigne()
        self._enregistrer_si_besoin()

    def _cartes_puissance(self, allume):
        """Cartes (W par maille) des radiateurs et des pertes à l'instant courant."""
        radiateurs = physique.puissance_radiateurs(self.grille, self.parametres.puissance_radiateur, allume)
        pertes = physique.puissance_pertes(self.temperature, self.conductance, self.t_ext)
        return radiateurs, pertes

    def _cumuler_bilan(self, p_radiateurs, p_pertes, dt, allume):
        self.bilan.radiateurs += p_radiateurs * dt
        self.bilan.occupants += self.apport_occupants.sum() * dt
        self.bilan.pertes += p_pertes * dt
        self.bilan.duree_chauffe += dt if allume else 0.0

    def _verifier_consigne(self):
        atteinte = self.temperature_moyenne >= self.parametres.consigne
        if self.instant_consigne_atteinte is None and atteinte:
            self.instant_consigne_atteinte = self.temps

    def cloturer(self):
        """Enregistre l'état final s'il ne tombe pas sur une minute ronde."""
        debut, _ = self._dernier_enregistrement
        if self.temps - debut > EPSILON_TEMPS:
            self._enregistrer_point(self._puissances_moyennes())

    # Enregistrement

    def _enregistrer_si_besoin(self):
        debut, _ = self._dernier_enregistrement
        if self.temps - debut >= INTERVALLE_ENREGISTREMENT - EPSILON_TEMPS:
            self._enregistrer_point(self._puissances_moyennes())

    def _puissances_instantanees(self):
        """(P radiateurs, P pertes, fraction de marche) à l'instant courant."""
        radiateurs, pertes = self._cartes_puissance(self.thermostat.allume)
        return float(radiateurs.sum()), float(pertes.sum()), float(self.thermostat.allume)

    def _puissances_moyennes(self):
        """(P radiateurs, P pertes, fraction de marche) moyennes depuis le dernier point."""
        debut, bilan_debut = self._dernier_enregistrement
        duree = self.temps - debut
        return ((self.bilan.radiateurs - bilan_debut.radiateurs) / duree,
                (self.bilan.pertes - bilan_debut.pertes) / duree,
                (self.bilan.duree_chauffe - bilan_debut.duree_chauffe) / duree)

    def _enregistrer_point(self, puissances):
        h, air = self.historique, self.grille.air
        p_radiateurs, p_pertes, fraction = puissances
        h.temps.append(self.temps)
        h.t_ext.append(self.t_ext)
        h.t_moyenne.append(self.temperature_moyenne)
        h.t_min.append(float(self.temperature[air].min()))
        h.t_max.append(float(self.temperature[air].max()))
        h.fraction_marche.append(fraction)
        h.puissance_radiateurs.append(p_radiateurs)
        h.puissance_pertes.append(p_pertes)
        h.energie_radiateurs.append(self.bilan.radiateurs)
        self._dernier_enregistrement = (self.temps, Bilan(**asdict(self.bilan)))
