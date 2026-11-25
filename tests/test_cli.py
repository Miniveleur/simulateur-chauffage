import pytest

from simulateur_chauffage import cli


def test_cli_exporte_un_cycle(tmp_path, capsys):
    cli.main(["--duree", "1", "--sortie", str(tmp_path), "--puissance_radiateur", "1500"])
    assert "Énergie consommée" in capsys.readouterr().out
    assert len(list(tmp_path.glob("cycle_*"))) == 1


def test_cli_surface_tiree_de_la_piece(chambre_type):
    arguments = cli.creer_analyseur().parse_args([])
    assert cli.parametres_depuis_arguments(arguments, chambre_type).surface_facade == pytest.approx(10.0)


def test_cli_refuse_duree_nulle():
    with pytest.raises(SystemExit):
        cli.creer_analyseur().parse_args(["--duree", "0"])
