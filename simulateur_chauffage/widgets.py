"""Création des curseurs, boutons et choix de l'interface matplotlib."""

from dataclasses import dataclass

from matplotlib.widgets import Button, RadioButtons, Slider

COULEUR_VERROU = "#DDDDDD"


@dataclass(frozen=True)
class ReglageCurseur:
    """Un curseur relié à un champ de Parametres."""

    champ: str
    libelle: str
    minimum: float
    maximum: float
    pas: float


REGLAGES = (
    ReglageCurseur("puissance_radiateur", "Puissance radiateur (W)", 0, 3000, 50),
    ReglageCurseur("consigne", "Consigne Tc (°C)", 15, 25, 0.5),
    ReglageCurseur("temperature_initiale", "T initiale pièce (°C)", 5, 25, 0.5),
    ReglageCurseur("h", "h façade (W/m².K)", 0.2, 6, 0.1),
    ReglageCurseur("surface_facade", "Surface façade S (m²)", 2, 30, 0.5),
    ReglageCurseur("occupants", "Occupants (100 W chacun)", 0, 4, 1),
    ReglageCurseur("diffusivite", "Diffusivité air (m²/s)", 0.001, 0.05, 0.001),
    ReglageCurseur("inertie", "Inertie (x capacité air)", 1, 20, 0.5),
)

DUREES_H = {"24 h": 24, "48 h": 48, "72 h": 72, "7 jours": 168}


def creer_curseur(figure, rectangle, reglage, valeur):
    axe = figure.add_axes(rectangle)
    return Slider(axe, reglage.libelle, reglage.minimum, reglage.maximum,
                  valinit=valeur, valstep=reglage.pas)


def creer_curseurs(figure, parametres, gauche, bas, largeur, hauteur_ligne):
    """Un curseur par réglage, empilés de haut en bas. Renvoie un dict champ -> Slider."""
    curseurs = {}
    for rang, reglage in enumerate(REGLAGES):
        y = bas + (len(REGLAGES) - 1 - rang) * hauteur_ligne
        rectangle = (gauche, y, largeur, hauteur_ligne * 0.6)
        curseurs[reglage.champ] = creer_curseur(figure, rectangle, reglage, getattr(parametres, reglage.champ))
    return curseurs


def creer_choix(figure, rectangle, titre, options):
    axe = figure.add_axes(rectangle)
    axe.set_title(titre, fontsize=9, loc="left")
    return RadioButtons(axe, list(options))


def creer_bouton(figure, rectangle, libelle, couleur="#EEEEEE"):
    return Button(figure.add_axes(rectangle), libelle, color=couleur, hovercolor="#FFE0B2")


def verrouiller(widget, verrou):
    """Rend un widget inactif (et grisé) pendant un cycle."""
    widget.active = not verrou  # attention : RadioButtons.set_active a un autre sens
    widget.ax.set_facecolor(COULEUR_VERROU if verrou else couleur_normale(widget))
    griser_curseur(widget, verrou)


def couleur_normale(widget):
    """Couleur de fond d'origine : celle du bouton, sinon blanc."""
    return widget.color if isinstance(widget, Button) else "white"


def griser_curseur(widget, verrou):
    """Pâlit la barre et le libellé d'un curseur (sans effet sur les autres widgets)."""
    if isinstance(widget, Slider):
        widget.poly.set_alpha(0.25 if verrou else 1.0)
        widget.label.set_color("#999999" if verrou else "black")
