"""Partie affichage de l'interface : carte de température, courbes, ligne d'état."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle as Carre

from .graphiques import COULEUR_CHAUFFAGE, COULEUR_CONSIGNE, COULEUR_EXTERIEUR, COULEUR_INTERIEUR, heures
from .resultats import texte_atteinte
from .unites import JOULES_PAR_KWH, en_heures

COULEUR_ALLUME, COULEUR_ETEINT = "#FF3B30", "#FFFFFF"
COULEUR_MUR, COULEUR_FENETRE, COULEUR_OBSTACLE = "#1565C0", "#81D4FA", "#9E9E9E"
MARGE_COULEUR = 4.0  # °C autour des températures attendues


class Vue:
    def __init__(self, figure, piece, grille):
        self.figure, self.piece, self.grille = figure, piece, grille
        self._creer_carte()
        self._creer_courbes()
        self.texte_etat = figure.text(0.03, 0.965, "", fontsize=11, family="monospace", va="center")
        self.texte_message = figure.text(0.48, 0.04, "", fontsize=9, color="#333333")

    # Construction

    def _creer_carte(self):
        self.axe_carte = self.figure.add_axes((0.03, 0.40, 0.36, 0.53))
        self.image = self._creer_image()
        self.figure.colorbar(self.image, ax=self.axe_carte, label="Température (°C)", fraction=0.05)
        self.axe_carte.set_xlabel("x (m)")
        self.axe_carte.set_ylabel("y (m)")
        self._dessiner_bord(self.grille.facade, COULEUR_MUR, 4)
        self._dessiner_bord(self.grille.fenetre, COULEUR_FENETRE, 7)
        self.marques_radiateurs = [self._dessiner_radiateur(j, i) for j, i in self.grille.radiateurs]

    def _creer_image(self):
        ny, nx = self.grille.forme
        etendue = (0, nx * self.grille.pas, 0, ny * self.grille.pas)
        couleurs = plt.get_cmap("turbo").with_extremes(bad=COULEUR_OBSTACLE)
        return self.axe_carte.imshow(np.zeros((ny, nx)), origin="lower", extent=etendue,
                                     cmap=couleurs, interpolation="bilinear")

    def _dessiner_bord(self, masque, couleur, epaisseur):
        for j, i in zip(*np.nonzero(masque)):
            xs, ys = segment_bord(self.piece.facade, j, i, self.grille.pas)
            self.axe_carte.plot(xs, ys, color=couleur, linewidth=epaisseur, solid_capstyle="butt")

    def _dessiner_radiateur(self, j, i):
        pas = self.grille.pas
        carre = Carre((i * pas, j * pas), pas, pas, facecolor=COULEUR_ETEINT, edgecolor="black", linewidth=1.5)
        return self.axe_carte.add_patch(carre)

    def _creer_courbes(self):
        self.axe_temp = self.figure.add_axes((0.48, 0.62, 0.49, 0.31))
        self.axe_puiss = self.figure.add_axes((0.48, 0.40, 0.49, 0.17), sharex=self.axe_temp)
        self.ligne_tint, = self.axe_temp.plot([], [], color=COULEUR_INTERIEUR, label="T moyenne pièce")
        self.ligne_text, = self.axe_temp.plot([], [], color=COULEUR_EXTERIEUR, label="T extérieure")
        self.ligne_tc = self.axe_temp.axhline(20, color=COULEUR_CONSIGNE, linestyle="--", label="Consigne Tc")
        self.ligne_p, = self.axe_puiss.step([], [], where="pre", color=COULEUR_CHAUFFAGE, label="Radiateurs")
        self.ligne_pertes, = self.axe_puiss.plot([], [], color=COULEUR_EXTERIEUR, label="Pertes façade")
        habiller_axes(self.axe_temp, "Température (°C)")
        habiller_axes(self.axe_puiss, "Puissance (W)", "Temps (h)")

    # Mise à jour

    def montrer_apercu(self, parametres):
        """Pièce uniforme à la température initiale, courbes vides."""
        uniforme = np.full(self.grille.forme, parametres.temperature_initiale)
        self.image.set_data(masquer_obstacles(uniforme, self.grille.air))
        self.image.set_clim(*bornes_couleur(parametres))
        self.ligne_tc.set_ydata([parametres.consigne] * 2)
        self.colorer_radiateurs(False)
        self.vider_courbes()
        self.texte_etat.set_text(f"Pièce : {self.piece.nom}   |   prête, T initiale "
                                 f"{parametres.temperature_initiale:.1f} °C")

    def preparer_cycle(self, simulation, duree_s):
        """Règle les axes et les couleurs pour un nouveau cycle."""
        p = simulation.parametres
        t_ext = [simulation.profil.temperature(t) for t in np.linspace(0, duree_s, 200)]
        self.axe_temp.set_xlim(0, en_heures(duree_s))
        self.axe_temp.set_ylim(min(t_ext) - 2, max(p.temperature_initiale, p.consigne) + MARGE_COULEUR)
        self.axe_puiss.set_ylim(-50, puissance_max_attendue(simulation, min(t_ext)) * 1.1)
        self.image.set_clim(*bornes_couleur(p))
        self.ligne_tc.set_ydata([p.consigne] * 2)
        self.vider_courbes()

    def montrer_simulation(self, simulation):
        self.image.set_data(masquer_obstacles(simulation.temperature, self.grille.air))
        self.colorer_radiateurs(simulation.thermostat.allume)
        self._tracer_historique(simulation.historique)
        self.texte_etat.set_text(texte_etat(simulation))

    def colorer_radiateurs(self, allume):
        for marque in self.marques_radiateurs:
            marque.set_facecolor(COULEUR_ALLUME if allume else COULEUR_ETEINT)

    def vider_courbes(self):
        for ligne in (self.ligne_tint, self.ligne_text, self.ligne_p, self.ligne_pertes):
            ligne.set_data([], [])

    def _tracer_historique(self, historique):
        t = heures(historique)
        self.ligne_tint.set_data(t, historique.t_moyenne)
        self.ligne_text.set_data(t, historique.t_ext)
        self.ligne_p.set_data(t, historique.puissance_radiateurs)
        self.ligne_pertes.set_data(t, historique.puissance_pertes)

    def afficher_message(self, texte):
        self.texte_message.set_text(texte)


# Fonctions utilitaires

def bornes_couleur(parametres):
    """Échelle de couleur qui contient la température initiale et la consigne."""
    bas = min(parametres.temperature_initiale, parametres.consigne) - MARGE_COULEUR
    haut = max(parametres.temperature_initiale, parametres.consigne) + MARGE_COULEUR
    return bas, haut


def puissance_max_attendue(simulation, t_ext_min):
    """Plus grande puissance à afficher : radiateurs ou pertes maximales."""
    p = simulation.parametres
    radiateurs = p.puissance_radiateur * len(simulation.grille.radiateurs)
    t_haute = max(p.temperature_initiale, p.consigne + p.hysteresis)
    pertes = p.h * p.surface_facade * max(t_haute - t_ext_min, 0.0)
    return max(radiateurs, pertes, 100.0)


def segment_bord(cote, j, i, pas):
    """Coordonnées (xs, ys) du bord extérieur de la maille (j, i) côté façade."""
    x0, x1, y0, y1 = i * pas, (i + 1) * pas, j * pas, (j + 1) * pas
    segments = {"nord": ([x0, x1], [y1, y1]), "sud": ([x0, x1], [y0, y0]),
                "est": ([x1, x1], [y0, y1]), "ouest": ([x0, x0], [y0, y1])}
    return segments[cote]


def masquer_obstacles(temperature, air):
    """Tableau masqué : les obstacles s'affichent en gris."""
    return np.ma.masked_where(~air, temperature)


def habiller_axes(axe, ylabel, xlabel=None):
    axe.set_ylabel(ylabel)
    if xlabel:
        axe.set_xlabel(xlabel)
    axe.grid(alpha=0.3)
    axe.legend(loc="upper right", fontsize=8)


def texte_etat(simulation):
    """Ligne d'état affichée en haut de la fenêtre."""
    minutes = int(round(simulation.temps) // 60)
    etat = "MARCHE" if simulation.thermostat.allume else "arrêt"
    energie = simulation.bilan.radiateurs / JOULES_PAR_KWH
    return (f"t = {minutes // 60:3d} h {minutes % 60:02d}   |   T moyenne {simulation.temperature_moyenne:5.2f} °C"
            f"   |   Text {simulation.t_ext:6.1f} °C   |   chauffage {etat:6s}   |   énergie {energie:6.2f} kWh")


def texte_fin_cycle(resume, dossier):
    atteinte = texte_atteinte(resume["temps_atteinte_tc_min"])
    return (f"Cycle terminé. Énergie {resume['energie_consommee_kwh']:.2f} kWh, puissance moyenne "
            f"{resume['puissance_moyenne_w']:.0f} W, Tc atteinte en {atteinte}.\nExport : {dossier}")
