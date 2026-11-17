"""Figures de la phase 3 (allocation et etudes). Aucun calcul radio ici."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from planif.contracts import FrequencyAllocation
from planif.front_end.style import BLUE, ORANGE, apply_style, group_colors

apply_style()

def plot_allocation_comparison(alloc_a: FrequencyAllocation, alloc_b: FrequencyAllocation,
                               out_path: Path) -> Path:
    """Figure : groupe (ligne) x canal (colonne), pour deux strategies cote a cote."""
    n_groups = alloc_a.N
    colors = group_colors(n_groups)
    cmap = ListedColormap([colors[g] for g in range(1, n_groups + 1)])

    fig, axes = plt.subplots(2, 1, figsize=(11, 4.8), sharex=True)
    for ax, alloc in zip(axes, (alloc_a, alloc_b)):
        grid = np.full((n_groups, alloc.N_f), np.nan)
        for g, channels in alloc.groups.items():
            for c in channels:
                grid[g - 1, c - 1] = g
        ax.imshow(grid, aspect="auto", cmap=cmap, vmin=0.5, vmax=n_groups + 0.5,
                  interpolation="nearest", extent=(0.5, alloc.N_f + 0.5, n_groups + 0.5, 0.5))
        ax.set_yticks(range(1, n_groups + 1))
        ax.set_ylabel("Groupe")
        ax.set_title(f"Allocation {alloc.strategy} (N_f = {alloc.N_f}, N = {alloc.N})")
    axes[-1].set_xlabel("Numero de canal")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def plot_density_vs_channels(rows: Sequence[dict], out_path: Path) -> Path:
    """Figure : utilisateurs actifs par cellule vs densite, avec les canaux disponibles (par N)."""
    patterns = sorted({r["N"] for r in rows})
    fig, ax = plt.subplots(figsize=(9, 5))

    first = [r for r in rows if r["N"] == patterns[0]]
    ax.plot([r["Dst_ab"] for r in first], [r["Utilisateurs_actifs"] for r in first],
            "o-", color="black", label="Utilisateurs actifs / cellule")
    for n_cells in patterns:
        row = next(r for r in rows if r["N"] == n_cells)
        ax.axhline(row["Canaux_par_cellule"], linestyle="--",
                   label=f"Canaux / cellule, N = {n_cells} ({row['Canaux_par_cellule']:.1f})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Densite d'abonnes (ab./km2)")
    ax.set_ylabel("Nombre par cellule (echelle log)")
    ax.set_title("Impact de la densite d'abonnes sur le dimensionnement en canaux")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def plot_environment_radius_sites(rows: Sequence[dict], out_path: Path) -> Path:
    """Figure : rayon de cellule R et nombre de sites selon l'environnement."""
    envs = list(dict.fromkeys(r["Environnement"] for r in rows))
    firsts = [next(r for r in rows if r["Environnement"] == e) for e in envs]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 5))

    bars = ax1.bar(envs, [r["R_km"] for r in firsts], color=BLUE)
    ax1.bar_label(bars, fmt="%.1f")
    ax1.set_ylabel("Rayon de cellule R (km)")
    ax1.set_title("Rayon de cellule")

    bars = ax2.bar(envs, [r["Sites_necessaires"] for r in firsts], color=ORANGE)
    ax2.bar_label(bars)
    ax2.set_ylabel("Nombre de sites")
    ax2.set_title("Sites necessaires pour couvrir la zone")
    for ax in (ax1, ax2):
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Impact de l'environnement (exposant d'affaiblissement)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def plot_environment_sir(rows: Sequence[dict], sir_min_db: float, out_path: Path) -> Path:
    """Figure : SIR par motif et par environnement, compare a SIR_min."""
    envs = list(dict.fromkeys(r["Environnement"] for r in rows))
    patterns = sorted({r["N"] for r in rows})
    x = np.arange(len(patterns))
    w = 0.8 / len(envs)

    fig, ax = plt.subplots(figsize=(9, 5))
    for k, env in enumerate(envs):
        vals = [next(r["SIR_dB"] for r in rows if r["Environnement"] == env and r["N"] == n)
                for n in patterns]
        n_exp = next(r["Pathloss_exp"] for r in rows if r["Environnement"] == env)
        ax.bar(x + k * w - 0.4 + w / 2, vals, w, label=f"{env} (n = {n_exp:g})")
    ax.axhline(sir_min_db, color="black", linestyle="--", label=f"SIR_min = {sir_min_db:g} dB")
    ax.set_xticks(x)
    ax.set_xticklabels([f"N = {n}" for n in patterns])
    ax.set_ylabel("SIR (dB)")
    ax.set_title("SIR obtenu selon le motif et l'environnement")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path