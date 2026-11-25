import csv

import pytest
from openpyxl import load_workbook

from simulateur_chauffage.export import exporter_cycle, format_francais
from simulateur_chauffage.profils import profil_constant
from simulateur_chauffage.resultats import resume_cycle
from simulateur_chauffage.simulation import Parametres, Simulation


def _cycle(grille, duree=7200):
    sim = Simulation(grille, Parametres(), profil_constant(-5))
    sim.avancer(duree)
    return sim, resume_cycle(sim, duree, "Test")


def test_format_francais():
    assert format_francais(1.5) == "1,5"
    assert format_francais(3) == 3
    assert format_francais("abc") == "abc"


def test_fichiers_exportes(tmp_path, grille):
    sim, resume = _cycle(grille)
    dossier = exporter_cycle(tmp_path, resume, sim.historique, sim.parametres)
    noms = sorted(f.name for f in dossier.iterdir())
    assert noms == ["courbes.png", "cycle.xlsx", "resume.csv", "series.csv"]
    assert (tmp_path / "tous_les_cycles.csv").exists()


def test_series_csv_lisible(tmp_path, grille):
    sim, resume = _cycle(grille)
    dossier = exporter_cycle(tmp_path, resume, sim.historique, sim.parametres)
    with open(dossier / "series.csv", encoding="utf-8-sig") as f:
        lignes = list(csv.reader(f, delimiter=";"))
    assert lignes[0][0] == "temps_s"
    assert len(lignes) == len(sim.historique.temps) + 1


def test_excel_contient_les_courbes(tmp_path, grille):
    sim, resume = _cycle(grille)
    dossier = exporter_cycle(tmp_path, resume, sim.historique, sim.parametres)
    classeur = load_workbook(dossier / "cycle.xlsx")
    assert classeur.sheetnames == ["Résumé", "Séries", "Courbes"]
    assert len(classeur["Courbes"]._charts) == 2


def test_journal_cumule(tmp_path, grille):
    for _ in range(2):
        sim, resume = _cycle(grille, 600)
        exporter_cycle(tmp_path, resume, sim.historique, sim.parametres)
    with open(tmp_path / "tous_les_cycles.csv", encoding="utf-8-sig") as f:
        assert len(f.readlines()) == 3


def test_dossiers_distincts_dans_la_meme_seconde(tmp_path):
    from datetime import datetime

    from simulateur_chauffage.export import creer_dossier_cycle

    instant = datetime(2026, 1, 1, 12, 0, 0)
    assert creer_dossier_cycle(tmp_path, instant) != creer_dossier_cycle(tmp_path, instant)


def test_resume_csv_relu(tmp_path, grille):
    sim, resume = _cycle(grille)
    dossier = exporter_cycle(tmp_path, resume, sim.historique, sim.parametres)
    with open(dossier / "resume.csv", encoding="utf-8-sig") as f:
        valeurs = dict(csv.reader(f, delimiter=";"))
    energie = float(valeurs["energie_consommee_kwh"].replace(",", "."))
    assert energie == pytest.approx(resume["energie_consommee_kwh"], rel=1e-9)


def test_journal_avec_nouvelles_colonnes(tmp_path, grille):
    from simulateur_chauffage.export import ajouter_au_journal

    ajouter_au_journal(tmp_path, {"a": 1})
    ajouter_au_journal(tmp_path, {"a": 1, "b": 2})
    assert (tmp_path / "tous_les_cycles_ancien.csv").exists()
    with open(tmp_path / "tous_les_cycles.csv", encoding="utf-8-sig") as f:
        assert f.readline().strip() == "a;b"


def test_series_excel_pointent_les_bonnes_colonnes(tmp_path, grille):
    sim, resume = _cycle(grille)
    dossier = exporter_cycle(tmp_path, resume, sim.historique, sim.parametres)
    feuille = load_workbook(dossier / "cycle.xlsx")["Séries"]
    assert feuille.cell(1, 4).value == "t_moyenne_c"
    assert feuille.cell(1, 8).value == "puissance_radiateurs_w"
