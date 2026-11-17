"""CONTRAT D'INTERFACE PARTAGE - fichier fige au jour 0.

Ne pas modifier sans prevenir les 4 membres de l'equipe.
Les noms des champs de Params sont exactement les cles de params.json.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Params:
    """Parametres d'entree (enonce, section 2)."""

    P_BTS_dBm: float          # puissance d'emission BTS (dBm)
    P_MS_dBm: float           # puissance d'emission mobile (dBm)
    P_sens_dBm: float         # sensibilite du recepteur (dBm)
    N_f: int                  # nombre total de canaux disponibles
    f_port_MHz: float         # frequence porteuse (MHz)
    N: int                    # nombre de cellules par motif
    SIR_min_dB: float         # seuil de SIR exige (dB)
    Dst_ab: float             # densite d'abonnes (ab./km2)
    T_act: float              # taux d'activite simultanee (0-1)
    Pathloss_exp: float       # exposant d'affaiblissement n
    d0_km: float              # distance de reference d0 (km)
    PL_d0_dB: Optional[float] = None  # option : PL(d0) fixe ; None = espace libre

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RadioResults:
    """Resultats du calcul radio pour un motif N (enonce, sections 4.1 a 4.4)."""

    N: int
    P_TX_dBm: float
    G_ant_dB: float
    MAPL_dB: float
    PL_d0_dB: float
    R_km: float
    D_km: float
    D_sur_R: float
    SIR_dB: float
    SIR_ok: bool                       # SIR >= SIR_min_dB
    Canaux_par_cellule: float          # N_f / N (peut etre non entier)
    Surface_cellule_km2: float
    Abonnes_cellule: float
    Utilisateurs_actifs_cellule: float  # Abonnes_cellule * T_act

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Contrats utilises par les Personnes 2, 3 et 4 (definis ici pour que chacun
# puisse travailler sans attendre les autres).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Cell:
    """Une cellule hexagonale du plan (produite par la Personne 2)."""

    cell_id: int      # identifiant unique 0..(rows*cols - 1)
    q: int            # coordonnee hexagonale axiale
    r: int            # coordonnee hexagonale axiale
    row: int          # ligne dans la grille rows x cols
    col: int          # colonne dans la grille rows x cols
    x_km: float       # centre de la cellule (km)
    y_km: float
    group: int        # groupe de frequences, de 1 a N


@dataclass(frozen=True)
class CellularPlan:
    """Plan cellulaire hexagonal (Personne 2 -> Personnes 3 et 4)."""

    N: int
    R_km: float
    rows: int
    cols: int
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class CellAssignment:
    """Groupe + liste exacte des canaux d'une cellule (produit par la Personne 3)."""

    cell_id: int
    group: int
    channels: tuple[int, ...]


@dataclass(frozen=True)
class FrequencyAllocation:
    """Allocation des N_f canaux aux N groupes (Personne 3 -> Personne 4)."""

    strategy: str                          # "contigue" ou "entrelacee"
    N_f: int
    N: int
    groups: dict[int, tuple[int, ...]]     # groupe (1..N) -> canaux (1..N_f)
    assignments: tuple[CellAssignment, ...]