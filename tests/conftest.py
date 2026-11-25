import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulateur_chauffage.piece import charger_piece, construire_grille, piece_depuis_dict  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def dict_piece(**modifs):
    donnees = {
        "nom": "Test", "largeur": 2.0, "profondeur": 3.0, "hauteur": 2.5, "pas": 0.25,
        "facade": "nord", "fenetres": [{"debut": 0.5, "fin": 1.5}],
        "radiateurs": [{"nom": "R", "x": 1.0, "y": 2.8}],
        "obstacles": [{"nom": "Placard", "x": 0.0, "y": 0.0, "largeur": 0.5, "profondeur": 1.0}],
    }
    donnees.update(modifs)
    return donnees


@pytest.fixture
def piece():
    return piece_depuis_dict(dict_piece())


@pytest.fixture
def grille(piece):
    return construire_grille(piece)


@pytest.fixture
def chambre_type():
    return charger_piece(RACINE / "pieces" / "chambre_type.toml")
