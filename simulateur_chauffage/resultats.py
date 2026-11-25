"""Indicateurs calculés à la fin d'un cycle."""

import numpy as np

from .unites import JOULES_PAR_KWH, SECONDES_PAR_HEURE, SECONDES_PAR_MINUTE


def resume_cycle(simulation, duree_cycle, nom_piece=""):
    """Dictionnaire des indicateurs d'un cycle, prêt à exporter."""
    if duree_cycle <= 0:
        raise ValueError("La durée du cycle doit être positive")
    return {
        **contexte_cycle(simulation, duree_cycle, nom_piece),
        **indicateurs_energie(simulation, duree_cycle),
        **indicateurs_temperature(simulation),
        **{f"param_{cle}": valeur for cle, valeur in simulation.parametres.en_dict().items()},
    }


def contexte_cycle(simulation, duree_cycle, nom_piece):
    return {"piece": nom_piece, "profil_text": simulation.profil.nom,
            "duree_cycle_h": duree_cycle / SECONDES_PAR_HEURE}


def indicateurs_energie(simulation, duree_cycle):
    bilan = simulation.bilan
    return {
        "temps_atteinte_tc_min": en_minutes(simulation.instant_consigne_atteinte),
        "energie_consommee_kwh": bilan.radiateurs / JOULES_PAR_KWH,
        "puissance_moyenne_w": bilan.radiateurs / duree_cycle,
        "taux_de_fonctionnement_pct": 100.0 * bilan.duree_chauffe / duree_cycle,
        "nb_demarrages": simulation.thermostat.demarrages,
        "energie_occupants_kwh": bilan.occupants / JOULES_PAR_KWH,
        "energie_pertes_kwh": bilan.pertes / JOULES_PAR_KWH,
        "ecart_bilan_energie_pct": ecart_bilan_pct(simulation),
    }


def indicateurs_temperature(simulation):
    historique = simulation.historique
    return {
        "t_moyenne_finale_c": simulation.temperature_moyenne,
        "t_moyenne_cycle_c": float(np.mean(historique.t_moyenne)),
        "t_ext_min_c": float(np.min(historique.t_ext)),
        "t_ext_max_c": float(np.max(historique.t_ext)),
    }


def en_minutes(secondes):
    """Convertit en minutes ; None reste None (consigne jamais atteinte)."""
    return None if secondes is None else secondes / SECONDES_PAR_MINUTE


def texte_atteinte(minutes):
    """Texte lisible pour le temps d'atteinte de Tc."""
    return "jamais" if minutes is None else f"{minutes:.0f} min"


def ecart_bilan_pct(simulation):
    """Écart relatif entre l'énergie stockée et (apports - pertes), en %.

    Doit rester proche de 0 : c'est un contrôle de cohérence du calcul.
    """
    bilan = simulation.bilan
    attendu = bilan.radiateurs + bilan.occupants - bilan.pertes
    echelle = max(bilan.radiateurs + bilan.occupants + bilan.pertes, 1.0)
    return 100.0 * (simulation.energie_stockee() - attendu) / echelle
