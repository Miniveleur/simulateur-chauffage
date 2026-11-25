"""Export d'un cycle : CSV (résumé et séries), classeur Excel avec courbes, PNG.

Les CSV utilisent le point-virgule et la virgule décimale pour s'ouvrir
directement dans Excel en français.
"""

import csv
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import Reference, ScatterChart, Series

from .graphiques import figure_cycle
from .unites import en_heures

NOMS_COLONNES = {
    "temps": "temps_s",
    "t_ext": "t_ext_c",
    "t_moyenne": "t_moyenne_c",
    "t_min": "t_min_c",
    "t_max": "t_max_c",
    "fraction_marche": "fraction_marche",
    "puissance_radiateurs": "puissance_radiateurs_w",
    "puissance_pertes": "pertes_facade_w",
    "energie_radiateurs": "energie_radiateurs_j",
}
NOM_JOURNAL = "tous_les_cycles.csv"


# Mise en forme

def format_francais(valeur):
    """Nombre avec virgule décimale, None en case vide, le reste tel quel."""
    if valeur is None:
        return ""
    if isinstance(valeur, float):
        return f"{valeur:.10g}".replace(".", ",")
    return valeur


def valeur_excel(valeur):
    return "" if valeur is None else valeur


# Dossiers

def creer_dossier_cycle(racine, instant=None):
    """Crée ``racine/cycle_AAAAMMJJ_HHMMSS`` (suffixé _2, _3... s'il existe déjà)."""
    base = Path(racine) / (instant or datetime.now()).strftime("cycle_%Y%m%d_%H%M%S")
    dossier, numero = base, 1
    while dossier.exists():
        numero += 1
        dossier = base.with_name(f"{base.name}_{numero}")
    dossier.mkdir(parents=True)
    return dossier


# CSV

def lignes_series(historique):
    """En-tête puis une ligne par instant enregistré."""
    colonnes = historique.colonnes()
    yield [NOMS_COLONNES[nom] for nom in colonnes]
    yield from zip(*colonnes.values())


def ecrire_csv(chemin, lignes, mode="w"):
    with open(chemin, mode, newline="", encoding="utf-8-sig") as fichier:
        ecrivain = csv.writer(fichier, delimiter=";")
        for ligne in lignes:
            ecrivain.writerow([format_francais(v) for v in ligne])


def ecrire_resume_csv(chemin, resume):
    ecrire_csv(chemin, [("indicateur", "valeur"), *resume.items()])


def lire_en_tete(chemin):
    with open(chemin, newline="", encoding="utf-8-sig") as fichier:
        return next(csv.reader(fichier, delimiter=";"), [])


def ajouter_au_journal(racine, resume):
    """Ajoute une ligne au CSV qui regroupe tous les cycles.

    Si les colonnes ont changé (nouvelle version du programme), l'ancien
    journal est renommé pour ne pas mélanger les colonnes.
    """
    chemin = Path(racine) / NOM_JOURNAL
    if chemin.exists() and lire_en_tete(chemin) != list(resume.keys()):
        chemin.rename(creer_nom_libre(chemin.with_name("tous_les_cycles_ancien.csv")))
    lignes = [resume.values()] if chemin.exists() else [resume.keys(), resume.values()]
    ecrire_csv(chemin, lignes, mode="a")


def creer_nom_libre(chemin):
    numero = 1
    candidat = chemin
    while candidat.exists():
        numero += 1
        candidat = chemin.with_name(f"{chemin.stem}_{numero}{chemin.suffix}")
    return candidat


# Excel

def feuille_resume(classeur, resume):
    feuille = classeur.active
    feuille.title = "Résumé"
    feuille.append(["Indicateur", "Valeur"])
    for cle, valeur in resume.items():
        feuille.append([cle, valeur_excel(valeur)])
    feuille.column_dimensions["A"].width = 34


def feuille_series(classeur, historique):
    """Feuille des séries, avec le temps en heures en première colonne."""
    feuille = classeur.create_sheet("Séries")
    lignes = lignes_series(historique)
    feuille.append(["temps_h", *next(lignes)])
    for ligne in lignes:
        feuille.append([en_heures(ligne[0]), *ligne])
    return feuille


def numero_colonne(champ):
    """Numéro de colonne Excel (A = 1) d'un champ de l'historique dans la feuille Séries."""
    return 2 + list(NOMS_COLONNES).index(champ)


def graphique_temps(feuille, titre, axe_y, champs):
    """Courbes en fonction du temps en heures (colonne A)."""
    graphique = ScatterChart()
    graphique.title, graphique.y_axis.title, graphique.x_axis.title = titre, axe_y, "Temps (h)"
    graphique.style, graphique.height, graphique.width = 13, 9, 22
    dernier = feuille.max_row
    temps = Reference(feuille, min_col=1, min_row=2, max_row=dernier)
    for champ in champs:
        valeurs = Reference(feuille, min_col=numero_colonne(champ), min_row=1, max_row=dernier)
        serie = Series(valeurs, temps, title_from_data=True)
        serie.marker.symbol = "none"
        graphique.series.append(serie)
    return graphique


def feuille_courbes(classeur, series):
    feuille = classeur.create_sheet("Courbes")
    feuille.add_chart(graphique_temps(series, "Températures", "°C", ["t_ext", "t_moyenne"]), "A1")
    feuille.add_chart(graphique_temps(series, "Puissances", "W",
                                      ["puissance_radiateurs", "puissance_pertes"]), "A20")


def ecrire_excel(chemin, resume, historique):
    classeur = Workbook()
    feuille_resume(classeur, resume)
    feuille_courbes(classeur, feuille_series(classeur, historique))
    classeur.save(chemin)


# PNG et ensemble

def titre_cycle(resume):
    return f"{resume['profil_text']}, {resume['duree_cycle_h']:.0f} h"


def ecrire_png(chemin, historique, parametres, titre):
    figure = figure_cycle(historique, parametres.consigne, parametres.hysteresis, titre)
    figure.savefig(chemin, dpi=120)


def exporter_cycle(racine, resume, historique, parametres):
    """Écrit tous les fichiers d'un cycle et renvoie le dossier créé."""
    dossier = creer_dossier_cycle(racine)
    ecrire_resume_csv(dossier / "resume.csv", resume)
    ecrire_csv(dossier / "series.csv", lignes_series(historique))
    ecrire_excel(dossier / "cycle.xlsx", resume, historique)
    ecrire_png(dossier / "courbes.png", historique, parametres, titre_cycle(resume))
    ajouter_au_journal(racine, resume)
    return dossier
