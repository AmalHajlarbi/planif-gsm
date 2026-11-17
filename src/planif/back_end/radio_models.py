"""Formules radio de l'enonce (section 4). Fonctions pures, sans entree/sortie.

Toutes les distances sont en km, les puissances en dBm, les gains/pertes en dB.
"""
from __future__ import annotations

import math

G_ANT_DB = 2.0          # gain d'antenne forfaitaire emission + reception (enonce, section 3)
N_INTERFERERS = 6       # premier anneau de cellules interferentes (enonce, section 3)


# ----------------------------------------------------------------- 4.1
def p_tx_dbm(p_bts_dbm: float, p_ms_dbm: float) -> float:
    """P_TX = min(P_BTS, P_MS) : sens le plus defavorable."""
    return min(p_bts_dbm, p_ms_dbm)


def mapl_db(p_tx_dbm_: float, p_sens_dbm: float, g_ant_db: float = G_ANT_DB) -> float:
    """MAPL = P_TX - P_sens + G_ant."""
    return p_tx_dbm_ - p_sens_dbm + g_ant_db


def free_space_pl_db(f_mhz: float, d_km: float) -> float:
    """Affaiblissement en espace libre : 32.44 + 20 log10(f_MHz) + 20 log10(d_km).

    CHOIX TECHNIQUE (l'enonce autorise espace libre ou parametre additionnel).
    """
    return 32.44 + 20.0 * math.log10(f_mhz) + 20.0 * math.log10(d_km)


def path_loss_db(d_km: float, pl_d0_db: float, n: float, d0_km: float) -> float:
    """Modele log-distance : PL(d) = PL(d0) + 10 n log10(d / d0)."""
    return pl_d0_db + 10.0 * n * math.log10(d_km / d0_km)


def cell_radius_km(mapl_db_: float, pl_d0_db: float, n: float, d0_km: float) -> float:
    """R = d0 * 10^E avec E = (MAPL - PL(d0)) / (10 n)."""
    exponent = (mapl_db_ - pl_d0_db) / (10.0 * n)
    return d0_km * 10.0 ** exponent


# ----------------------------------------------------------------- 4.2
def is_valid_cluster_size(n_cells: int) -> bool:
    """Vrai si N = i^2 + i*j + j^2 pour des entiers i, j >= 0 non tous nuls."""
    if n_cells < 1:
        return False
    limit = int(math.isqrt(n_cells)) + 1
    for i in range(limit + 1):
        for j in range(limit + 1):
            if (i, j) != (0, 0) and i * i + i * j + j * j == n_cells:
                return True
    return False


def reuse_ratio(n_cells: int) -> float:
    """D / R = sqrt(3 N)."""
    return math.sqrt(3.0 * n_cells)


def reuse_distance_km(r_km: float, n_cells: int) -> float:
    """D = R * sqrt(3 N)."""
    return r_km * reuse_ratio(n_cells)


# ----------------------------------------------------------------- 4.3
def sir_linear(n_cells: int, n: float) -> float:
    """S/I = (1/6) * (D/R)^n (6 cellules interferentes)."""
    return (1.0 / N_INTERFERERS) * reuse_ratio(n_cells) ** n


def sir_db(n_cells: int, n: float) -> float:
    """S/I (dB) = 10 n log10(D/R) - 10 log10(6)."""
    return 10.0 * n * math.log10(reuse_ratio(n_cells)) - 10.0 * math.log10(N_INTERFERERS)


# ----------------------------------------------------------------- 4.4
def channels_per_cell(n_f: int, n_cells: int) -> float:
    """Canaux par cellule = N_f / N."""
    return n_f / n_cells


def hex_cell_area_km2(r_km: float) -> float:
    """Surface d'un hexagone regulier de rayon R : (3 sqrt(3) / 2) R^2."""
    return (3.0 * math.sqrt(3.0) / 2.0) * r_km ** 2


def subscribers_per_cell(area_km2: float, density_per_km2: float) -> float:
    """Abonnes_cellule = Surface_cellule * Dst_ab."""
    return area_km2 * density_per_km2


def active_users_per_cell(subscribers: float, t_act: float) -> float:
    """Utilisateurs actifs simultanes = Abonnes_cellule * T_act."""
    return subscribers * t_act