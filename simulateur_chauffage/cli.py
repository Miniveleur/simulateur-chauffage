"""Lancer un cycle sans interface, depuis un terminal.

Exemple :
    python -m simulateur_chauffage.cli --profil "Vague de froid 2300 m" --duree 48
"""

import argparse
from dataclasses import fields, replace
from pathlib import Path

from .cycle import executer_cycle, parametres_pour_piece
from .export import exporter_cycle
from .piece import charger_piece
from .profils import PROFILS
from .resultats import texte_atteinte
from .simulation import Parametres

PIECE_PAR_DEFAUT = Path(__file__).resolve().parent.parent / "pieces" / "chambre_type.toml"


def duree_positive(texte):
    duree = float(texte)
    if duree <= 0:
        raise argparse.ArgumentTypeError("la durée doit être positive")
    return duree


def creer_analyseur():
    analyseur = argparse.ArgumentParser(description="Simulation d'un cycle de chauffage")
    analyseur.add_argument("--piece", default=str(PIECE_PAR_DEFAUT), help="fichier TOML de la pièce")
    analyseur.add_argument("--profil", default=next(iter(PROFILS)), choices=list(PROFILS))
    analyseur.add_argument("--duree", type=duree_positive, default=24.0, help="durée du cycle en heures")
    analyseur.add_argument("--sortie", default="resultats", help="dossier des exports")
    for champ in fields(Parametres):
        aide = "par défaut : surface du mur de la pièce" if champ.name == "surface_facade" else None
        analyseur.add_argument(f"--{champ.name}", type=type(champ.default), default=None, help=aide)
    return analyseur


def parametres_depuis_arguments(arguments, piece):
    """Valeurs données en ligne de commande, sinon valeurs par défaut (S tirée de la pièce)."""
    parametres = parametres_pour_piece(piece)
    donnes = {c.name: getattr(arguments, c.name) for c in fields(Parametres)}
    return replace(parametres, **{nom: v for nom, v in donnes.items() if v is not None})


def afficher_resume(resume, dossier):
    print(f"Énergie consommée : {resume['energie_consommee_kwh']:.2f} kWh")
    print(f"Puissance moyenne : {resume['puissance_moyenne_w']:.0f} W")
    print(f"Tc atteinte après : {texte_atteinte(resume['temps_atteinte_tc_min'])}")
    print(f"Fichiers écrits dans {dossier}")


def main(argv=None):
    arguments = creer_analyseur().parse_args(argv)
    piece = charger_piece(arguments.piece)
    parametres = parametres_depuis_arguments(arguments, piece)
    simulation, resume = executer_cycle(piece, parametres, PROFILS[arguments.profil], arguments.duree)
    dossier = exporter_cycle(arguments.sortie, resume, simulation.historique, parametres)
    afficher_resume(resume, dossier)


if __name__ == "__main__":
    main()
