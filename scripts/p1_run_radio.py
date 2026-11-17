"""Phase 1 : calcul radio + sauvegarde des tableaux + generation des figures.

Executer depuis la racine du projet (planif-gsm/) :
    python scripts/p1_run_radio.py
"""
from __future__ import annotations

import csv
import json

from planif.back_end.calculator import compute_for_patterns, compute_radio
from planif.back_end.params_io import load_params
from planif.front_end import plots_radio
from planif.paths import DEFAULT_PARAMS_FILE, results_dir

PATTERNS = (3, 7, 9)  # tableau comparatif de l'enonce (section 7)


def main() -> None:
    params = load_params(DEFAULT_PARAMS_FILE)
    tables = results_dir("p1_radio", "tables")
    figures = results_dir("p1_radio", "figures")

    # --- 1) Resultat pour le motif choisi dans params.json
    res = compute_radio(params)
    print(f"=== Motif choisi : N = {res.N} ===")
    print(f"P_TX                : {res.P_TX_dBm:.1f} dBm")
    print(f"MAPL                : {res.MAPL_dB:.2f} dB")
    print(f"PL(d0)              : {res.PL_d0_dB:.2f} dB")
    print(f"Rayon R             : {res.R_km:.3f} km")
    print(f"Distance reuse. D   : {res.D_km:.3f} km  (D/R = {res.D_sur_R:.3f})")
    print(f"SIR obtenu          : {res.SIR_dB:.2f} dB  (seuil {params.SIR_min_dB:g} dB) -> "
          f"{'OK' if res.SIR_ok else 'NON RESPECTE'}")
    print(f"Canaux / cellule    : {res.Canaux_par_cellule:.2f}")
    print(f"Surface cellule     : {res.Surface_cellule_km2:.2f} km2")
    print(f"Abonnes / cellule   : {res.Abonnes_cellule:.0f}")
    print(f"Utilisateurs actifs : {res.Utilisateurs_actifs_cellule:.0f}")

    with open(tables / f"p1_resultats_N{res.N}.json", "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)

    # --- 2) Tableau comparatif N = 3, 7, 9 (modele de l'enonce, section 7)
    results = compute_for_patterns(params, PATTERNS)
    csv_path = tables / "p1_tableau_comparatif_N3_7_9.csv"
    header = ["Motif (N)", "R (km)", "D (km)", "SIR (dB)", "Canaux / cellule",
              "Abonnes / cellule", "Utilisateurs actifs / cellule", "SIR >= SIR_min"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        for r in results:
            writer.writerow([r.N, f"{r.R_km:.3f}", f"{r.D_km:.3f}", f"{r.SIR_dB:.2f}",
                             f"{r.Canaux_par_cellule:.2f}", f"{r.Abonnes_cellule:.0f}",
                             f"{r.Utilisateurs_actifs_cellule:.0f}", "oui" if r.SIR_ok else "non"])

    print("\n=== Tableau comparatif ===")
    print(" | ".join(header))
    for r in results:
        print(f"{r.N} | {r.R_km:.3f} | {r.D_km:.3f} | {r.SIR_dB:.2f} | "
              f"{r.Canaux_par_cellule:.2f} | {r.Abonnes_cellule:.0f} | "
              f"{r.Utilisateurs_actifs_cellule:.0f} | {'oui' if r.SIR_ok else 'non'}")

    with open(tables / "p1_tableau_comparatif_N3_7_9.json", "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in results], f, indent=2, ensure_ascii=False)

    # --- 3) Figures
    p1 = plots_radio.plot_path_loss_vs_distance(params, res, figures / "fig_p1_bilan_liaison_PL_vs_d.png")
    p2 = plots_radio.plot_sir_vs_pattern(params, results, figures / "fig_p1_sir_vs_motif.png")
    p3 = plots_radio.plot_capacity(results, figures / "fig_p1_canaux_vs_utilisateurs.png")

    print("\nFichiers generes :")
    for p in (csv_path, p1, p2, p3):
        print(" -", p)


if __name__ == "__main__":
    main()