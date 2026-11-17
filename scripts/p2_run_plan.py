"""Phase 2 : plan cellulaire hexagonal (N = 3, 7, 9), exports CSV + PNG.

Executer depuis la racine du projet (planif-gsm/) :
    python scripts/p2_run_plan.py
"""
from __future__ import annotations

import csv
import math

from planif.back_end.calculator import compute_radio
from planif.back_end.hex_grid import build_plan, min_cochannel_distance_km
from planif.back_end.params_io import load_params
from planif.front_end.plots_plan import plot_plan
from planif.paths import DEFAULT_PARAMS_FILE, results_dir

PATTERNS = (3, 7, 9)
ROWS, COLS = 7, 7  # grille minimale demandee par l'enonce


def main() -> None:
    params = load_params(DEFAULT_PARAMS_FILE)
    tables = results_dir("p2_plan", "tables")
    figures = results_dir("p2_plan", "figures")

    r_km = compute_radio(params).R_km  # le rayon R vient de la Personne 1
    print(f"Rayon de cellule utilise : R = {r_km:.3f} km\n")

    for n_cells in PATTERNS:
        plan = build_plan(n_cells, r_km, ROWS, COLS)

        csv_path = tables / f"p2_plan_cellules_N{n_cells}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["cell_id", "row", "col", "q", "r", "x_km", "y_km", "groupe"])
            for c in plan.cells:
                w.writerow([c.cell_id, c.row, c.col, c.q, c.r,
                            f"{c.x_km:.3f}", f"{c.y_km:.3f}", c.group])

        png_path = plot_plan(plan, figures / f"fig_p2_plan_{ROWS}x{COLS}_N{n_cells}.png")

        d_theo = r_km * math.sqrt(3 * n_cells)
        d_mes = min_cochannel_distance_km(plan)
        n_groups = len({c.group for c in plan.cells})
        print(f"N = {n_cells} : {len(plan.cells)} cellules, {n_groups} groupes presents, "
              f"D theorique = {d_theo:.3f} km, D mesure (min co-canal) = "
              f"{'n/a' if d_mes is None else f'{d_mes:.3f} km'}")
        print(f"   - {csv_path}\n   - {png_path}")


if __name__ == "__main__":
    main()