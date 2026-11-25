"""Profils de température extérieure (Text) sur une journée, répétés jour après jour.

Forme classique d'une journée d'hiver : minimum peu après le lever du soleil
(vers 7 h), maximum en milieu d'après-midi (vers 15 h). La montée et la
descente suivent chacune une demi-sinusoïde.

Les valeurs sont des ordres de grandeur pour une station des Alpes du Nord
en janvier. Elles sont à ajuster avec de vraies données (Météo-France).
"""

import math
from dataclasses import dataclass

from .unites import SECONDES_PAR_HEURE


@dataclass(frozen=True)
class ProfilText:
    nom: str
    t_min: float
    t_max: float
    heure_min: float = 7.0
    heure_max: float = 15.0

    def __post_init__(self):
        if (self.heure_max - self.heure_min) % 24.0 == 0:
            raise ValueError("L'heure du minimum et celle du maximum doivent être différentes")

    def temperature(self, temps_s):
        """Text (°C) à l'instant ``temps_s`` compté depuis minuit du premier jour."""
        heure = (temps_s / SECONDES_PAR_HEURE) % 24.0
        return temperature_journaliere(heure, self.t_min, self.t_max, self.heure_min, self.heure_max)


def temperature_journaliere(heure, t_min, t_max, heure_min, heure_max):
    """Température à une heure donnée pour un cycle min/max sur 24 h."""
    fraction = fraction_montee(heure, heure_min, heure_max)
    if fraction is not None:
        return t_min + (t_max - t_min) * demi_sinus(fraction)
    fraction = fraction_montee(heure, heure_max, heure_min + 24.0)
    return t_max - (t_max - t_min) * demi_sinus(fraction)


def fraction_montee(heure, debut, fin):
    """Avancement (0 à 1) de ``heure`` dans l'intervalle [debut, fin[ modulo 24 h, ou None."""
    ecart = (heure - debut) % 24.0
    duree = (fin - debut) % 24.0
    if ecart < duree:
        return ecart / duree
    return None


def demi_sinus(fraction):
    """Passage doux de 0 à 1 quand ``fraction`` va de 0 à 1."""
    return 0.5 - 0.5 * math.cos(math.pi * fraction)


def profil_constant(temperature):
    """Profil plat, utile pour les tests et le réglage manuel."""
    return ProfilText("Constant", temperature, temperature)


PROFILS = {
    profil.nom: profil
    for profil in (
        ProfilText("Montagne 1800 m, temps clair", -14.0, -1.0),
        ProfilText("Montagne 1800 m, couvert", -7.0, -3.0),
        ProfilText("Vague de froid 2300 m", -22.0, -12.0),
        ProfilText("Redoux", -2.0, 6.0),
    )
}
