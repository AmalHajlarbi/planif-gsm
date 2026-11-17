"""Chaine de calcul complete : Params -> RadioResults (enonce, travail demande n°2)."""
from __future__ import annotations

from typing import Iterable

from planif.back_end import radio_models as rm
from planif.contracts import Params, RadioResults


def compute_radio(params: Params, n_cells: int | None = None) -> RadioResults:
    """Calcule R, D, SIR, canaux/cellule, abonnes/cellule pour un motif.

    n_cells : motif a evaluer. Si None, on utilise params.N.
    """
    n_cells = params.N if n_cells is None else n_cells
    if not rm.is_valid_cluster_size(n_cells):
        raise ValueError(f"N={n_cells} n'est pas un motif hexagonal valide")

    p_tx = rm.p_tx_dbm(params.P_BTS_dBm, params.P_MS_dBm)
    mapl = rm.mapl_db(p_tx, params.P_sens_dBm)

    if params.PL_d0_dB is not None:
        pl_d0 = params.PL_d0_dB
    else:
        pl_d0 = rm.free_space_pl_db(params.f_port_MHz, params.d0_km)

    r_km = rm.cell_radius_km(mapl, pl_d0, params.Pathloss_exp, params.d0_km)
    d_km = rm.reuse_distance_km(r_km, n_cells)
    sir = rm.sir_db(n_cells, params.Pathloss_exp)

    area = rm.hex_cell_area_km2(r_km)
    subs = rm.subscribers_per_cell(area, params.Dst_ab)

    return RadioResults(
        N=n_cells,
        P_TX_dBm=p_tx,
        G_ant_dB=rm.G_ANT_DB,
        MAPL_dB=mapl,
        PL_d0_dB=pl_d0,
        R_km=r_km,
        D_km=d_km,
        D_sur_R=rm.reuse_ratio(n_cells),
        SIR_dB=sir,
        SIR_ok=sir >= params.SIR_min_dB,
        Canaux_par_cellule=rm.channels_per_cell(params.N_f, n_cells),
        Surface_cellule_km2=area,
        Abonnes_cellule=subs,
        Utilisateurs_actifs_cellule=rm.active_users_per_cell(subs, params.T_act),
    )


def compute_for_patterns(params: Params, patterns: Iterable[int] = (3, 7, 9)) -> list[RadioResults]:
    """Un RadioResults par motif (tableau comparatif N = 3, 7, 9)."""
    return [compute_radio(params, n) for n in patterns]