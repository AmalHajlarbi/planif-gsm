"""Phase 3 : allocation des canaux (contigue / entrelacee) + etudes densite et environnement.

Executer depuis la racine du projet (planif-gsm/) :
    python scripts/p3_run_alloc.py
"""
from __future__ import annotations

import csv

from planif.back_end.calculator import compute_radio
from planif.back_end.freq_allocation import (STRATEGIES, adjacent_pairs_in_same_group,
                                             build_allocation, verify_allocation,
                                             verify_cochannel_separation)
from planif.back_end.hex_grid import build_plan
from planif.back_end.params_io import load_params
from planif.back_end.studies import (density_study, environment_study, load_studies_config,
                                     max_density_supported)
from planif.front_end import plots_studies
from planif.front_end.plots_plan import plot_plan
from planif.paths import DEFAULT_PARAMS_FILE, results_dir

ROWS, COLS = 7, 7


def write_rows(rows: list[dict], path) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    params = load_params(DEFAULT_PARAMS_FILE)
    cfg = load_studies_config()
    tables = results_dir("p3_alloc", "tables")
    figures = results_dir("p3_alloc", "figures")
    r_km = compute_radio(params).R_km

    # ------------------------------------------------ A) allocation des canaux
    print("=== A) Allocation des canaux ===")
    for n_cells in cfg.patterns:
        d_km = compute_radio(params, n_cells).D_km
        plan = build_plan(n_cells, r_km, ROWS, COLS)
        allocs = {s: build_allocation(plan, params.N_f, s) for s in STRATEGIES}

        for s, alloc in allocs.items():
            problems = verify_allocation(alloc) + verify_cochannel_separation(plan, alloc, d_km)
            sizes = [len(alloc.groups[g]) for g in sorted(alloc.groups)]
            print(f"N = {n_cells} | {s:10s} | tailles des groupes {sizes} | "
                  f"paires de canaux consecutifs dans un meme groupe : "
                  f"{adjacent_pairs_in_same_group(alloc.groups)} | "
                  f"verification : {'OK' if not problems else problems}")

            with open(tables / f"p3_groupes_{s}_N{n_cells}.csv", "w", newline="",
                      encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["groupe", "nb_canaux", "canaux"])
                for g in sorted(alloc.groups):
                    w.writerow([g, len(alloc.groups[g]), " ".join(map(str, alloc.groups[g]))])

            cell_by_id = {c.cell_id: c for c in plan.cells}
            with open(tables / f"p3_allocation_cellules_{s}_N{n_cells}.csv", "w", newline="",
                      encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["cell_id", "row", "col", "groupe", "nb_canaux", "canaux"])
                for a in alloc.assignments:
                    c = cell_by_id[a.cell_id]
                    w.writerow([a.cell_id, c.row, c.col, a.group, len(a.channels),
                                " ".join(map(str, a.channels))])

        plot_plan(plan, figures / f"fig_p3_plan_avec_allocation_7x7_N{n_cells}.png",
                  allocation=allocs["contigue"])
        plots_studies.plot_allocation_comparison(
            allocs["contigue"], allocs["entrelacee"],
            figures / f"fig_p3_allocation_contigue_vs_entrelacee_N{n_cells}.png")

    # ------------------------------------------------ B) etude de densite
    print("\n=== B) Impact de la densite d'abonnes ===")
    dens_rows = density_study(params, cfg.densities_ab_km2, cfg.patterns)
    write_rows(dens_rows, tables / "p3_etude_densite.csv")
    plots_studies.plot_density_vs_channels(dens_rows, figures / "fig_p3_densite_vs_canaux.png")
    for n_cells in cfg.patterns:
        print(f"N = {n_cells} : densite max supportee = "
              f"{max_density_supported(params, n_cells):.3f} ab./km2 "
              f"(densite de params.json : {params.Dst_ab:g})")

    # ------------------------------------------------ C) etude d'environnement
    print(f"\n=== C) Impact de l'environnement (zone = {cfg.zone_area_km2:g} km2) ===")
    env_rows = environment_study(params, cfg.environments, cfg.zone_area_km2, cfg.patterns)
    write_rows(env_rows, tables / "p3_etude_environnement.csv")
    plots_studies.plot_environment_radius_sites(env_rows, figures / "fig_p3_environnement_R_sites.png")
    plots_studies.plot_environment_sir(env_rows, params.SIR_min_dB, figures / "fig_p3_environnement_sir.png")
    for env in cfg.environments:
        r0 = next(r for r in env_rows if r["Environnement"] == env)
        print(f"{env:11s} n = {r0['Pathloss_exp']:g} | R = {r0['R_km']:.2f} km | "
              f"sites = {r0['Sites_necessaires']} | N minimal valide = {r0['N_min_valide']}")

    print(f"\nTous les fichiers sont dans {tables.parent}")


if __name__ == "__main__":
    main()