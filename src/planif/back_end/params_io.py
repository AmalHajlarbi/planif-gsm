"""Lecture, validation, modification et sauvegarde de params.json."""
from __future__ import annotations

import json
from dataclasses import fields, replace
from pathlib import Path
from typing import Any

from planif.back_end.radio_models import is_valid_cluster_size
from planif.contracts import Params
from planif.paths import DEFAULT_PARAMS_FILE

REQUIRED_KEYS = [f.name for f in fields(Params) if f.name != "PL_d0_dB"]


def validate_params(p: Params) -> None:
    """Leve ValueError avec un message clair si un parametre est incoherent."""
    errors = []
    if p.N_f < 1:
        errors.append("N_f doit etre >= 1")
    if not is_valid_cluster_size(p.N):
        errors.append(f"N={p.N} n'est pas de la forme i^2 + i*j + j^2 (ex: 3, 4, 7, 9, 12)")
    if p.N > p.N_f:
        errors.append("N ne doit pas depasser N_f (au moins 1 canal par groupe)")
    if p.f_port_MHz <= 0:
        errors.append("f_port_MHz doit etre > 0")
    if p.Pathloss_exp <= 0:
        errors.append("Pathloss_exp doit etre > 0")
    if p.d0_km <= 0:
        errors.append("d0_km doit etre > 0")
    if p.Dst_ab < 0:
        errors.append("Dst_ab doit etre >= 0")
    if not 0.0 <= p.T_act <= 1.0:
        errors.append("T_act doit etre compris entre 0 et 1")
    if errors:
        raise ValueError("Parametres invalides : " + " ; ".join(errors))


def params_from_dict(data: dict[str, Any]) -> Params:
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Cles manquantes dans params.json : {missing}")
    known = {f.name for f in fields(Params)}
    unknown = [k for k in data if k not in known]
    if unknown:
        raise ValueError(f"Cles inconnues dans params.json : {unknown}")
    try:
        p = Params(
            P_BTS_dBm=float(data["P_BTS_dBm"]),
            P_MS_dBm=float(data["P_MS_dBm"]),
            P_sens_dBm=float(data["P_sens_dBm"]),
            N_f=int(data["N_f"]),
            f_port_MHz=float(data["f_port_MHz"]),
            N=int(data["N"]),
            SIR_min_dB=float(data["SIR_min_dB"]),
            Dst_ab=float(data["Dst_ab"]),
            T_act=float(data["T_act"]),
            Pathloss_exp=float(data["Pathloss_exp"]),
            d0_km=float(data["d0_km"]),
            PL_d0_dB=None if data.get("PL_d0_dB") is None else float(data["PL_d0_dB"]),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Valeur de parametre non numerique : {exc}") from exc
    validate_params(p)
    return p


def load_params(path: str | Path = DEFAULT_PARAMS_FILE) -> Params:
    """Lit params.json et retourne un objet Params valide."""
    with open(path, "r", encoding="utf-8") as f:
        return params_from_dict(json.load(f))


def save_params(params: Params, path: str | Path = DEFAULT_PARAMS_FILE) -> None:
    """Sauvegarde les parametres dans un fichier JSON (apres validation)."""
    validate_params(params)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(params.to_dict(), f, indent=2, ensure_ascii=False)


def update_params(params: Params, **changes: Any) -> Params:
    """Retourne une copie modifiee (ex: update_params(p, N=9, Pathloss_exp=3.0))."""
    new = replace(params, **changes)
    validate_params(new)
    return new