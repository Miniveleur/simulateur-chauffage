import numpy as np
import pytest

from simulateur_chauffage.profils import PROFILS, profil_constant


@pytest.mark.parametrize("profil", PROFILS.values(), ids=list(PROFILS))
def test_min_et_max_aux_bonnes_heures(profil):
    heures = np.linspace(0, 24, 24 * 60, endpoint=False)
    valeurs = np.array([profil.temperature(h * 3600) for h in heures])
    assert valeurs.min() == pytest.approx(profil.t_min)
    assert valeurs.max() == pytest.approx(profil.t_max)
    assert heures[valeurs.argmin()] == pytest.approx(profil.heure_min, abs=0.02)
    assert heures[valeurs.argmax()] == pytest.approx(profil.heure_max, abs=0.02)


@pytest.mark.parametrize("profil", PROFILS.values(), ids=list(PROFILS))
def test_profil_continu_et_periodique(profil):
    t = np.arange(0, 48 * 3600, 60.0)
    valeurs = np.array([profil.temperature(x) for x in t])
    assert np.abs(np.diff(valeurs)).max() < 0.1
    assert profil.temperature(3 * 3600) == pytest.approx(profil.temperature(27 * 3600))


def test_profil_constant():
    assert profil_constant(-5).temperature(12345) == -5


def test_heures_min_et_max_identiques_refusees():
    from simulateur_chauffage.profils import ProfilText

    with pytest.raises(ValueError):
        ProfilText("X", -5, 5, heure_min=7, heure_max=7)
