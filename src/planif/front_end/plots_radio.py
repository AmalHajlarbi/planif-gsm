"""Figures de la phase 1 (calcul radio). Aucune logique de calcul ici : on trace seulement."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from planif.contracts import Params, RadioResults
from planif.front_end.style import BLUE, GREEN, INK, ORANGE, RED, apply_style

apply_style()
FIGSIZE = (7, 4.5)   # meme format pour les 3 figures : alignement garanti dans l'application


def _save(fig, out_path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def plot_path_loss_vs_distance(params: Params, res: RadioResults, out_path: Path) -> Path:
    """Figure 1 : PL(d) en fonction de d, avec la droite MAPL et le rayon R a l'intersection."""
    d = np.linspace(params.d0_km, res.R_km * 1.6, 300)
    pl = res.PL_d0_dB + 10.0 * params.Pathloss_exp * np.log10(d / params.d0_km)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.axvspan(params.d0_km, res.R_km, color=GREEN, alpha=0.08, label="Zone couverte (d ≤ R)")
    ax.plot(d, pl, color=BLUE, lw=2.2, label=f"PL(d), n = {params.Pathloss_exp:g}")
    ax.axhline(res.MAPL_dB, color=RED, linestyle="--", lw=1.5, label=f"MAPL = {res.MAPL_dB:.1f} dB")
    ax.axvline(res.R_km, color=GREEN, linestyle=":", lw=1.8, label=f"R = {res.R_km:.2f} km")
    ax.plot([res.R_km], [res.MAPL_dB], "o", color=INK, ms=7, zorder=5)
    ax.annotate(f"R = {res.R_km:.2f} km", (res.R_km, res.MAPL_dB), xytext=(10, -22),
                textcoords="offset points", fontsize=9, fontweight="bold")
    ax.set_xlabel("Distance d (km)")
    ax.set_ylabel("Affaiblissement de parcours (dB)")
    ax.set_title("Bilan de liaison : PL(R) = MAPL")
    ax.legend(loc="lower right")
    return _save(fig, out_path)


def plot_sir_vs_pattern(params: Params, results: Sequence[RadioResults], out_path: Path) -> Path:
    """Figure 2 : SIR obtenu pour chaque motif N, compare au seuil SIR_min."""
    labels = [f"N = {r.N}" for r in results]
    values = [r.SIR_dB for r in results]
    colors = [GREEN if r.SIR_ok else RED for r in results]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.bar(labels, values, color=colors, width=0.55)
    ax.axhline(params.SIR_min_dB, color=INK, linestyle="--", lw=1.4,
               label=f"SIR_min = {params.SIR_min_dB:g} dB")
    ax.bar_label(bars, labels=[f"{v:.2f} dB" for v in values], padding=3, fontsize=9)
    top = max(max(values), params.SIR_min_dB)
    ax.set_ylim(min(0.0, min(values) * 1.1), top * 1.22)
    ax.set_ylabel("SIR (dB)")
    ax.set_title("Critère SIR ≥ SIR_min selon le motif")
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
    return _save(fig, out_path)


def plot_capacity(results: Sequence[RadioResults], out_path: Path) -> Path:
    """Figure 3 : canaux disponibles par cellule vs utilisateurs actifs simultanes par cellule."""
    x = np.arange(len(results))
    w = 0.36
    channels = [r.Canaux_par_cellule for r in results]
    actives = [r.Utilisateurs_actifs_cellule for r in results]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    b1 = ax.bar(x - w / 2, channels, w, label="Canaux par cellule (N_f / N)", color=BLUE)
    b2 = ax.bar(x + w / 2, actives, w, label="Utilisateurs actifs par cellule", color=ORANGE)
    ax.bar_label(b1, labels=[f"{v:.1f}" for v in channels], padding=2, fontsize=8)
    ax.bar_label(b2, labels=[f"{v:.0f}" for v in actives], padding=2, fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"N = {r.N}" for r in results])
    ax.set_yscale("log")
    positives = [v for v in channels + actives if v > 0] or [1.0]
    ax.set_ylim(min(positives) / 2, max(positives) * 6)
    ax.set_ylabel("Nombre (échelle log)")
    ax.set_title("Dimensionnement : canaux vs utilisateurs actifs")
    ax.legend(loc="upper right")
    ax.grid(axis="x", visible=False)
    return _save(fig, out_path)