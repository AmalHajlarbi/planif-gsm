"""Tests de la Personne 1 : calcul radio + lecture/ecriture des parametres."""
import json
import math

import pytest

from planif.back_end import radio_models as rm
from planif.back_end.calculator import compute_for_patterns, compute_radio
from planif.back_end.params_io import load_params, params_from_dict, save_params, update_params
from planif.paths import DEFAULT_PARAMS_FILE


@pytest.fixture
def params():
    return load_params(DEFAULT_PARAMS_FILE)


def test_p_tx_is_min():
    assert rm.p_tx_dbm(43, 23) == 23


def test_mapl_example():
    # 23 - (-100) + 2 = 125 dB
    assert rm.mapl_db(23, -100) == pytest.approx(125.0)


def test_radius_satisfies_pl_equals_mapl(params):
    res = compute_radio(params)
    pl_at_r = rm.path_loss_db(res.R_km, res.PL_d0_dB, params.Pathloss_exp, params.d0_km)
    assert pl_at_r == pytest.approx(res.MAPL_dB)


def test_free_space_pl_d0():
    # 900 MHz, 1 km : 32.44 + 59.085 = 91.52 dB
    assert rm.free_space_pl_db(900, 1) == pytest.approx(91.52, abs=0.01)


@pytest.mark.parametrize("n_cells, expected", [(3, 3.0), (7, math.sqrt(21)), (9, math.sqrt(27))])
def test_reuse_ratio(n_cells, expected):
    assert rm.reuse_ratio(n_cells) == pytest.approx(expected)


def test_sir_db_matches_linear():
    for n_cells in (3, 7, 9):
        lin = rm.sir_linear(n_cells, 3.5)
        assert 10 * math.log10(lin) == pytest.approx(rm.sir_db(n_cells, 3.5))


def test_sir_criterion_example(params):
    res = {r.N: r for r in compute_for_patterns(params)}
    assert not res[3].SIR_ok
    assert not res[7].SIR_ok
    assert res[9].SIR_ok


def test_sir_does_not_depend_on_R(params):
    r_a = compute_radio(update_params(params, P_BTS_dBm=50, P_MS_dBm=40))
    r_b = compute_radio(params)
    assert r_a.SIR_dB == pytest.approx(r_b.SIR_dB)


def test_channels_per_cell(params):
    assert compute_radio(params, 3).Canaux_par_cellule == pytest.approx(124 / 3)


def test_hex_area_unit_radius():
    assert rm.hex_cell_area_km2(1.0) == pytest.approx(3 * math.sqrt(3) / 2)


def test_subscribers_and_active_users(params):
    res = compute_radio(params)
    assert res.Abonnes_cellule == pytest.approx(res.Surface_cellule_km2 * params.Dst_ab)
    assert res.Utilisateurs_actifs_cellule == pytest.approx(res.Abonnes_cellule * params.T_act)


@pytest.mark.parametrize("n_cells, ok", [(1, True), (3, True), (4, True), (7, True), (9, True),
                                          (12, True), (13, True), (2, False), (5, False),
                                          (6, False), (8, False), (0, False)])
def test_valid_cluster_size(n_cells, ok):
    assert rm.is_valid_cluster_size(n_cells) is ok


def test_save_and_reload(tmp_path, params):
    path = tmp_path / "p.json"
    new = update_params(params, N=9, Pathloss_exp=3.0)
    save_params(new, path)
    assert load_params(path) == new


def test_missing_key_raises():
    with open(DEFAULT_PARAMS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    del data["N_f"]
    with pytest.raises(ValueError, match="manquantes"):
        params_from_dict(data)


def test_invalid_values_raise(params):
    with pytest.raises(ValueError):
        update_params(params, N=5)
    with pytest.raises(ValueError):
        update_params(params, T_act=1.5)