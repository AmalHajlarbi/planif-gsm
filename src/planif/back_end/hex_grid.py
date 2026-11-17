"""Geometrie hexagonale et construction du plan cellulaire.

Convention : hexagones "pointe en haut", grille rows x cols en decalage "odd-r"
(les lignes impaires sont decalees d'une demi-cellule vers la droite).
R = rayon de la cellule = distance centre -> sommet (km).
Distance entre centres de deux cellules voisines = sqrt(3) * R.
"""
from __future__ import annotations

import math

from planif.back_end.coloring import group_of
from planif.back_end.radio_models import is_valid_cluster_size
from planif.contracts import Cell, CellularPlan

SQRT3 = math.sqrt(3.0)


def offset_to_axial(row: int, col: int) -> tuple[int, int]:
    """Decalage odd-r (row, col) -> coordonnees axiales (q, r)."""
    return col - (row - (row & 1)) // 2, row


def axial_to_xy_km(q: int, r: int, r_km: float) -> tuple[float, float]:
    """Centre de la cellule (x, y) en km."""
    return SQRT3 * r_km * (q + r / 2.0), 1.5 * r_km * r


def hex_vertices(x_km: float, y_km: float, r_km: float) -> list[tuple[float, float]]:
    """6 sommets d'un hexagone pointe en haut, centre (x, y), rayon R."""
    return [
        (x_km + r_km * math.cos(math.radians(90 + 60 * k)),
         y_km + r_km * math.sin(math.radians(90 + 60 * k)))
        for k in range(6)
    ]


def distance_km(a: Cell, b: Cell) -> float:
    """Distance euclidienne entre les centres de deux cellules."""
    return math.hypot(a.x_km - b.x_km, a.y_km - b.y_km)


def build_plan(n_cells: int, r_km: float, rows: int = 7, cols: int = 7) -> CellularPlan:
    """Construit le plan cellulaire rows x cols avec le groupe de chaque cellule."""
    if not is_valid_cluster_size(n_cells):
        raise ValueError(f"N={n_cells} n'est pas un motif hexagonal valide")
    if r_km <= 0:
        raise ValueError("Le rayon R doit etre > 0")
    if rows < 1 or cols < 1:
        raise ValueError("rows et cols doivent etre >= 1")

    cells = []
    for row in range(rows):
        for col in range(cols):
            q, r = offset_to_axial(row, col)
            x, y = axial_to_xy_km(q, r, r_km)
            cells.append(Cell(
                cell_id=row * cols + col,
                q=q, r=r, row=row, col=col,
                x_km=x, y_km=y,
                group=group_of(q, r, n_cells),
            ))
    return CellularPlan(N=n_cells, R_km=r_km, rows=rows, cols=cols, cells=tuple(cells))


def min_cochannel_distance_km(plan: CellularPlan) -> float | None:
    """Plus petite distance entre deux cellules du meme groupe (None s'il n'y en a pas)."""
    best = None
    cells = plan.cells
    for a in range(len(cells)):
        for b in range(a + 1, len(cells)):
            if cells[a].group == cells[b].group:
                d = distance_km(cells[a], cells[b])
                if best is None or d < best:
                    best = d
    return best