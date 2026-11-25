"""Description de la pièce et construction du maillage.

La pièce est décrite dans un fichier TOML (voir le dossier ``pieces/``).
Ce module lit ce fichier, vérifie qu'il est cohérent et le transforme en
grille de mailles carrées.
Convention : un tableau ``T[j, i]`` a ``j`` selon y (sud vers nord)
et ``i`` selon x (ouest vers est).
"""

import math
import tomllib
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

COTES = ("nord", "sud", "est", "ouest")
TOLERANCE = 1e-6


@dataclass(frozen=True)
class Rectangle:
    nom: str
    x: float
    y: float
    largeur: float
    profondeur: float


@dataclass(frozen=True)
class Radiateur:
    nom: str
    x: float
    y: float


@dataclass(frozen=True)
class Fenetre:
    debut: float
    fin: float


@dataclass(frozen=True)
class Piece:
    nom: str
    largeur: float
    profondeur: float
    hauteur: float
    pas: float
    facade: str
    fenetres: tuple
    radiateurs: tuple
    obstacles: tuple
    poids_fenetre: float = 1.0

    @property
    def longueur_facade(self):
        return self.largeur if self.facade in ("nord", "sud") else self.profondeur

    @property
    def surface_facade(self):
        """Surface du mur extérieur (m²), valeur par défaut de S."""
        return self.longueur_facade * self.hauteur


@dataclass(frozen=True)
class Grille:
    """Maillage prêt pour le calcul."""

    pas: float
    hauteur: float
    air: np.ndarray
    facade: np.ndarray
    fenetre: np.ndarray
    radiateurs: tuple
    poids_fenetre: float

    @property
    def forme(self):
        return self.air.shape

    @property
    def nb_mailles_air(self):
        return int(self.air.sum())


# Lecture du fichier

def charger_piece(chemin):
    """Lit un fichier TOML et renvoie une Piece vérifiée."""
    with open(Path(chemin), "rb") as fichier:
        return piece_depuis_dict(tomllib.load(fichier))


def piece_depuis_dict(donnees):
    """Construit une Piece à partir d'un dictionnaire (contenu du TOML)."""
    piece = Piece(
        nom=donnees.get("nom", "Pièce"),
        largeur=float(donnees["largeur"]),
        profondeur=float(donnees["profondeur"]),
        hauteur=float(donnees["hauteur"]),
        pas=float(donnees.get("pas", 0.2)),
        facade=donnees["facade"],
        fenetres=tuple(Fenetre(float(f["debut"]), float(f["fin"])) for f in donnees.get("fenetres", [])),
        radiateurs=tuple(_lire_radiateur(r) for r in donnees.get("radiateurs", [])),
        obstacles=tuple(_lire_obstacle(o) for o in donnees.get("obstacles", [])),
        poids_fenetre=float(donnees.get("poids_fenetre", 1.0)),
    )
    verifier_piece(piece)
    return piece


def _lire_radiateur(donnees):
    return Radiateur(donnees.get("nom", "Radiateur"), float(donnees["x"]), float(donnees["y"]))


def _lire_obstacle(donnees):
    return Rectangle(donnees.get("nom", "Obstacle"), float(donnees["x"]), float(donnees["y"]),
                     float(donnees["largeur"]), float(donnees["profondeur"]))


# Vérifications

def verifier_piece(piece):
    """Lève ValueError si la description est incohérente."""
    verifier_dimensions(piece)
    verifier_radiateurs(piece)
    verifier_fenetres(piece)
    verifier_obstacles(piece)


def verifier_dimensions(piece):
    if piece.facade not in COTES:
        raise ValueError(f"Façade inconnue : {piece.facade!r} (choisir parmi {COTES})")
    if min(piece.largeur, piece.profondeur, piece.hauteur, piece.pas) <= 0:
        raise ValueError("Les dimensions et le pas doivent être positifs")
    if piece.poids_fenetre <= 0:
        raise ValueError("poids_fenetre doit être positif")
    for nom, longueur in (("largeur", piece.largeur), ("profondeur", piece.profondeur)):
        if not est_multiple(longueur, piece.pas):
            raise ValueError(f"La {nom} ({longueur} m) doit être un multiple du pas ({piece.pas} m)")


def verifier_radiateurs(piece):
    if not piece.radiateurs:
        raise ValueError("La pièce doit contenir au moins un radiateur")
    for radiateur in piece.radiateurs:
        if not point_dans_piece(piece, radiateur.x, radiateur.y):
            raise ValueError(f"{radiateur.nom} est en dehors de la pièce")


def verifier_fenetres(piece):
    for fenetre in piece.fenetres:
        if not 0 <= fenetre.debut < fenetre.fin <= piece.longueur_facade + TOLERANCE:
            raise ValueError(f"Fenêtre incohérente : début {fenetre.debut} m, fin {fenetre.fin} m")


def verifier_obstacles(piece):
    for obstacle in piece.obstacles:
        if min(obstacle.largeur, obstacle.profondeur) < piece.pas - TOLERANCE:
            raise ValueError(f"{obstacle.nom} est plus fin que le pas du maillage")


def est_multiple(longueur, pas):
    return abs(longueur / pas - round(longueur / pas)) < TOLERANCE


def point_dans_piece(piece, x, y):
    return 0 <= x <= piece.largeur and 0 <= y <= piece.profondeur


# Maillage

def nb_mailles(longueur, pas):
    """Nombre de mailles pour couvrir une longueur multiple du pas."""
    return int(round(longueur / pas))


def forme_grille(piece):
    """Forme (ny, nx) du maillage."""
    return nb_mailles(piece.profondeur, piece.pas), nb_mailles(piece.largeur, piece.pas)


def centres_mailles(nombre, pas):
    """Coordonnées des centres des mailles le long d'un axe."""
    return (np.arange(nombre) + 0.5) * pas


def masque_rectangle(piece, rectangle):
    """Mailles dont le centre est dans le rectangle."""
    ny, nx = forme_grille(piece)
    x = centres_mailles(nx, piece.pas)
    y = centres_mailles(ny, piece.pas)
    dans_x = (x >= rectangle.x) & (x <= rectangle.x + rectangle.largeur)
    dans_y = (y >= rectangle.y) & (y <= rectangle.y + rectangle.profondeur)
    return np.outer(dans_y, dans_x)


def masque_air(piece):
    """Mailles remplies d'air (la pièce moins les obstacles)."""
    air = np.ones(forme_grille(piece), dtype=bool)
    for obstacle in piece.obstacles:
        air &= ~masque_rectangle(piece, obstacle)
    return air


def masque_bord(forme, cote):
    """Mailles de la rangée collée au côté demandé."""
    bord = np.zeros(forme, dtype=bool)
    lignes = {"sud": (0, slice(None)), "nord": (-1, slice(None)),
              "ouest": (slice(None), 0), "est": (slice(None), -1)}
    bord[lignes[cote]] = True
    return bord


def abscisses_le_long_facade(piece):
    """Position des centres des mailles le long de la façade."""
    ny, nx = forme_grille(piece)
    nombre = nx if piece.facade in ("nord", "sud") else ny
    return centres_mailles(nombre, piece.pas)


def masque_fenetres(piece):
    """Mailles de façade situées devant une fenêtre."""
    position = abscisses_le_long_facade(piece)
    devant = np.zeros(position.shape, dtype=bool)
    for fenetre in piece.fenetres:
        devant |= (position >= fenetre.debut) & (position <= fenetre.fin)
    masque = np.zeros(forme_grille(piece), dtype=bool)
    masque[masque_bord(masque.shape, piece.facade)] = devant
    return masque


def indice_maille(piece, x, y):
    """Indices (j, i) de la maille qui contient le point (x, y), déjà vérifié dans la pièce."""
    ny, nx = forme_grille(piece)
    i = min(nx - 1, math.floor(x / piece.pas + TOLERANCE))
    j = min(ny - 1, math.floor(y / piece.pas + TOLERANCE))
    return j, i


def mailles_radiateurs(piece, air):
    """Indices des mailles des radiateurs, en vérifiant qu'elles sont dans l'air."""
    indices = []
    for radiateur in piece.radiateurs:
        j, i = indice_maille(piece, radiateur.x, radiateur.y)
        if not air[j, i]:
            raise ValueError(f"{radiateur.nom} est placé dans un obstacle")
        indices.append((j, i))
    return tuple(indices)


def zone_connectee(air, depart):
    """Mailles d'air reliées à la maille ``depart`` (parcours en largeur)."""
    vue = np.zeros_like(air)
    vue[depart] = True
    file = deque([depart])
    while file:
        j, i = file.popleft()
        for voisin in ((j + 1, i), (j - 1, i), (j, i + 1), (j, i - 1)):
            if _est_air_non_vu(air, vue, voisin):
                vue[voisin] = True
                file.append(voisin)
    return vue


def _est_air_non_vu(air, vue, maille):
    j, i = maille
    return 0 <= j < air.shape[0] and 0 <= i < air.shape[1] and air[j, i] and not vue[j, i]


def verifier_air_connecte(air):
    """Refuse une poche d'air isolée : elle fausserait la température moyenne."""
    depart = tuple(int(k) for k in np.argwhere(air)[0])
    if not (zone_connectee(air, depart) == air).all():
        raise ValueError("Les obstacles isolent une poche d'air : la pièce doit être d'un seul tenant")


def construire_grille(piece):
    """Transforme la description de la pièce en maillage de calcul."""
    air = masque_air(piece)
    if not air.any():
        raise ValueError("Les obstacles remplissent toute la pièce")
    verifier_air_connecte(air)
    facade = masque_bord(air.shape, piece.facade) & air
    if not facade.any():
        raise ValueError("Aucune maille d'air ne touche la façade")
    return Grille(pas=piece.pas, hauteur=piece.hauteur, air=air, facade=facade,
                  fenetre=masque_fenetres(piece) & air,
                  radiateurs=mailles_radiateurs(piece, air), poids_fenetre=piece.poids_fenetre)
