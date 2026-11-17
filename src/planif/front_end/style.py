"""Style graphique commun a toutes les figures : palette, polices, grilles."""
from __future__ import annotations

import colorsys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cycler

# Couleurs semantiques
BLUE, ORANGE, GREEN, RED = "#3B6FB6", "#E8833A", "#3E9B6B", "#D1495B"
INK = "#1F2937"      # texte
GRID = "#D9DEE7"     # grilles
PANEL = "#F6F8FB"    # fond des plans

# Palette des groupes de frequences (douce, contrastee, lisible)
GROUP_PALETTE = [
    "#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#9C755F", "#76B7B2",
    "#EDC948", "#FF9DA7", "#86BCB6", "#A0CBE8", "#D4A6C8", "#8CD17D", "#FFBE7D",
    "#BAB0AC", "#D37295", "#499894", "#B6992D", "#79706E", "#FABFD2",
]


def group_colors(n_groups: int) -> dict[int, str]:
    """Couleur (hexadecimal) de chaque groupe 1..N."""
    colors = {}
    for g in range(1, n_groups + 1):
        if g <= len(GROUP_PALETTE):
            colors[g] = GROUP_PALETTE[g - 1]
        else:  # plus de 20 groupes : teintes reparties uniformement
            r, gr, b = colorsys.hsv_to_rgb((g * 0.618) % 1.0, 0.45, 0.85)
            colors[g] = "#{:02X}{:02X}{:02X}".format(int(r * 255), int(gr * 255), int(b * 255))
    return colors


def text_color(hex_color: str) -> str:
    """Blanc sur fond sombre, encre sur fond clair."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#FFFFFF" if 0.299 * r + 0.587 * g + 0.114 * b < 140 else INK


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "axes.edgecolor": "#9AA5B1", "axes.labelcolor": INK, "axes.titlecolor": INK,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.labelsize": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.8,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "legend.frameon": False, "legend.fontsize": 9,
        "axes.prop_cycle": cycler(color=GROUP_PALETTE[:10]),
    })