"""Figure du plan cellulaire hexagonal (aucun calcul radio ici : on trace seulement)."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon

from planif.back_end.hex_grid import distance_km, hex_vertices
from planif.contracts import CellularPlan, FrequencyAllocation
from planif.front_end.style import INK, PANEL, apply_style, group_colors, text_color

apply_style()


def _reference_pair(plan: CellularPlan):
    """Cellule la plus proche du centre + sa plus proche cellule co-canal (pour tracer D)."""
    cx = sum(c.x_km for c in plan.cells) / len(plan.cells)
    cy = sum(c.y_km for c in plan.cells) / len(plan.cells)
    ref = min(plan.cells, key=lambda c: math.hypot(c.x_km - cx, c.y_km - cy))
    others = [c for c in plan.cells if c.group == ref.group and c.cell_id != ref.cell_id]
    if not others:
        return None
    return ref, min(others, key=lambda c: distance_km(ref, c))


def plot_plan(plan: CellularPlan, out_path: Path,
              allocation: Optional[FrequencyAllocation] = None,
              show_cochannel: bool = True) -> Path:
    """Exporte le plan cellulaire en PNG legende.

    - une couleur par groupe de frequences, numero du groupe dans chaque cellule ;
    - legende sous la carte (avec le nombre de canaux si `allocation` est fournie) ;
    - option : fleche materialisant la distance de reutilisation D entre deux cellules co-canal.
    """
    colors = group_colors(plan.N)
    pair = _reference_pair(plan) if show_cochannel else None
    highlighted = {pair[0].cell_id, pair[1].cell_id} if pair else set()

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_facecolor(PANEL)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for c in plan.cells:
        hl = c.cell_id in highlighted
        ax.add_patch(Polygon(hex_vertices(c.x_km, c.y_km, plan.R_km), closed=True,
                             facecolor=colors[c.group],
                             edgecolor=INK if hl else "white",
                             linewidth=2.6 if hl else 1.6, zorder=3 if hl else 2))
        ax.text(c.x_km, c.y_km, str(c.group), ha="center", va="center", fontsize=11,
                fontweight="bold", color=text_color(colors[c.group]), zorder=4)

    if pair:
        a, b = pair
        ax.annotate("", xy=(b.x_km, b.y_km), xytext=(a.x_km, a.y_km), zorder=5,
                    arrowprops=dict(arrowstyle="<|-|>", color=INK, lw=1.8,
                                    shrinkA=0, shrinkB=0))
        ax.text((a.x_km + b.x_km) / 2, (a.y_km + b.y_km) / 2,
                f"D = {distance_km(a, b):.2f} km", ha="center", va="center",
                fontsize=10, fontweight="bold", zorder=6,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=INK, alpha=0.95))

    handles = []
    for g in range(1, plan.N + 1):
        label = f"Groupe {g}"
        if allocation is not None and g in allocation.groups:
            label += f" ({len(allocation.groups[g])} canaux)"
        handles.append(Patch(facecolor=colors[g], edgecolor="white", label=label))
    ax.legend(handles=handles, title="Groupes de fréquences", loc="upper center",
              bbox_to_anchor=(0.5, -0.09), ncol=min(plan.N, 4))

    xs = [v[0] for c in plan.cells for v in hex_vertices(c.x_km, c.y_km, plan.R_km)]
    ys = [v[1] for c in plan.cells for v in hex_vertices(c.x_km, c.y_km, plan.R_km)]
    margin = plan.R_km * 0.5
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    ax.set_aspect("equal")
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_title(f"Plan cellulaire {plan.rows}×{plan.cols} : motif N = {plan.N}, "
                 f"R = {plan.R_km:.2f} km")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path