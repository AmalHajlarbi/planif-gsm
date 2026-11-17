"""Coloration (groupes de frequences) d'un reseau hexagonal selon le motif N.

Fonctions pures : pas de geometrie en km, uniquement des coordonnees hexagonales
axiales (q, r) entieres.

Principe : un motif N = i^2 + i*j + j^2 engendre un reseau de "cellules
co-canal" de vecteurs de base u = (i, j) et v = (-j, i + j) en coordonnees
axiales. Deux cellules ont le meme groupe si et seulement si leur difference
est une combinaison entiere de u et v.
"""
from __future__ import annotations

from functools import lru_cache

from planif.back_end.radio_models import is_valid_cluster_size


def cluster_ij(n_cells: int) -> tuple[int, int]:
    """Retourne (i, j) avec i >= j >= 0 et i^2 + i*j + j^2 = N (ex: 7 -> (2, 1))."""
    if not is_valid_cluster_size(n_cells):
        raise ValueError(f"N={n_cells} n'est pas de la forme i^2 + i*j + j^2")
    for i in range(n_cells + 1):
        for j in range(i + 1):
            if (i, j) != (0, 0) and i * i + i * j + j * j == n_cells:
                return i, j
    raise ValueError(f"Aucun couple (i, j) pour N={n_cells}")  # ne devrait pas arriver


def _coset_key(q: int, r: int, i: int, j: int, n_cells: int) -> tuple[int, int]:
    """Cle identifiant la classe de (q, r) modulo le reseau co-canal."""
    s = ((i + j) * q + j * r) % n_cells
    t = (-j * q + i * r) % n_cells
    return s, t


@lru_cache(maxsize=None)
def _group_table(n_cells: int) -> dict[tuple[int, int], int]:
    """Associe a chaque classe un numero de groupe 1..N (ordre stable)."""
    i, j = cluster_ij(n_cells)
    keys = {_coset_key(q, r, i, j, n_cells) for q in range(n_cells) for r in range(n_cells)}
    if len(keys) != n_cells:
        raise RuntimeError(f"Coloration incoherente pour N={n_cells} : {len(keys)} classes")
    return {key: idx for idx, key in enumerate(sorted(keys), start=1)}


def group_of(q: int, r: int, n_cells: int) -> int:
    """Numero de groupe (1..N) de la cellule de coordonnees axiales (q, r)."""
    i, j = cluster_ij(n_cells)
    return _group_table(n_cells)[_coset_key(q, r, i, j, n_cells)]