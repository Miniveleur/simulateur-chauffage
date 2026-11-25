"""Équations thermiques sur le maillage (schéma explicite en volumes finis).

Chaque maille est une colonne d'air de section pas x pas et de hauteur h_piece.
Bilan sur une maille de capacité C (J/K) :

    C dT/dt = C a / pas^2 * somme(T_voisin - T) + P_radiateur + P_occupants - P_pertes

avec a la diffusivité effective de l'air (brassage par convection compris)
et P_pertes = g (T - Text) sur les mailles de façade. La conductance totale
vaut toujours h S. Elle est répartie sur les mailles de façade avec un poids 1
pour le mur et ``poids_fenetre`` devant une fenêtre (une fenêtre laisse passer
plus de chaleur qu'un mur isolé). Si un obstacle masque une partie de la
façade, h S est réparti sur les mailles d'air restantes.
Les murs autres que la façade sont adiabatiques (flux nul).

``a`` est la diffusivité du milieu équivalent (air brassé, meubles compris),
pas celle de l'air immobile.
"""

import numpy as np

MASSE_VOLUMIQUE_AIR = 1.2  # kg/m3
CAPACITE_MASSIQUE_AIR = 1005.0  # J/(kg.K)
PUISSANCE_PAR_OCCUPANT = 100.0  # W
MARGE_STABILITE = 0.9


def capacite_maille(grille, inertie):
    """Capacité thermique d'une maille (J/K).

    ``inertie`` multiplie la capacité de l'air seul pour tenir compte des
    meubles, du sol et des murs intérieurs qui stockent aussi la chaleur.
    """
    volume = grille.pas ** 2 * grille.hauteur
    return inertie * MASSE_VOLUMIQUE_AIR * CAPACITE_MASSIQUE_AIR * volume


def poids_facade(grille):
    """Poids de chaque maille dans la répartition des pertes (0 hors façade)."""
    poids = np.where(grille.facade, 1.0, 0.0)
    poids[grille.fenetre] = grille.poids_fenetre
    return poids


def conductance_facade(grille, h, surface):
    """Conductance (W/K) de chaque maille vers l'extérieur ; la somme vaut h S."""
    poids = poids_facade(grille)
    return h * surface * poids / poids.sum()


def liaisons_voisins(air):
    """Pour chaque direction, vrai si la maille et sa voisine sont toutes deux de l'air.

    Renvoie un dict direction -> (masque, décalage) où le décalage (dj, di)
    pointe vers la voisine.
    """
    decalages = {"est": (0, 1), "ouest": (0, -1), "nord": (1, 0), "sud": (-1, 0)}
    return {nom: (air & decaler(air, d, False), d) for nom, d in decalages.items()}


def decaler(tableau, decalage, remplissage):
    """Valeur de la voisine dans la direction ``decalage``, sans boucler aux bords."""
    dj, di = decalage
    resultat = np.full_like(tableau, remplissage)
    ny, nx = tableau.shape
    source = tableau[max(dj, 0):ny + min(dj, 0), max(di, 0):nx + min(di, 0)]
    resultat[max(-dj, 0):ny + min(-dj, 0), max(-di, 0):nx + min(-di, 0)] = source
    return resultat


def somme_ecarts_voisins(temperature, liaisons):
    """Somme sur les voisines d'air de (T_voisin - T). Nulle hors de l'air."""
    somme = np.zeros_like(temperature)
    for masque, decalage in liaisons.values():
        voisin = decaler(temperature, decalage, 0.0)
        somme += np.where(masque, voisin - temperature, 0.0)
    return somme


def nombre_voisins_max(liaisons):
    """Nombre maximal de voisines d'air d'une maille."""
    return int(sum(masque.astype(int) for masque, _ in liaisons.values()).max())


def pas_de_temps_stable(diffusivite, pas, conductance_max, capacite, nb_voisins=4):
    """Plus grand pas de temps (s) qui garde le schéma explicite stable.

    Condition : dt * (nb_voisins a / pas^2 + g / C) <= 1, avec une marge.
    Renvoie l'infini si rien ne limite le pas (pas de diffusion ni de pertes).
    """
    taux = nb_voisins * diffusivite / pas ** 2 + conductance_max / capacite
    return MARGE_STABILITE / taux if taux > 0 else float("inf")


def puissance_radiateurs(grille, puissance_unitaire, allume):
    """Carte des puissances des radiateurs (W par maille)."""
    carte = np.zeros(grille.forme)
    if allume:
        for j, i in grille.radiateurs:
            carte[j, i] += puissance_unitaire
    return carte


def puissance_occupants(grille, nb_occupants):
    """Apport des occupants réparti uniformément sur les mailles d'air (W par maille)."""
    total = nb_occupants * PUISSANCE_PAR_OCCUPANT
    return np.where(grille.air, total / grille.nb_mailles_air, 0.0)


def puissance_pertes(temperature, conductance, t_ext):
    """Pertes vers l'extérieur par la façade (W par maille), loi de Newton."""
    return conductance * (temperature - t_ext)


def avancer_temperature(temperature, liaisons, dt, coef_diffusion, sources, capacite):
    """Un pas explicite : renvoie la nouvelle carte de température.

    ``coef_diffusion`` = a / pas^2 ; ``sources`` = puissance nette par maille (W).
    """
    diffusion = coef_diffusion * somme_ecarts_voisins(temperature, liaisons)
    return temperature + dt * (diffusion + sources / capacite)


def temperature_moyenne(temperature, air):
    """Température moyenne de l'air (toutes les mailles ont le même volume)."""
    return float(temperature[air].mean())


def energie_stockee(temperature, air, capacite, reference):
    """Énergie (J) stockée dans l'air par rapport à une température de référence."""
    return float(capacite * (temperature[air] - reference).sum())
