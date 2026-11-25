"""Courbes de fin de cycle (export PNG) et couleurs communes à l'interface."""

import numpy as np
from matplotlib.figure import Figure

from .unites import en_heures

COULEUR_INTERIEUR = "#8E2462"
COULEUR_EXTERIEUR = "#2B6CB0"
COULEUR_CONSIGNE = "#FF9900"
COULEUR_CHAUFFAGE = "#C0392B"


def heures(historique):
    return en_heures(np.asarray(historique.temps))


def tracer_temperatures(axe, historique, consigne, hysteresis):
    """Températures moyenne, min, max, extérieure et bande de consigne."""
    t = heures(historique)
    axe.fill_between(t, historique.t_min, historique.t_max, color=COULEUR_INTERIEUR, alpha=0.15,
                     label="Écart min/max dans la pièce")
    axe.plot(t, historique.t_moyenne, color=COULEUR_INTERIEUR, label="T moyenne pièce")
    axe.plot(t, historique.t_ext, color=COULEUR_EXTERIEUR, label="T extérieure")
    axe.axhline(consigne, color=COULEUR_CONSIGNE, linestyle="--", label="Consigne Tc")
    axe.axhspan(consigne - hysteresis, consigne + hysteresis, color=COULEUR_CONSIGNE, alpha=0.12)
    axe.set_ylabel("Température (°C)")
    axe.legend(loc="lower right", fontsize=8)
    axe.grid(alpha=0.3)


def tracer_puissances(axe, historique):
    """Puissance des radiateurs et pertes par la façade."""
    t = heures(historique)
    # Chaque valeur est la moyenne de la minute qui se termine à l'instant t.
    axe.step(t, historique.puissance_radiateurs, where="pre", color=COULEUR_CHAUFFAGE,
             label="Puissance radiateurs")
    axe.plot(t, historique.puissance_pertes, color=COULEUR_EXTERIEUR, label="Pertes façade")
    axe.set_ylabel("Puissance (W)")
    axe.set_xlabel("Temps (h)")
    axe.legend(loc="upper right", fontsize=8)
    axe.grid(alpha=0.3)


def figure_cycle(historique, consigne, hysteresis, titre=""):
    """Figure à deux graphiques : températures en haut, puissances en bas."""
    figure = Figure(figsize=(10, 7), layout="constrained")
    haut, bas = figure.subplots(2, 1, sharex=True)
    tracer_temperatures(haut, historique, consigne, hysteresis)
    tracer_puissances(bas, historique)
    haut.set_title(titre)
    return figure
