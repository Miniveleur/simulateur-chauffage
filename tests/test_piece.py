import numpy as np
import pytest

from conftest import dict_piece
from simulateur_chauffage.piece import construire_grille, forme_grille, masque_bord, piece_depuis_dict


def test_forme_grille(piece):
    assert forme_grille(piece) == (12, 8)


def test_obstacle_retire_de_l_air(grille):
    # Placard 0,5 m x 1 m = 2 x 4 mailles dans le coin sud-ouest
    assert not grille.air[:4, :2].any()
    assert grille.nb_mailles_air == 12 * 8 - 8


def test_facade_nord_est_la_derniere_ligne(grille):
    assert grille.facade[-1].all()
    assert grille.facade.sum() == 8


def test_fenetre_sur_la_facade(grille):
    assert (grille.fenetre <= grille.facade).all()
    assert np.nonzero(grille.fenetre[-1])[0].tolist() == [2, 3, 4, 5]


def test_radiateur_dans_la_bonne_maille(grille):
    assert grille.radiateurs == ((11, 4),)


@pytest.mark.parametrize("cote, attendu", [("sud", (0, slice(None))), ("est", (slice(None), -1))])
def test_masque_bord(cote, attendu):
    bord = masque_bord((3, 4), cote)
    assert bord[attendu].all() and bord.sum() == bord[attendu].size


def test_facade_ouest_avec_fenetre():
    grille = construire_grille(piece_depuis_dict(dict_piece(facade="ouest", fenetres=[{"debut": 2.0, "fin": 3.0}])))
    assert grille.fenetre[:, 0].tolist() == [False] * 8 + [True] * 4


def test_radiateur_dans_obstacle_refuse():
    piece = piece_depuis_dict(dict_piece(radiateurs=[{"x": 0.2, "y": 0.2}]))
    with pytest.raises(ValueError, match="obstacle"):
        construire_grille(piece)


def test_facade_inconnue_refusee():
    with pytest.raises(ValueError, match="Façade"):
        piece_depuis_dict(dict_piece(facade="haut"))


def test_piece_sans_radiateur_refusee():
    with pytest.raises(ValueError, match="radiateur"):
        piece_depuis_dict(dict_piece(radiateurs=[]))


def test_chambre_type_se_charge(chambre_type):
    grille = construire_grille(chambre_type)
    assert grille.forme == (25, 20)
    assert grille.fenetre.any() and len(grille.radiateurs) == 1


def test_surface_facade_par_defaut(piece):
    assert piece.surface_facade == pytest.approx(2.0 * 2.5)


@pytest.mark.parametrize("modif, message", [
    ({"largeur": 2.1}, "multiple du pas"),
    ({"radiateurs": [{"x": 50.0, "y": -3.0}]}, "dehors"),
    ({"fenetres": [{"debut": 1.5, "fin": 0.5}]}, "Fenêtre"),
    ({"fenetres": [{"debut": 1.5, "fin": 9.0}]}, "Fenêtre"),
    ({"obstacles": [{"x": 0, "y": 1, "largeur": 0.1, "profondeur": 1}]}, "plus fin"),
    ({"poids_fenetre": 0}, "poids_fenetre"),
])
def test_descriptions_incoherentes_refusees(modif, message):
    with pytest.raises(ValueError, match=message):
        piece_depuis_dict(dict_piece(**modif))


def test_poche_d_air_isolee_refusee():
    mur = {"nom": "Mur", "x": 0.0, "y": 1.0, "largeur": 2.0, "profondeur": 0.25}
    with pytest.raises(ValueError, match="poche"):
        construire_grille(piece_depuis_dict(dict_piece(obstacles=[mur])))


def test_radiateur_sur_une_limite_de_maille():
    # 0,75 / 0,25 donne 2,9999... en flottant : la maille doit quand même être la n° 3
    grille = construire_grille(piece_depuis_dict(dict_piece(radiateurs=[{"x": 0.75, "y": 2.8}])))
    assert grille.radiateurs == ((11, 3),)
