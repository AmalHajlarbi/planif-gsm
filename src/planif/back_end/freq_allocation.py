"""Allocation des N_f canaux aux N groupes de frequences (enonce, section 4.5).

Les canaux sont numerotes de 1 a N_f, les groupes de 1 a N.
Les N_f mod N canaux "restants" vont aux premiers groupes (aucun canal perdu).
Ce module ne depend pas de la geometrie : il utilise seulement les contrats.
"""
from __future__ import annotations

import math

from planif.contracts import CellAssignment, CellularPlan, FrequencyAllocation

STRATEGIES = ("contigue", "entrelacee")


def group_sizes(n_f: int, n_groups: int) -> list[int]:
    """Taille de chaque groupe (liste d'indice 0 = groupe 1) : repartition la plus equilibree."""
    if n_groups < 1:
        raise ValueError("Le nombre de groupes N doit etre >= 1")
    if n_f < n_groups:
        raise ValueError(f"N_f={n_f} < N={n_groups} : impossible d'avoir un canal par groupe")
    base, extra = divmod(n_f, n_groups)
    return [base + 1 if g < extra else base for g in range(n_groups)]


def allocate(n_f: int, n_cells: int, strategy: str) -> dict[int, tuple[int, ...]]:
    """Retourne {groupe: (canaux,...)} selon la strategie 'contigue' ou 'entrelacee'."""
    sizes = group_sizes(n_f, n_cells)

    if strategy == "contigue":
        groups: dict[int, tuple[int, ...]] = {}
        start = 1
        for g, size in enumerate(sizes, start=1):
            groups[g] = tuple(range(start, start + size))
            start += size
        return groups

    if strategy == "entrelacee":
        tmp: dict[int, list[int]] = {g: [] for g in range(1, n_cells + 1)}
        for channel in range(1, n_f + 1):
            tmp[(channel - 1) % n_cells + 1].append(channel)   # round-robin
        return {g: tuple(chs) for g, chs in tmp.items()}

    raise ValueError(f"Strategie inconnue : {strategy!r} (attendu : {STRATEGIES})")


def assign_to_cells(plan: CellularPlan, groups: dict[int, tuple[int, ...]]) -> tuple[CellAssignment, ...]:
    """Associe a chaque cellule son groupe ET la liste exacte de ses canaux."""
    assignments = []
    for cell in plan.cells:
        if cell.group not in groups:
            raise ValueError(f"Groupe {cell.group} (cellule {cell.cell_id}) absent de l'allocation")
        assignments.append(CellAssignment(cell_id=cell.cell_id, group=cell.group,
                                          channels=groups[cell.group]))
    return tuple(assignments)


def build_allocation(plan: CellularPlan, n_f: int, strategy: str) -> FrequencyAllocation:
    """Allocation complete : groupes -> canaux, et cellule -> (groupe, canaux)."""
    groups = allocate(n_f, plan.N, strategy)
    return FrequencyAllocation(strategy=strategy, N_f=n_f, N=plan.N, groups=groups,
                               assignments=assign_to_cells(plan, groups))


# --------------------------------------------------------------- verifications
def verify_allocation(allocation: FrequencyAllocation) -> list[str]:
    """Liste de problemes (vide = allocation correcte) : partition, equilibre, coherence."""
    problems: list[str] = []
    groups = allocation.groups

    if sorted(groups) != list(range(1, allocation.N + 1)):
        problems.append("Les groupes ne sont pas numerotes de 1 a N")

    all_channels = [c for g in sorted(groups) for c in groups[g]]
    if sorted(all_channels) != list(range(1, allocation.N_f + 1)):
        problems.append("Les canaux ne forment pas une partition exacte de 1..N_f "
                        "(canal perdu, manquant ou en double)")

    sizes = [len(groups[g]) for g in sorted(groups)]
    if sizes and max(sizes) - min(sizes) > 1:
        problems.append(f"Repartition desequilibree : tailles {sizes}")
    if sizes != sorted(sizes, reverse=True):
        problems.append("Les canaux restants (N_f mod N) ne vont pas aux premiers groupes")

    for a in allocation.assignments:
        if a.channels != groups.get(a.group):
            problems.append(f"Cellule {a.cell_id} : canaux incoherents avec le groupe {a.group}")
    return problems


def verify_cochannel_separation(plan: CellularPlan, allocation: FrequencyAllocation,
                                d_km: float, tol: float = 1e-6) -> list[str]:
    """Deux cellules partageant un canal doivent etre separees d'au moins D."""
    problems = []
    cells = {c.cell_id: c for c in plan.cells}
    items = allocation.assignments
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            if set(items[a].channels) & set(items[b].channels):
                ca, cb = cells[items[a].cell_id], cells[items[b].cell_id]
                dist = math.hypot(ca.x_km - cb.x_km, ca.y_km - cb.y_km)
                if dist < d_km - tol:
                    problems.append(f"Cellules {ca.cell_id} et {cb.cell_id} : "
                                    f"{dist:.2f} km < D = {d_km:.2f} km")
    return problems


def adjacent_pairs_in_same_group(groups: dict[int, tuple[int, ...]]) -> int:
    """Nombre de paires de canaux consecutifs (c, c+1) appartenant au MEME groupe.

    Indicateur propose par l'equipe pour comparer les deux strategies (l'enonce
    parle d'interference de canal adjacent a l'interieur d'un meme groupe).
    """
    return sum(1 for chs in groups.values() for c in chs if c + 1 in chs)