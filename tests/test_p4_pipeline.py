"""Tests de la Personne 4 : pipeline complet, exports, application."""
import ast

import pytest

from planif.back_end.freq_allocation import STRATEGIES
from planif.back_end.params_io import load_params, save_params, update_params
from planif.back_end.studies import load_studies_config
from planif.paths import DEFAULT_PARAMS_FILE, ROOT_DIR
from planif.pipeline import build_summary_text, export_all, run_pipeline


@pytest.fixture
def params():
    return load_params(DEFAULT_PARAMS_FILE)


def test_pipeline_modules_are_consistent(params):
    res = run_pipeline(params)
    assert res.radio.N == res.plan.N == res.allocation.N == params.N
    assert res.plan.R_km == pytest.approx(res.radio.R_km)
    assert res.allocation.N_f == params.N_f
    assert len(res.plan.cells) == 49
    assert len(res.allocation.assignments) == 49


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_pipeline_both_strategies_have_no_problem(params, strategy):
    res = run_pipeline(params, strategy=strategy)
    assert res.problems == ()
    assert res.d_measured_km == pytest.approx(res.radio.D_km)


@pytest.mark.parametrize("n_cells", [3, 4, 9, 12])
def test_pipeline_other_patterns(params, n_cells):
    res = run_pipeline(update_params(params, N=n_cells), with_studies=False)
    assert res.plan.N == n_cells
    assert res.problems == ()


def test_comparison_table_n3_7_9(params):
    res = run_pipeline(params)
    assert [r.N for r in res.comparison] == [3, 7, 9]
    assert [r.SIR_ok for r in res.comparison] == [False, False, True]


def test_sir_warning_when_pattern_too_small(params):
    res = run_pipeline(params)                       # N = 7 : SIR 15.36 dB < 17 dB
    assert any("SIR" in w for w in res.warnings)


def test_no_sir_warning_when_pattern_valid(params):
    res = run_pipeline(update_params(params, N=9))   # SIR 17.27 dB >= 17 dB
    assert not any("SIR" in w for w in res.warnings)


def test_invalid_strategy_raises(params):
    with pytest.raises(ValueError):
        run_pipeline(params, strategy="aleatoire")


def test_save_reload_then_pipeline(tmp_path, params):
    path = tmp_path / "params.json"
    save_params(update_params(params, N=9), path)
    res = run_pipeline(load_params(path))
    assert res.radio.N == 9 and res.radio.SIR_ok


def test_studies_included(params):
    cfg = load_studies_config()
    res = run_pipeline(params)
    assert len(res.density_rows) == len(cfg.densities_ab_km2) * len(cfg.patterns)
    assert len(res.env_rows) == len(cfg.environments) * len(cfg.patterns)


def test_export_all_creates_files(tmp_path, params):
    res = run_pipeline(params)
    files = export_all(res, tmp_path)
    assert len(files) >= 15
    assert all(f.exists() and f.stat().st_size > 0 for f in files)
    assert (tmp_path / "figures" / "fig_p4_plan_7x7_N7_entrelacee.png").exists()
    assert (tmp_path / "tables" / "p4_tableau_comparatif_N3_7_9.csv").exists()


def test_export_allocation_csv_one_line_per_cell(tmp_path, params):
    export_all(run_pipeline(params), tmp_path)
    path = tmp_path / "tables" / "p4_allocation_cellules_entrelacee_N7.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) == 1 + 49                      # en-tete + 49 cellules


def test_summary_text_mentions_key_values(params):
    text = build_summary_text(run_pipeline(params))
    assert "N = 7" in text and "entrelacee" in text and "R = 9.046 km" in text


def test_streamlit_app_is_valid_python():
    source = (ROOT_DIR / "src" / "planif" / "front_end" / "app_streamlit.py").read_text(encoding="utf-8")
    ast.parse(source)