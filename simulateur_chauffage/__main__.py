"""Lancer l'interface : python -m simulateur_chauffage [fichier_piece.toml]"""

import sys

import matplotlib.pyplot as plt

from .cli import PIECE_PAR_DEFAUT
from .interface import InterfaceSimulateur
from .piece import charger_piece


def main():
    chemin = sys.argv[1] if len(sys.argv) > 1 else PIECE_PAR_DEFAUT
    interface = InterfaceSimulateur(charger_piece(chemin))
    plt.show()
    return interface


if __name__ == "__main__":
    main()
