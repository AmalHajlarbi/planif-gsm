"""Etudes d'analyse : densite d'abonnes, environnement, nombre de sites (enonce, section 7).

Utilise les fonctions de la Personne 1 (compute_radio, update_params) : aucune formule
radio n'est reecrite ici.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from planif.back_end import radio_models as rm
from planif.back_end.calculator import compute_radio
from planif.back_end.params_io import update_params
from planif.contracts import Params
from planif.paths import CONFIG_DIR

STUDIES_FILE = CONFIG_DIR / "studies.json"


@dataclass(frozen=True)
class StudiesConfig:
    zone_area_km2: float                 # surface de la zone a couvrir (HYPOTHESE de l'equipe)
    environments: dict[str, float]       # nom -> exposant n (HYPOTHESE de l'equipe)
    densities_ab_km2: tuple[float, ...]
    patterns: tuple[int, ...]


def load_studies_config(path: str | Path = STUDIES_FILE) -> StudiesConfig:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    cfg = StudiesConfig(
        zone_area_km2=float(d["zone_area_km2"]),
        environments={str(k): float(v) for k, v in d["environments"].items()},
        densities_ab_km2=tuple(float(x) for x in d["densities_ab_km2"]),
        patterns=tuple(int(x) for x in d["patterns"]),
    )
    if cfg.zone_area_km2 <= 0 or not cfg.environments or not cfg.densities_ab_km2:
        raise ValueError("studies.json : zone_area_km2 > 0, environnements et densites requis")
    return cfg


# ------------------------------------------------------------------ densite
def density_study(params: Params, densities: Iterable[float], patterns: Iterable[int]) -> list[dict]:
    """Pour chaque (densite, motif) : actifs par cellule vs canaux disponibles.

    HYPOTHESE : 1 canal par utilisateur actif (comparaison directe demandee en 4.4).
    """
    rows = []
    for dens in densities:
        p = update_params(params, Dst_ab=dens)
        for n_cells in patterns:
            res = compute_radio(p, n_cells)
            actifs = res.Utilisateurs_actifs_cellule
            rows.append({
                "Dst_ab": dens,
                "N": n_cells,
                "Canaux_par_cellule": round(res.Canaux_par_cellule, 2),
                "Abonnes_cellule": round(res.Abonnes_cellule, 1),
                "Utilisateurs_actifs": round(actifs, 1),
                "Actifs_sur_canaux": round(actifs / res.Canaux_par_cellule, 2),
                "Dimensionnement_OK": actifs <= res.Canaux_par_cellule,
                "N_f_requis": math.ceil(actifs * n_cells),
            })
    return rows


def max_density_supported(params: Params, n_cells: int) -> float:
    """Densite maximale (ab./km2) pour laquelle actifs <= canaux disponibles par cellule."""
    if params.T_act == 0:
        return math.inf
    res = compute_radio(params, n_cells)
    return res.Canaux_par_cellule / (params.T_act * res.Surface_cellule_km2)


# ------------------------------------------------------------- environnement
def minimal_valid_pattern(n_exp: float, sir_min_db: float, n_max: int = 100) -> int | None:
    """Plus petit motif N valide (i^2+ij+j^2) tel que SIR >= SIR_min, ou None."""
    for n_cells in range(1, n_max + 1):
        if rm.is_valid_cluster_size(n_cells) and rm.sir_db(n_cells, n_exp) >= sir_min_db:
            return n_cells
    return None


def environment_study(params: Params, environments: dict[str, float], zone_area_km2: float,
                      patterns: Iterable[int]) -> list[dict]:
    """Pour chaque (environnement, motif) : R, surface, nombre de sites, SIR.

    Nombre de sites = ceil(zone / surface d'une cellule) (1 site par cellule : HYPOTHESE).
    """
    rows = []
    for env, n_exp in environments.items():
        p = update_params(params, Pathloss_exp=n_exp)
        n_min = minimal_valid_pattern(n_exp, params.SIR_min_dB, n_max=params.N_f)
        for n_cells in patterns:
            res = compute_radio(p, n_cells)
            rows.append({
                "Environnement": env,
                "Pathloss_exp": n_exp,
                "N": n_cells,
                "R_km": round(res.R_km, 3),
                "Surface_cellule_km2": round(res.Surface_cellule_km2, 2),
                "Sites_necessaires": math.ceil(zone_area_km2 / res.Surface_cellule_km2),
                "D_km": round(res.D_km, 3),
                "SIR_dB": round(res.SIR_dB, 2),
                "SIR_ok": res.SIR_ok,
                "N_min_valide": n_min,
            })
    return rows