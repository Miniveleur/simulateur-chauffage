"""Constantes de conversion d'unités."""

SECONDES_PAR_HEURE = 3600.0
SECONDES_PAR_MINUTE = 60.0
JOULES_PAR_KWH = 3.6e6


def en_heures(secondes):
    """Convertit des secondes (nombre ou tableau numpy) en heures."""
    return secondes / SECONDES_PAR_HEURE
