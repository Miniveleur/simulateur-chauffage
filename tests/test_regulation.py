from simulateur_chauffage.regulation import ThermostatTOR


def test_hysteresis():
    th = ThermostatTOR(20.0, 0.5)
    assert th.initialiser(19.0) is True
    assert th.mettre_a_jour(20.4) is True   # dans la bande : garde l'état
    assert th.mettre_a_jour(20.6) is False  # au-dessus de Tc + 0,5
    assert th.mettre_a_jour(19.6) is False  # dans la bande : reste éteint
    assert th.mettre_a_jour(19.4) is True   # sous Tc - 0,5


def test_demarrage_au_dessus_de_la_consigne():
    assert ThermostatTOR(20.0).initialiser(21.0) is False


def test_demarre_entre_tc_moins_hysteresis_et_tc():
    assert ThermostatTOR(20.0, 0.5).initialiser(19.8) is True


def test_seuils_exacts_gardent_l_etat():
    th = ThermostatTOR(20.0, 0.5)
    th.initialiser(21.0)
    assert th.mettre_a_jour(19.5) is False
    th.mettre_a_jour(19.0)
    assert th.mettre_a_jour(20.5) is True


def test_comptage_des_demarrages():
    th = ThermostatTOR(20.0, 0.5)
    th.initialiser(18.0)
    for t in (21.0, 19.0, 19.2, 21.0, 19.0):
        th.mettre_a_jour(t)
    assert th.demarrages == 3
