"""Pipeline complet P1 -> P2 -> P3 et exports finaux (Personne 4).

Ce module ne contient AUCUNE formule radio : il appelle les fonctions des
Personnes 1, 2 et 3 et rassemble leurs resultats dans un objet unique.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from planif.back_end.calculator import compute_for_patterns, compute_radio
from planif.back_end.freq_allocation import (STRATEGIES, adjacent_pairs_in_same_group,
                                             build_allocation, verify_allocation,
                                             verify_cochannel_separation)
from planif.back_end.hex_grid import build_plan, min_cochannel_distance_km
from planif.back_end.studies import (StudiesConfig, density_study, environment_study,
                                     load_studies_config, max_density_supported,
                                     minimal_valid_pattern)
from planif.contracts import (CellularPlan, FrequencyAllocation, Params, RadioResults)
from planif.paths import results_dir

DEFAULT_PATTERNS = (3, 7, 9)
DEFAULT_STRATEGY = "entrelacee"


@dataclass(frozen=True)
class PipelineResult:
    """Tout ce qui est produit par la chaine complete pour un jeu de parametres."""

    params: Params
    strategy: str
    radio: RadioResults                       # motif choisi (params.N)
    comparison: tuple[RadioResults, ...]      # tableau comparatif (N = 3, 7, 9)
    plan: CellularPlan
    allocation: FrequencyAllocation
    d_measured_km: Optional[float]            # distance co-canal minimale mesuree sur le plan
    max_density_ab_km2: float                 # densite maximale supportee par le motif choisi
    problems: tuple[str, ...]                 # verifications en echec (vide = tout est correct)
    warnings: tuple[str, ...]                 # points a discuter (SIR, capacite, taille de grille)
    studies: Optional[StudiesConfig]
    density_rows: tuple[dict, ...]
    env_rows: tuple[dict, ...]


# ------------------------------------------------------------------ pipeline
def run_pipeline(params: Params, strategy: str = DEFAULT_STRATEGY,
                 rows: int = 7, cols: int = 7,
                 patterns: Iterable[int] = DEFAULT_PATTERNS,
                 with_studies: bool = True,
                 studies_config: Optional[StudiesConfig] = None) -> PipelineResult:
    """Enchaine P1 (radio) -> P2 (plan) -> P3 (allocation, etudes) et verifie la coherence."""
    if strategy not in STRATEGIES:
        raise ValueError(f"Strategie inconnue : {strategy!r} (attendu : {STRATEGIES})")

    # P1
    radio = compute_radio(params)
    comparison = tuple(compute_for_patterns(params, tuple(patterns)))

    # P2
    plan = build_plan(params.N, radio.R_km, rows, cols)

    # P3
    allocation = build_allocation(plan, params.N_f, strategy)

    # Verifications croisees
    problems = verify_allocation(allocation)
    problems += verify_cochannel_separation(plan, allocation, radio.D_km)
    d_measured = min_cochannel_distance_km(plan)
    if d_measured is not None and not math.isclose(d_measured, radio.D_km, rel_tol=1e-6):
        problems.append(f"D mesure ({d_measured:.3f} km) different de D theorique ({radio.D_km:.3f} km)")

    d_max = max_density_supported(params, params.N)

    # Avertissements (points a discuter dans le rapport)
    warnings: list[str] = []
    if not radio.SIR_ok:
        msg = (f"SIR = {radio.SIR_dB:.2f} dB < SIR_min = {params.SIR_min_dB:g} dB "
               f"pour N = {params.N}.")
        n_min = minimal_valid_pattern(params.Pathloss_exp, params.SIR_min_dB, n_max=params.N_f)
        msg += (f" Motif minimal valide : N = {n_min}." if n_min is not None
                else " Aucun motif valide avec ce nombre de canaux.")
        warnings.append(msg)
    if radio.Utilisateurs_actifs_cellule > radio.Canaux_par_cellule:
        warnings.append(
            f"Capacite insuffisante : {radio.Utilisateurs_actifs_cellule:.0f} utilisateurs actifs "
            f"par cellule pour {radio.Canaux_par_cellule:.1f} canaux "
            f"(densite maximale supportee : {d_max:.3f} ab./km2).")
    if rows < 7 or cols < 7:
        warnings.append(f"Grille {rows}x{cols} inferieure au minimum demande (7x7).")

    # Etudes (P3)
    studies = None
    density_rows: tuple[dict, ...] = ()
    env_rows: tuple[dict, ...] = ()
    if with_studies:
        studies = studies_config or load_studies_config()
        density_rows = tuple(density_study(params, studies.densities_ab_km2, studies.patterns))
        env_rows = tuple(environment_study(params, studies.environments,
                                           studies.zone_area_km2, studies.patterns))

    return PipelineResult(params=params, strategy=strategy, radio=radio, comparison=comparison,
                          plan=plan, allocation=allocation, d_measured_km=d_measured,
                          max_density_ab_km2=d_max, problems=tuple(problems),
                          warnings=tuple(warnings), studies=studies,
                          density_rows=density_rows, env_rows=env_rows)


# ------------------------------------------------------------------ synthese
def build_summary_text(result: PipelineResult) -> str:
    """Synthese textuelle (console, fichier .txt, onglet Export de l'application)."""
    p, r, a = result.params, result.radio, result.allocation
    sizes = [len(a.groups[g]) for g in sorted(a.groups)]
    d_mes = "n/a" if result.d_measured_km is None else f"{result.d_measured_km:.3f} km"
    lines = [
        "=== Synthese du plan cellulaire GSM ===",
        f"Motif choisi : N = {r.N} | strategie d'allocation : {result.strategy}",
        f"P_TX = {r.P_TX_dBm:.1f} dBm | MAPL = {r.MAPL_dB:.2f} dB | PL(d0) = {r.PL_d0_dB:.2f} dB",
        f"R = {r.R_km:.3f} km | D = {r.D_km:.3f} km (D/R = {r.D_sur_R:.3f})",
        f"SIR = {r.SIR_dB:.2f} dB (seuil {p.SIR_min_dB:g} dB) -> "
        f"{'OK' if r.SIR_ok else 'NON RESPECTE'}",
        f"Canaux / cellule = {r.Canaux_par_cellule:.2f} | Surface = {r.Surface_cellule_km2:.2f} km2",
        f"Abonnes / cellule = {r.Abonnes_cellule:.0f} | Actifs / cellule = "
        f"{r.Utilisateurs_actifs_cellule:.0f}",
        f"Plan : {result.plan.rows}x{result.plan.cols} = {len(result.plan.cells)} cellules | "
        f"D mesure (min co-canal) = {d_mes}",
        f"Allocation : tailles des groupes {sizes} | paires de canaux consecutifs "
        f"dans un meme groupe : {adjacent_pairs_in_same_group(a.groups)}",
        f"Densite maximale supportee : {result.max_density_ab_km2:.3f} ab./km2 "
        f"(params.json : {p.Dst_ab:g})",
        "Verifications : " + ("OK" if not result.problems else " ; ".join(result.problems)),
    ]
    if result.warnings:
        lines.append("Avertissements :")
        lines += [f" - {w}" for w in result.warnings]
    return "\n".join(lines)


# ------------------------------------------------------------------ exports
def _write_rows(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)


def export_all(result: PipelineResult, out_root: Optional[Path] = None) -> list[Path]:
    """Ecrit tous les livrables dans <out_root>/tables et <out_root>/figures.

    Par defaut : results/p4_final/. Retourne la liste des fichiers crees.
    """
    # imports ici : le calcul (run_pipeline) reste independant de matplotlib
    from planif.front_end import plots_plan, plots_radio, plots_studies

    if out_root is None:
        tables, figures = results_dir("p4_final", "tables"), results_dir("p4_final", "figures")
    else:
        out_root = Path(out_root)
        tables, figures = out_root / "tables", out_root / "figures"
        tables.mkdir(parents=True, exist_ok=True)
        figures.mkdir(parents=True, exist_ok=True)

    p, r, plan, alloc = result.params, result.radio, result.plan, result.allocation
    n, s = r.N, result.strategy
    files: list[Path] = []

    def keep(path: Path) -> Path:
        files.append(path)
        return path

    # ---- tables
    path = keep(tables / "p4_params_utilises.json")
    path.write_text(json.dumps(p.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    path = keep(tables / f"p4_resultats_radio_N{n}.json")
    path.write_text(json.dumps(r.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    path = keep(tables / "p4_tableau_comparatif_N3_7_9.csv")
    header = ["Motif (N)", "R (km)", "D (km)", "SIR (dB)", "Canaux / cellule",
              "Abonnes / cellule", "Utilisateurs actifs / cellule", "SIR >= SIR_min"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        for c in result.comparison:
            w.writerow([c.N, f"{c.R_km:.3f}", f"{c.D_km:.3f}", f"{c.SIR_dB:.2f}",
                        f"{c.Canaux_par_cellule:.2f}", f"{c.Abonnes_cellule:.0f}",
                        f"{c.Utilisateurs_actifs_cellule:.0f}", "oui" if c.SIR_ok else "non"])

    cell_by_id = {c.cell_id: c for c in plan.cells}
    path = keep(tables / f"p4_allocation_cellules_{s}_N{n}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["cell_id", "row", "col", "groupe", "nb_canaux", "canaux"])
        for a in alloc.assignments:
            c = cell_by_id[a.cell_id]
            w.writerow([a.cell_id, c.row, c.col, a.group, len(a.channels),
                        " ".join(map(str, a.channels))])

    path = keep(tables / f"p4_groupes_{s}_N{n}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["groupe", "nb_canaux", "canaux"])
        for g in sorted(alloc.groups):
            w.writerow([g, len(alloc.groups[g]), " ".join(map(str, alloc.groups[g]))])

    if result.density_rows:
        _write_rows(list(result.density_rows), keep(tables / "p4_etude_densite.csv"))
    if result.env_rows:
        _write_rows(list(result.env_rows), keep(tables / "p4_etude_environnement.csv"))

    path = keep(tables / "p4_synthese.txt")
    path.write_text(build_summary_text(result), encoding="utf-8")

    # ---- figures
    keep(plots_plan.plot_plan(plan, figures / f"fig_p4_plan_{plan.rows}x{plan.cols}_N{n}_{s}.png",
                              allocation=alloc))
    keep(plots_radio.plot_path_loss_vs_distance(p, r, figures / "fig_p4_bilan_liaison_PL_vs_d.png"))
    keep(plots_radio.plot_sir_vs_pattern(p, result.comparison, figures / "fig_p4_sir_vs_motif.png"))
    keep(plots_radio.plot_capacity(result.comparison, figures / "fig_p4_canaux_vs_utilisateurs.png"))

    both = {strat: build_allocation(plan, p.N_f, strat) for strat in STRATEGIES}
    keep(plots_studies.plot_allocation_comparison(
        both["contigue"], both["entrelacee"],
        figures / f"fig_p4_allocation_contigue_vs_entrelacee_N{n}.png"))

    if result.density_rows:
        keep(plots_studies.plot_density_vs_channels(
            list(result.density_rows), figures / "fig_p4_densite_vs_canaux.png"))
    if result.env_rows:
        keep(plots_studies.plot_environment_radius_sites(
            list(result.env_rows), figures / "fig_p4_environnement_R_sites.png"))
        keep(plots_studies.plot_environment_sir(
            list(result.env_rows), p.SIR_min_dB, figures / "fig_p4_environnement_sir.png"))

    return files