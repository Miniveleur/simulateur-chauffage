"""Interface matplotlib : réglages, lancement et déroulement des cycles."""

from dataclasses import fields, replace
from pathlib import Path

import matplotlib.pyplot as plt

from . import widgets
from .cycle import parametres_pour_piece, terminer_cycle
from .export import exporter_cycle
from .piece import construire_grille
from .profils import PROFILS
from .simulation import Parametres, Simulation
from .unites import SECONDES_PAR_HEURE, SECONDES_PAR_MINUTE
from .vue import Vue, texte_fin_cycle

INTERVALLE_IMAGE_MS = 40
TYPES_PARAMETRES = {champ.name: type(champ.default) for champ in fields(Parametres)}


class InterfaceSimulateur:
    def __init__(self, piece, dossier_resultats="resultats", parametres=None):
        self.piece = piece
        self.grille = construire_grille(piece)
        self.dossier_resultats = Path(dossier_resultats)
        self.simulation = None
        self.duree_cycle = 0.0
        self.figure = plt.figure(figsize=(15, 9))
        nommer_fenetre(self.figure, "Simulateur de chauffage")
        self.vue = Vue(self.figure, piece, self.grille)
        self._creer_reglages(parametres or parametres_pour_piece(piece))
        self._creer_boutons()
        self.minuterie = self.figure.canvas.new_timer(interval=INTERVALLE_IMAGE_MS)
        self.minuterie.add_callback(self.image_suivante)
        self.afficher_apercu()

    # Construction des commandes

    def _creer_reglages(self, parametres):
        self.curseurs = widgets.creer_curseurs(self.figure, parametres, 0.17, 0.03, 0.20, 0.038)
        for curseur in self.curseurs.values():
            curseur.on_changed(lambda _valeur: self.afficher_apercu())
        self.choix_profil = widgets.creer_choix(self.figure, (0.48, 0.10, 0.20, 0.20), "Profil Text", PROFILS)
        self.choix_duree = widgets.creer_choix(self.figure, (0.70, 0.10, 0.09, 0.20), "Durée", widgets.DUREES_H)

    def _creer_boutons(self):
        axe_vitesse = self.figure.add_axes((0.86, 0.27, 0.11, 0.025))
        self.curseur_vitesse = widgets.Slider(axe_vitesse, "Vitesse\n(min/image)", 1, 60, valinit=10, valstep=1)
        self.bouton_lancer = widgets.creer_bouton(self.figure, (0.83, 0.18, 0.14, 0.05), "Lancer le cycle",
                                                  "#C8E6C9")
        self.bouton_arreter = widgets.creer_bouton(self.figure, (0.83, 0.11, 0.14, 0.05), "Arrêter", "#FFCDD2")
        self.bouton_lancer.on_clicked(lambda _evt: self.lancer_cycle())
        self.bouton_arreter.on_clicked(lambda _evt: self.arreter_cycle())

    # Lecture des réglages

    def lire_parametres(self):
        """Parametres construits à partir de la position des curseurs."""
        valeurs = {champ: TYPES_PARAMETRES[champ](c.val) for champ, c in self.curseurs.items()}
        return replace(Parametres(), **valeurs)

    def profil_choisi(self):
        return PROFILS[self.choix_profil.value_selected]

    def duree_choisie_s(self):
        return widgets.DUREES_H[self.choix_duree.value_selected] * SECONDES_PAR_HEURE

    # Déroulement d'un cycle

    @property
    def cycle_en_cours(self):
        return self.simulation is not None

    def lancer_cycle(self):
        if self.cycle_en_cours:
            return
        self.duree_cycle = self.duree_choisie_s()
        self.simulation = Simulation(self.grille, self.lire_parametres(), self.profil_choisi())
        self.verrouiller_reglages(True)
        self.vue.preparer_cycle(self.simulation, self.duree_cycle)
        self.afficher_message("Cycle en cours, réglages verrouillés.")
        self.minuterie.start()

    def image_suivante(self):
        """Appelé par la minuterie : avance la simulation puis redessine."""
        if not self.cycle_en_cours:
            return
        restant = self.duree_cycle - self.simulation.temps
        self.simulation.avancer(min(self.curseur_vitesse.val * SECONDES_PAR_MINUTE, restant))
        self.vue.montrer_simulation(self.simulation)
        self.figure.canvas.draw_idle()
        if self.simulation.temps >= self.duree_cycle - 1e-6:
            self.terminer_cycle()

    def terminer_cycle(self):
        simulation = self._fermer_cycle()
        resume = terminer_cycle(simulation, self.duree_cycle, self.piece.nom)
        self.vue.montrer_simulation(simulation)
        try:
            dossier = exporter_cycle(self.dossier_resultats, resume, simulation.historique, simulation.parametres)
        except OSError as erreur:
            self.afficher_message(f"Cycle terminé mais l'export a échoué (fichier ouvert ?) : {erreur}")
            return
        self.afficher_message(texte_fin_cycle(resume, dossier))

    def arreter_cycle(self):
        if self.cycle_en_cours:
            self._fermer_cycle()
            self.afficher_message("Cycle arrêté, rien n'a été exporté.")

    def _fermer_cycle(self):
        self.minuterie.stop()
        simulation, self.simulation = self.simulation, None
        self.verrouiller_reglages(False)
        self.vue.colorer_radiateurs(False)
        return simulation

    def verrouiller_reglages(self, verrou):
        for widget in (*self.curseurs.values(), self.choix_profil, self.choix_duree, self.bouton_lancer):
            widgets.verrouiller(widget, verrou)
        self.figure.canvas.draw_idle()

    # Affichage

    def afficher_apercu(self):
        """Hors cycle : montre la pièce à sa température initiale."""
        if self.cycle_en_cours:
            return
        self.vue.montrer_apercu(self.lire_parametres())
        self.figure.canvas.draw_idle()

    def afficher_message(self, texte):
        self.vue.afficher_message(texte)
        self.figure.canvas.draw_idle()


def nommer_fenetre(figure, titre):
    if figure.canvas.manager is not None:
        figure.canvas.manager.set_window_title(titre)
