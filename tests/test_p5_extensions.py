"""Tests des options d'amelioration (enonce, section 6)."""
import math

import pytest

from planif.back_end import extensions as ext
from planif.back_end.calculator import compute_radio
from planif.back_end.coloring import group_of
from planif.back_end.hex_grid import axial_to_xy_km
from planif.back_end.params_io import load_params, update_params
from planif.front_end import plots_extensions as pe
from planif.front_end.map_html import build_leaflet_html
from planif.paths import DEFAULT_PARAMS_FILE

R = 9.046


@pytest.fixture
def params():
    return load_params(DEFAULT_PARAMS_FILE)


# ---------------------------------------------------------------- motifs
def test_pattern_comparison_includes_n4_and_minimal(params):
    rows = ext.pattern_comparison(params)
    assert [r["N"] for r in rows] == [3, 4, 7, 9, 12, 13, 16]
    sirs = [r["SIR_dB"] for r in rows]
    assert sirs == sorted(sirs)
    assert [r["SIR_ok"] for r in rows] == [False, False, False, True, True, True, True]
    assert [r["N"] for r in rows if r["Motif_minimal"]] == [9]


def test_pattern_comparison_skips_n_above_nf(params):
    rows = ext.pattern_comparison(update_params(params, N_f=10))
    assert [r["N"] for r in rows] == [3, 4, 7, 9]


def test_pattern_rows_match_p1(params):
    for r in ext.pattern_comparison(params):
        res = compute_radio(params, r["N"])
        assert r["D_km"] == pytest.approx(res.D_km, abs=1e-3)
        assert r["SIR_dB"] == pytest.approx(res.SIR_dB, abs=1e-2)


# --------------------------------------------------------------- exposants
def test_exponent_sweep_monotonic_and_nmin(params):
    rows = ext.exponent_sweep(params, exponents=(2.5, 3.0, 3.5), patterns=(7,))
    radii = [r["R_km"] for r in rows]
    sites = [r["Sites_necessaires"] for r in rows]
    assert radii == sorted(radii, reverse=True)
    assert sites == sorted(sites)
    assert [r["N_min_valide"] for r in rows] == [36, 16, 9]


# ---------------------------------------------------------------- clusters
@pytest.mark.parametrize("n_cells", [3, 4, 7, 9, 12, 13])
def test_cluster_offsets_are_complete(n_cells):
    off = ext.cluster_offsets(n_cells)
    assert sorted(off) == list(range(1, n_cells + 1))
    assert len(set(off.values())) == n_cells
    assert off[group_of(0, 0, n_cells)] == (0, 0)


@pytest.mark.parametrize("n_cells", [3, 4, 7, 9, 12])
def test_cluster_map_is_valid_and_covers_zone(n_cells):
    zone = 40.0
    cmap = ext.build_cluster_map(n_cells, R, 124, zone)
    assert ext.verify_cluster_map(cmap) == []
    assert cmap.n_cells == cmap.n_clusters * n_cells
    present = {(c.q, c.r) for c in cmap.cells}
    for q in range(-30, 31):
        for r in range(-30, 31):
            x, y = axial_to_xy_km(q, r, R)
            if math.hypot(x, y) <= zone:
                assert (q, r) in present


def test_cluster_map_cochannel_distance_is_D():
    cmap = ext.build_cluster_map(7, R, 124, 40.0)
    best = None
    for a in cmap.cells:
        for b in cmap.cells:
            if a.cell_id < b.cell_id and a.group == b.group:
                d = math.hypot(a.x_km - b.x_km, a.y_km - b.y_km)
                best = d if best is None or d < best else best
    assert best is not None
    assert best == pytest.approx(R * math.sqrt(21))


def test_km_to_latlon():
    assert ext.km_to_latlon(0, 0, 36.8, 10.18) == pytest.approx((36.8, 10.18))
    lat, _ = ext.km_to_latlon(0, 111.195, 36.8, 10.18)
    assert lat - 36.8 == pytest.approx(1.0, abs=1e-3)


def test_geojson_structure():
    cmap = ext.build_cluster_map(7, R, 124, 40.0)
    gj = ext.to_geojson(cmap)
    assert len(gj["features"]) == cmap.n_cells
    ring = gj["features"][0]["geometry"]["coordinates"][0]
    assert len(ring) == 7 and ring[0] == ring[-1]
    assert -180 <= ring[0][0] <= 180 and -90 <= ring[0][1] <= 90


def test_convex_hull_square():
    pts = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5)]
    assert sorted(ext.convex_hull(pts)) == [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_leaflet_html():
    cmap = ext.build_cluster_map(7, R, 124, 40.0)
    html = build_leaflet_html(cmap)
    assert "L.map" in html and "__DATA__" not in html
    assert html.count('"ring"') == cmap.n_cells


def test_invalid_inputs():
    with pytest.raises(ValueError):
        ext.build_cluster_map(5, R, 124, 40.0)
    with pytest.raises(ValueError):
        ext.build_cluster_map(7, -1.0, 124, 40.0)
    with pytest.raises(ValueError):
        ext.build_cluster_map(7, R, 124, 40.0, strategy="aleatoire")


def test_all_figures_are_written(tmp_path, params):
    rows = ext.pattern_comparison(params)
    sweep = ext.exponent_sweep(params)
    envs = {"urbain": 3.5, "sub-urbain": 3.0, "rural": 2.5}
    cmap = ext.build_cluster_map(7, R, 124, 40.0)
    paths = [
        pe.plot_pattern_sir(rows, params.SIR_min_dB, tmp_path / "a.png"),
        pe.plot_pattern_capacity(rows, tmp_path / "b.png"),
        pe.plot_exponent_radius_sites(sweep, envs, tmp_path / "c.png"),
        pe.plot_exponent_sir(sweep, params.SIR_min_dB, envs, tmp_path / "d.png"),
        pe.plot_cluster_map(cmap, tmp_path / "e.png"),
    ]
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)