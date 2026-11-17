"""Tests de la Personne 2 : geometrie hexagonale et coloration par motif."""
import math

import pytest

from planif.back_end.coloring import cluster_ij, group_of
from planif.back_end.hex_grid import build_plan, distance_km, min_cochannel_distance_km

R = 9.0


@pytest.mark.parametrize("n_cells, expected", [(3, (1, 1)), (4, (2, 0)), (7, (2, 1)),
                                                (9, (3, 0)), (12, (2, 2)), (13, (3, 1))])
def test_cluster_ij(n_cells, expected):
    assert cluster_ij(n_cells) == expected


def test_cluster_ij_invalid():
    with pytest.raises(ValueError):
        cluster_ij(5)


def test_plan_size_and_ids():
    plan = build_plan(7, R, 7, 7)
    assert len(plan.cells) == 49
    assert [c.cell_id for c in plan.cells] == list(range(49))


@pytest.mark.parametrize("n_cells", [3, 7, 9])
def test_groups_range_and_all_present_7x7(n_cells):
    plan = build_plan(n_cells, R, 7, 7)
    groups = {c.group for c in plan.cells}
    assert groups == set(range(1, n_cells + 1))


def test_neighbor_distance_is_sqrt3_R():
    plan = build_plan(7, R, 7, 7)
    a = plan.cells[0 * 7 + 0]
    b = plan.cells[0 * 7 + 1]   # voisin sur la meme ligne
    assert distance_km(a, b) == pytest.approx(math.sqrt(3) * R)


@pytest.mark.parametrize("n_cells", [3, 4, 7, 9, 12, 13])
def test_min_cochannel_distance_equals_D(n_cells):
    plan = build_plan(n_cells, R, 15, 15)
    assert min_cochannel_distance_km(plan) == pytest.approx(R * math.sqrt(3 * n_cells))


@pytest.mark.parametrize("n_cells", [3, 4, 7, 9, 12])
def test_adjacent_cells_have_different_groups(n_cells):
    plan = build_plan(n_cells, R, 10, 10)
    for a in plan.cells:
        for b in plan.cells:
            if a.cell_id < b.cell_id and distance_km(a, b) < math.sqrt(3) * R * 1.01:
                assert a.group != b.group


@pytest.mark.parametrize("n_cells", [3, 7, 9, 12])
def test_group_is_periodic_on_cochannel_lattice(n_cells):
    i, j = cluster_ij(n_cells)
    for q in range(-4, 5):
        for r in range(-4, 5):
            g = group_of(q, r, n_cells)
            assert group_of(q + i, r + j, n_cells) == g
            assert group_of(q - j, r + i + j, n_cells) == g


def test_invalid_inputs():
    with pytest.raises(ValueError):
        build_plan(5, R)
    with pytest.raises(ValueError):
        build_plan(7, -1.0)