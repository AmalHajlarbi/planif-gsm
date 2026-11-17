"""Figures des options d'amelioration (enonce, section 6). Aucun calcul radio ici."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon
from matplotlib.ticker import FormatStrFormatter

from planif.back_end.extensions import ClusterMap, cluster_hull, km_to_latlon
from planif.front_end.style import (BLUE, GREEN, INK, ORANGE, PANEL, RED, apply_style,
                                    group_colors, text_color)

apply_style()
FIGSIZE = (7, 4.5)    # meme format que les figures de P1 : alignement garanti


def _save(fig, out_path: Path, **kwargs) -> Path:
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, **kwargs)
    plt.close(fig)
    return out_path


def _mark_envs(ax, environments: dict[str, float]) -> None:
    for name, n_exp in environments.items():
        ax.axvline(n_exp, color="#9AA5B1", linestyle=":", lw=1.2)
        ax.text(n_exp, 0.98, f" {name} (n = {n_exp:g})", transform=ax.get_xaxis_transform(),
                rotation=90, va="top", ha="right", fontsize=8, color="#5B6677")


# ------------------------------------------------------------ 1) motifs
def plot_pattern_sir(rows: Sequence[dict], sir_min_db: float, out_path: Path) -> Path:
    labels = [f"N = {r['N']}" for r in rows]
    vals = [r["SIR_dB"] for r in rows]
    colors = [GREEN if r["SIR_ok"] else RED for r in rows]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.bar(labels, vals, color=colors, width=0.6)
    ax.axhline(sir_min_db, color=INK, linestyle="--", lw=1.4, label=f"SIR_min = {sir_min_db:g} dB")
    ax.bar_label(bars, labels=[f"{v:.1f}" for v in vals], padding=3, fontsize=9)
    for bar, r in zip(bars, rows):
        if r.get("Motif_minimal"):
            ax.annotate("motif minimal\nvalide", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 26), textcoords="offset points", ha="center", fontsize=8,
                        fontweight="bold", color=GREEN,
                        arrowprops=dict(arrowstyle="-", color=GREEN))
    ax.set_ylim(min(0.0, min(vals) * 1.1), max(max(vals), sir_min_db) * 1.3)
    handles, _ = ax.get_legend_handles_labels()
    handles += [Patch(color=GREEN, label="SIR conforme"), Patch(color=RED, label="SIR insuffisant")]
    ax.legend(handles=handles, loc="upper left")
    ax.set_ylabel("SIR (dB)")
    ax.set_title("SIR selon le motif cellulaire")
    ax.grid(axis="x", visible=False)
    return _save(fig, out_path)


def plot_pattern_capacity(rows: Sequence[dict], out_path: Path) -> Path:
    labels = [f"N = {r['N']}" for r in rows]
    channels = [r["Canaux_par_cellule"] for r in rows]
    colors = [GREEN if r["SIR_ok"] else RED for r in rows]
    actives = rows[0]["Actifs_par_cellule"]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.bar(labels, channels, color=colors, width=0.6)
    ax.bar_label(bars, labels=[f"{v:.1f}" for v in channels], padding=2, fontsize=8)
    ax.axhline(actives, color=ORANGE, lw=2, label=f"Utilisateurs actifs / cellule = {actives:.0f}")
    ax.set_yscale("log")
    ax.set_ylim(min(channels) / 2, max(max(channels), actives) * 3)
    handles, _ = ax.get_legend_handles_labels()
    handles += [Patch(color=GREEN, label="SIR conforme"), Patch(color=RED, label="SIR insuffisant")]
    ax.legend(handles=handles, loc="upper right", fontsize=8)
    ax.set_ylabel("Canaux par cellule (échelle log)")
    ax.set_title("Compromis : plus N est grand, moins il y a de canaux")
    ax.grid(axis="x", visible=False)
    return _save(fig, out_path)


# ---------------------------------------------------------- 2) exposants
def plot_exponent_radius_sites(rows: Sequence[dict], environments: dict[str, float],
                               out_path: Path) -> Path:
    exps = sorted({r["Pathloss_exp"] for r in rows})
    first = {e: next(r for r in rows if r["Pathloss_exp"] == e) for e in exps}

    fig, ax = plt.subplots(figsize=FIGSIZE)
    l1, = ax.plot(exps, [first[e]["R_km"] for e in exps], color=BLUE, lw=2.2, marker="o",
                  ms=4, label="Rayon R (km)")
    ax.set_ylabel("Rayon de cellule R (km)", color=BLUE)
    ax2 = ax.twinx()
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    l2, = ax2.plot(exps, [first[e]["Sites_necessaires"] for e in exps], color=ORANGE, lw=2.2,
                   marker="s", ms=4, label="Sites nécessaires")
    ax2.set_ylabel("Nombre de sites", color=ORANGE)
    _mark_envs(ax, environments)
    ax.set_xlabel("Exposant d'affaiblissement n")
    ax.set_title("Impact de l'exposant n sur R et sur le nombre de sites")
    ax.legend(handles=[l1, l2], loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    return _save(fig, out_path)


def plot_exponent_sir(rows: Sequence[dict], sir_min_db: float, environments: dict[str, float],
                      out_path: Path) -> Path:
    patterns = sorted({r["N"] for r in rows})
    colors = group_colors(len(patterns))

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for k, n_cells in enumerate(patterns, start=1):
        pts = sorted((r["Pathloss_exp"], r["SIR_dB"]) for r in rows if r["N"] == n_cells)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=colors[k], lw=2, marker="o",
                ms=3, label=f"N = {n_cells}")
    ax.axhline(sir_min_db, color=INK, linestyle="--", lw=1.4, label=f"SIR_min = {sir_min_db:g} dB")
    _mark_envs(ax, environments)
    ax.set_xlabel("Exposant d'affaiblissement n")
    ax.set_ylabel("SIR (dB)")
    ax.set_title("SIR selon l'exposant n et le motif N")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    return _save(fig, out_path)


# --------------------------------------------------- 3) carte des clusters
def plot_cluster_map(cmap: ClusterMap, out_path: Path) -> Path:
    colors = group_colors(cmap.N)
    lat0, lon0 = cmap.center_lat, cmap.center_lon

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_facecolor(PANEL)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for c in cmap.cells:
        ring = [(lon, lat) for lat, lon in c.vertices]
        ax.add_patch(Polygon(ring, closed=True, facecolor=colors[c.group], edgecolor="white",
                             linewidth=1.2, alpha=1.0 if c.in_zone else 0.35, zorder=2))
        ax.text(c.lon, c.lat, str(c.group), ha="center", va="center", fontsize=9,
                fontweight="bold", zorder=4, alpha=1.0 if c.in_zone else 0.6,
                color=text_color(colors[c.group]) if c.in_zone else INK)

    for cid in range(1, cmap.n_clusters + 1):
        hull = cluster_hull(cmap, cid)
        ax.add_patch(Polygon([(lon, lat) for lat, lon in hull], closed=True, fill=False,
                             edgecolor=INK, linewidth=2, linestyle="--", zorder=5))
        top_lat, top_lon = max(hull)
        ax.annotate(f"C{cid}", (top_lon, top_lat), xytext=(0, 8), textcoords="offset points",
                    ha="center", fontsize=9, fontweight="bold", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=INK, edgecolor=INK),
                    color="white")

    rz = cmap.zone_radius_km
    ring = [km_to_latlon(rz * math.cos(t), rz * math.sin(t), lat0, lon0)
            for t in np.linspace(0, 2 * math.pi, 240)]
    ax.plot([p[1] for p in ring], [p[0] for p in ring], color=RED, linestyle="--", lw=1.6, zorder=6)

    lats = [v[0] for c in cmap.cells for v in c.vertices] + [p[0] for p in ring]
    lons = [v[1] for c in cmap.cells for v in c.vertices] + [p[1] for p in ring]
    mlat = (max(lats) - min(lats)) * 0.04
    mlon = (max(lons) - min(lons)) * 0.04
    ax.set_xlim(min(lons) - mlon, max(lons) + mlon)
    ax.set_ylim(min(lats) - mlat, max(lats) + mlat)
    ax.set_aspect(1.0 / math.cos(math.radians(lat0)))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.2f°"))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f°"))
    ax.set_xlabel("Longitude (coordonnées GPS fictives)")
    ax.set_ylabel("Latitude (coordonnées GPS fictives)")
    ax.set_title(f"Positionnement automatique de {cmap.n_clusters} clusters (N = {cmap.N}) : "
                 f"{cmap.n_cells} cellules\nZone à couvrir : rayon {rz:.1f} km, R = {cmap.R_km:.2f} km")

    handles = [Patch(facecolor=colors[g], edgecolor="white", label=f"Groupe {g}")
               for g in range(1, cmap.N + 1)]
    handles += [Line2D([0], [0], color=INK, linestyle="--", lw=2, label="Cluster (C1, C2…)"),
                Line2D([0], [0], color=RED, linestyle="--", lw=1.6, label="Zone à couvrir")]
    ax.legend(handles=handles, title="Groupes de fréquences", loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncol=min(cmap.N + 2, 5))
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path