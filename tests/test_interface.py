import matplotlib.pyplot as plt
import pytest

from simulateur_chauffage.interface import InterfaceSimulateur


@pytest.fixture
def interface(piece, tmp_path):
    ui = InterfaceSimulateur(piece, tmp_path)
    yield ui
    plt.close(ui.figure)


def test_reglages_verrouilles_pendant_le_cycle(interface):
    interface.lancer_cycle()
    assert interface.cycle_en_cours
    assert not any(c.active for c in interface.curseurs.values())
    assert not interface.choix_profil.active and not interface.bouton_lancer.active
    assert interface.curseur_vitesse.active


def test_parametres_figes_pendant_le_cycle(interface):
    interface.lancer_cycle()
    interface.curseurs["puissance_radiateur"].set_val(2500)
    assert interface.simulation.parametres.puissance_radiateur == 1000


def test_cycle_complet_exporte(interface, tmp_path):
    interface.choix_duree.set_active(0)
    interface.curseur_vitesse.set_val(60)
    interface.lancer_cycle()
    while interface.cycle_en_cours:
        interface.image_suivante()
    assert all(c.active for c in interface.curseurs.values())
    assert len(list(tmp_path.glob("cycle_*"))) == 1
    assert "Cycle terminé" in interface.vue.texte_message.get_text()


def test_arret_sans_export(interface, tmp_path):
    interface.lancer_cycle()
    interface.image_suivante()
    interface.arreter_cycle()
    assert not interface.cycle_en_cours
    assert not list(tmp_path.glob("cycle_*"))


def test_occupants_entier(interface):
    interface.curseurs["occupants"].set_val(2)
    assert interface.lire_parametres().occupants == 2
    assert isinstance(interface.lire_parametres().occupants, int)


def _cliquer(figure, axe):
    from matplotlib.backend_bases import MouseEvent

    figure.canvas.draw()
    x, y = axe.transAxes.transform((0.9, 0.5))
    for nom in ("button_press_event", "button_release_event"):
        MouseEvent(nom, figure.canvas, x, y, button=1)._process()


def test_clic_sur_curseur_verrouille_ignore(interface):
    interface.lancer_cycle()
    curseur = interface.curseurs["puissance_radiateur"]
    _cliquer(interface.figure, curseur.ax)
    assert curseur.val == 1000


def test_clic_sur_curseur_libre_pris_en_compte(interface):
    curseur = interface.curseurs["puissance_radiateur"]
    _cliquer(interface.figure, curseur.ax)
    assert curseur.val > 2000


def test_relance_apres_arret_et_affichage_remis_a_zero(interface):
    interface.lancer_cycle()
    interface.image_suivante()
    interface.arreter_cycle()
    interface.curseurs["consigne"].set_val(21)
    assert len(interface.vue.ligne_tint.get_xdata()) == 0
    assert interface.vue.marques_radiateurs[0].get_facecolor()[:3] == (1.0, 1.0, 1.0)
    interface.lancer_cycle()
    assert interface.simulation.parametres.consigne == 21


def test_export_en_echec_affiche_un_message(interface, monkeypatch):
    import simulateur_chauffage.interface as module

    def echec(*_args):
        raise PermissionError("fichier verrouillé")

    monkeypatch.setattr(module, "exporter_cycle", echec)
    interface.choix_duree.set_active(0)
    interface.curseur_vitesse.set_val(60)
    interface.lancer_cycle()
    while interface.cycle_en_cours:
        interface.image_suivante()
    assert "échoué" in interface.vue.texte_message.get_text()
