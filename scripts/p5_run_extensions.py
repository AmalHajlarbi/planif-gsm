"""Phase 5 : options d'amelioration (enonce, section 6) -> results/p5_options/.

Executer depuis la racine du projet (planif-gsm/) :
    python scripts/p5_run_extensions.py
"""
from __future__ import annotations

import csv
import json
import math

from planif.back_end import extensions as ext
from planif.back_end.calculator import compute_radio
from planif.back_end.params_io import load_params
from planif.back_end.studies import load_studies_config
from planif.front_end import plots_extensions as pe
from planif.front_end.map_html import build_leaflet_html
from planif.paths import DEFAULT_PARAMS_FILE, results_dir


def write_rows(rows: list[dict], path) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    params = load_params(DEFAULT_PARAMS_FILE)
    cfg = load_studies_config()
    tables = results_dir("p5_options", "tables")
    figures = results_dir("p5_options", "figures")
    maps = results_dir("p5_options", "maps")

    # ---- 1) plusieurs motifs
    print("=== 1) Comparaison de plusieurs motifs (memes parametres radio) ===")
    rows = ext.pattern_comparison(params)
    write_rows(rows, tables / "p5_comparaison_motifs.csv")
    pe.plot_pattern_sir(rows, params.SIR_min_dB, figures / "fig_p5_motifs_sir.png")
    pe.plot_pattern_capacity(rows, figures / "fig_p5_motifs_canaux.png")
    for r in rows:
        print(f"N = {r['N']:2d} | D/R = {r['D_sur_R']:.3f} | SIR = {r['SIR_dB']:6.2f} dB | "
              f"canaux/cellule = {r['Canaux_par_cellule']:6.2f} | "
              f"{'OK' if r['SIR_ok'] else 'NON'}{'  <- motif minimal valide' if r['Motif_minimal'] else ''}")

    # ---- 2) plusieurs exposants
    print("\n=== 2) Comparaison de plusieurs exposants de propagation ===")
    sweep = ext.exponent_sweep(params, zone_area_km2=cfg.zone_area_km2)
    write_rows(sweep, tables / "p5_balayage_exposants.csv")
    pe.plot_exponent_radius_sites(sweep, cfg.environments, figures / "fig_p5_exposant_R_sites.png")
    pe.plot_exponent_sir(sweep, params.SIR_min_dB, cfg.environments, figures / "fig_p5_exposant_sir.png")
    for env, n_exp in cfg.environments.items():
        r0 = min((r for r in sweep if r["N"] == 7), key=lambda r: abs(r["Pathloss_exp"] - n_exp))
        print(f"{env:11s} n = {n_exp:g} | R = {r0['R_km']:.2f} km | sites = {r0['Sites_necessaires']} "
              f"| N minimal valide = {r0['N_min_valide']}")

    # ---- 3) positionnement automatique des clusters
    r_km = compute_radio(params).R_km
    radius = math.sqrt(cfg.zone_area_km2 / math.pi)
    print(f"\n=== 3) Positionnement automatique de clusters (zone de {cfg.zone_area_km2:g} km2, "
          f"rayon {radius:.1f} km, centre GPS fictif {ext.DEFAULT_CENTER}) ===")
    for n_cells in cfg.patterns:
        cmap = ext.build_cluster_map(n_cells, r_km, params.N_f, radius, ext.DEFAULT_CENTER)
        problems = ext.verify_cluster_map(cmap)
        write_rows(ext.cells_table(cmap), tables / f"p5_clusters_cellules_N{n_cells}.csv")
        (maps / f"clusters_N{n_cells}.geojson").write_text(
            json.dumps(ext.to_geojson(cmap), ensure_ascii=False), encoding="utf-8")
        (maps / f"carte_clusters_N{n_cells}.html").write_text(
            build_leaflet_html(cmap, f"Plan de fréquences, motif N = {n_cells}"), encoding="utf-8")
        pe.plot_cluster_map(cmap, figures / f"fig_p5_clusters_N{n_cells}.png")
        print(f"N = {n_cells} : {cmap.n_clusters} clusters, {cmap.n_cells} cellules "
              f"({cmap.n_cells_in_zone} dans la zone) | verification : "
              f"{'OK' if not problems else problems}")

    print(f"\nTous les fichiers sont dans {tables.parent}")


if __name__ == "__main__":
    main()