"""Tests de la Personne 3 : allocation des canaux et etudes d'analyse."""
import math

import pytest

from planif.back_end.freq_allocation import (STRATEGIES, adjacent_pairs_in_same_group, allocate,
                                             assign_to_cells, build_allocation, group_sizes,
                                             verify_allocation, verify_cochannel_separation)
from planif.back_end.params_io import load_params
from planif.back_end.studies import (density_study, environment_study, load_studies_config,
                                     max_density_supported, minimal_valid_pattern)
from planif.contracts import Cell, CellAssignment, CellularPlan, FrequencyAllocation
from planif.paths import DEFAULT_PARAMS_FILE


def fake_plan(n_cells=3, groups=(1, 2, 3, 1), spacing=100.0):
    """Plan fabrique a la main : P3 peut etre teste sans le code de P2."""
    cells = tuple(Cell(cell_id=i, q=i, r=0, row=0, col=i, x_km=i * spacing, y_km=0.0, group=g)
                  for i, g in enumerate(groups))
    return CellularPlan(N=n_cells, R_km=9.0, rows=1, cols=len(groups), cells=cells)


def test_group_sizes_124_over_3_and_7():
    assert group_sizes(124, 3) == [42, 41, 41]
    assert group_sizes(124, 7) == [18, 18, 18, 18, 18, 17, 17]


def test_contiguous_small_example():
    assert allocate(10, 3, "contigue") == {1: (1, 2, 3, 4), 2: (5, 6, 7), 3: (8, 9, 10)}


def test_interleaved_small_example():
    assert allocate(10, 3, "entrelacee") == {1: (1, 4, 7, 10), 2: (2, 5, 8), 3: (3, 6, 9)}


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("n_f, n_cells", [(124, 3), (124, 7), (124, 9), (10, 3), (7, 7), (100, 4)])
def test_partition_and_balance(strategy, n_f, n_cells):
    groups = allocate(n_f, n_cells, strategy)
    channels = [c for g in groups.values() for c in g]
    assert sorted(channels) == list(range(1, n_f + 1))      # aucun canal perdu ni double
    sizes = [len(g) for g in groups.values()]
    assert max(sizes) - min(sizes) <= 1
    assert sizes == sorted(sizes, reverse=True)             # restes sur les premiers groupes


def test_invalid_inputs():
    with pytest.raises(ValueError):
        allocate(2, 3, "contigue")
    with pytest.raises(ValueError):
        allocate(10, 3, "aleatoire")


def test_adjacent_pairs_metric():
    assert adjacent_pairs_in_same_group(allocate(124, 7, "contigue")) == 124 - 7
    assert adjacent_pairs_in_same_group(allocate(124, 7, "entrelacee")) == 0


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_cells_of_same_group_share_exact_channels(strategy):
    plan = fake_plan()
    alloc = build_allocation(plan, 124, strategy)
    assert alloc.assignments[0].channels == alloc.assignments[3].channels
    assert alloc.assignments[0].channels != alloc.assignments[1].channels
    assert verify_allocation(alloc) == []


def test_verify_detects_lost_channel():
    plan = fake_plan()
    good = build_allocation(plan, 10, "contigue")
    groups = dict(good.groups)
    groups[3] = groups[3][:-1]                       # on "perd" le canal 10
    bad = FrequencyAllocation("contigue", 10, 3, groups, assign_to_cells(plan, groups))
    assert any("partition" in p for p in verify_allocation(bad))


def test_cochannel_separation_detection():
    plan = fake_plan(spacing=100.0)                  # cellules 0 et 3 a 300 km (meme groupe)
    alloc = build_allocation(plan, 10, "contigue")
    assert verify_cochannel_separation(plan, alloc, d_km=250.0) == []
    assert verify_cochannel_separation(plan, alloc, d_km=350.0) != []


def test_integration_with_person2_plan():
    from planif.back_end.hex_grid import build_plan
    r = 9.046
    plan = build_plan(7, r, 10, 10)
    alloc = build_allocation(plan, 124, "entrelacee")
    assert verify_allocation(alloc) == []
    assert verify_cochannel_separation(plan, alloc, r * math.sqrt(21)) == []


# ------------------------------------------------------------------ etudes
@pytest.fixture
def params():
    return load_params(DEFAULT_PARAMS_FILE)


def test_max_density_balances_active_and_channels(params):
    from planif.back_end.params_io import update_params
    from planif.back_end.calculator import compute_radio
    dmax = max_density_supported(params, 9)
    res = compute_radio(update_params(params, Dst_ab=dmax), 9)
    assert res.Utilisateurs_actifs_cellule == pytest.approx(res.Canaux_par_cellule)


def test_density_study_rows(params):
    rows = density_study(params, [1, 100], [3, 9])
    assert len(rows) == 4
    low = next(r for r in rows if r["Dst_ab"] == 1 and r["N"] == 3)
    high = next(r for r in rows if r["Dst_ab"] == 100 and r["N"] == 3)
    assert high["Utilisateurs_actifs"] > low["Utilisateurs_actifs"]
    assert high["Actifs_sur_canaux"] > low["Actifs_sur_canaux"]


@pytest.mark.parametrize("n_exp, expected", [(3.5, 9), (3.0, 16), (2.5, 36)])
def test_minimal_valid_pattern(n_exp, expected):
    assert minimal_valid_pattern(n_exp, 17.0) == expected


def test_environment_study(params):
    cfg = load_studies_config()
    rows = environment_study(params, cfg.environments, cfg.zone_area_km2, cfg.patterns)
    by_env = {e: next(r for r in rows if r["Environnement"] == e) for e in cfg.environments}
    assert by_env["rural"]["R_km"] > by_env["sub-urbain"]["R_km"] > by_env["urbain"]["R_km"]
    assert by_env["rural"]["Sites_necessaires"] < by_env["urbain"]["Sites_necessaires"]
    for r in rows:   # nombre de sites = surface de la zone / surface d'une cellule, arrondi au-dessus
        exact = cfg.zone_area_km2 / r["Surface_cellule_km2"]
        assert exact <= r["Sites_necessaires"] < exact + 1.01