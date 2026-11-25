"""Régulation tout ou rien (TOR) avec hystérésis.

Tous les radiateurs sont commandés ensemble à partir de la température
moyenne de la pièce. Ils s'allument quand la moyenne passe sous
Tc - hystérésis et s'éteignent quand elle passe au-dessus de Tc + hystérésis.
Entre les deux, ils gardent leur état.
"""

from dataclasses import dataclass


@dataclass
class ThermostatTOR:
    consigne: float
    hysteresis: float = 0.5
    allume: bool = False
    demarrages: int = 0

    @property
    def seuil_bas(self):
        return self.consigne - self.hysteresis

    @property
    def seuil_haut(self):
        return self.consigne + self.hysteresis

    def initialiser(self, temperature):
        """État de départ : on chauffe si la pièce est sous la consigne."""
        self.allume = temperature < self.consigne
        self.demarrages = int(self.allume)
        return self.allume

    def mettre_a_jour(self, temperature):
        """Met à jour l'état selon la température moyenne et le renvoie."""
        if temperature < self.seuil_bas and not self.allume:
            self.allume = True
            self.demarrages += 1
        elif temperature > self.seuil_haut:
            self.allume = False
        return self.allume
