"""Déroulement d'un cycle complet, commun à l'interface et au terminal."""

from .piece import construire_grille
from .resultats import resume_cycle
from .simulation import Parametres, Simulation
from .unites import SECONDES_PAR_HEURE


def parametres_pour_piece(piece):
    """Paramètres par défaut avec la surface de façade de la pièce."""
    return Parametres(surface_facade=piece.surface_facade)


def verifier_duree(duree_h):
    if duree_h <= 0:
        raise ValueError("La durée du cycle doit être positive")


def terminer_cycle(simulation, duree_s, nom_piece):
    """Enregistre l'état final et renvoie le résumé du cycle."""
    simulation.cloturer()
    return resume_cycle(simulation, duree_s, nom_piece)


def executer_cycle(piece, parametres, profil, duree_h):
    """Simule un cycle complet d'un coup et renvoie (simulation, résumé)."""
    verifier_duree(duree_h)
    duree_s = duree_h * SECONDES_PAR_HEURE
    simulation = Simulation(construire_grille(piece), parametres, profil)
    simulation.avancer(duree_s)
    return simulation, terminer_cycle(simulation, duree_s, piece.nom)
