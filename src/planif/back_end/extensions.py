"""Options d'amelioration (enonce, section 6).

1) Comparaison de plusieurs motifs N (3, 4, 7, 9, 12...) sur les memes parametres radio.
2) Comparaison de plusieurs exposants de propagation (balayage + environnements).
3) Positionnement automatique de clusters sur une zone, en coordonnees GPS FICTIVES.

Aucune formule radio n'est reecrite : on appelle compute_radio (P1), group_of (P2),
allocate et minimal_valid_pattern (P3).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from planif.back_end import radio_models as rm
from planif.back_end.calculator import compute_radio
from planif.back_end.coloring import cluster_ij, group_of
from planif.back_end.freq_allocation import allocate
from planif.back_end.hex_grid import SQRT3, axial_to_xy_km, hex_vertices
from planif.back_end.params_io import update_params
from planif.back_end.studies import minimal_valid_pattern
from planif.contracts import Params

DEFAULT_PATTERNS = (3, 4, 7, 9, 12, 13, 16)
DEFAULT_EXPONENTS = tuple(round(2.0 + 0.25 * k, 2) for k in range(13))   # 2.0 ... 5.0
EARTH_RADIUS_KM = 6371.0088
DEFAULT_CENTER = (36.80, 10.18)   # centre FICTIF de la carte (latitude, longitude), modifiable


# =============================================================== 1) motifs
def pattern_comparison(params: Params, patterns: Iterable[int] = DEFAULT_PATTERNS) -> list[dict]:
    """Une ligne par motif N (R, D, SIR, canaux, capacite), memes parametres radio.

    Les motifs N > N_f sont ignores (il faut au moins 1 canal par groupe).
    'Motif_minimal' = plus petit N dont le SIR respecte SIR_min.
    """
    rows: list[dict] = []
    for n_cells in sorted(set(patterns)):
        if n_cells > params.N_f:
            continue
        res = compute_radio(params, n_cells)          # leve ValueError si N invalide
        i, j = cluster_ij(n_cells)
        rows.append({
            "N": n_cells,
            "i": i,
            "j": j,
            "D_sur_R": round(res.D_sur_R, 3),
            "R_km": round(res.R_km, 3),
            "D_km": round(res.D_km, 3),
            "SIR_dB": round(res.SIR_dB, 2),
            "Marge_SIR_dB": round(res.SIR_dB - params.SIR_min_dB, 2),
            "SIR_ok": res.SIR_ok,
            "Canaux_par_cellule": round(res.Canaux_par_cellule, 2),
            "Actifs_par_cellule": round(res.Utilisateurs_actifs_cellule, 1),
            "Actifs_sur_canaux": round(res.Utilisateurs_actifs_cellule / res.Canaux_par_cellule, 2),
        })
    first_ok = next((r for r in rows if r["SIR_ok"]), None)
    for r in rows:
        r["Motif_minimal"] = r is first_ok
    return rows


# ============================================================ 2) exposants
def exponent_sweep(params: Params, exponents: Iterable[float] = DEFAULT_EXPONENTS,
                   patterns: Iterable[int] = (3, 4, 7, 9, 12),
                   zone_area_km2: float = 5000.0) -> list[dict]:
    """Pour chaque exposant n et chaque motif N : R, nombre de sites, SIR.

    Nombre de sites = ceil(zone / surface d'une cellule) (1 site par cellule : meme
    hypothese que l'etude d'environnement de P3).
    """
    rows: list[dict] = []
    for n_exp in exponents:
        p = update_params(params, Pathloss_exp=float(n_exp))
        n_min = minimal_valid_pattern(float(n_exp), params.SIR_min_dB, n_max=params.N_f)
        for n_cells in patterns:
            if n_cells > params.N_f:
                continue
            res = compute_radio(p, n_cells)
            rows.append({
                "Pathloss_exp": float(n_exp),
                "N": n_cells,
                "R_km": round(res.R_km, 3),
                "Surface_cellule_km2": round(res.Surface_cellule_km2, 2),
                "Sites_necessaires": math.ceil(zone_area_km2 / res.Surface_cellule_km2),
                "SIR_dB": round(res.SIR_dB, 2),
                "SIR_ok": res.SIR_ok,
                "N_min_valide": n_min,
            })
    return rows


# ============================================== 3) positionnement des clusters
def km_to_latlon(x_km: float, y_km: float, lat0: float, lon0: float) -> tuple[float, float]:
    """Repere local (km, origine au centre) -> (latitude, longitude) en degres."""
    lat = lat0 + math.degrees(y_km / EARTH_RADIUS_KM)
    lon = lon0 + math.degrees(x_km / (EARTH_RADIUS_KM * math.cos(math.radians(lat0))))
    return lat, lon


@dataclass(frozen=True)
class MapCell:
    cell_id: int
    cluster_id: int                      # 1..K, numerotes du centre vers l'exterieur
    group: int                           # groupe de frequences 1..N
    q: int
    r: int
    x_km: float
    y_km: float
    lat: float
    lon: float
    in_zone: bool                        # centre de la cellule dans la zone a couvrir
    channels: tuple[int, ...]
    vertices: tuple[tuple[float, float], ...]   # 6 sommets (lat, lon)


@dataclass(frozen=True)
class ClusterMap:
    N: int
    R_km: float
    n_f: int
    strategy: str
    center_lat: float
    center_lon: float
    zone_radius_km: float
    n_clusters: int
    cells: tuple[MapCell, ...]

    @property
    def n_cells(self) -> int:
        return len(self.cells)

    @property
    def n_cells_in_zone(self) -> int:
        return sum(1 for c in self.cells if c.in_zone)

    @property
    def D_km(self) -> float:
        return self.R_km * math.sqrt(3 * self.N)

    def cluster_cells(self, cluster_id: int) -> list[MapCell]:
        return [c for c in self.cells if c.cluster_id == cluster_id]


def cluster_offsets(n_cells: int) -> dict[int, tuple[int, int]]:
    """Forme d'un cluster : pour chaque groupe g, le decalage (dq, dr) le plus proche du centre.

    Distance au carre en axial : dq^2 + dq*dr + dr^2 (entier, donc sans ambiguite flottante).
    Departage deterministe par (dq, dr) : tous les clusters ont exactement la meme forme.
    """
    best: dict[int, tuple[tuple[int, int, int], tuple[int, int]]] = {}
    span = n_cells + 2
    for dq in range(-span, span + 1):
        for dr in range(-span, span + 1):
            g = group_of(dq, dr, n_cells)
            key = (dq * dq + dq * dr + dr * dr, dq, dr)
            if g not in best or key < best[g][0]:
                best[g] = (key, (dq, dr))
    return {g: v[1] for g, v in best.items()}


def build_cluster_map(n_cells: int, r_km: float, n_f: int, zone_radius_km: float,
                      center: tuple[float, float] = DEFAULT_CENTER,
                      strategy: str = "entrelacee") -> ClusterMap:
    """Place automatiquement les clusters necessaires pour couvrir une zone circulaire.

    Une cellule est "necessaire" si son centre est dans la zone ; on ajoute alors le cluster
    COMPLET qui la contient (N cellules, N groupes differents). Les cellules hors zone qui
    completent un cluster sont marquees in_zone = False.
    """
    if not rm.is_valid_cluster_size(n_cells):
        raise ValueError(f"N={n_cells} n'est pas de la forme i^2 + i*j + j^2")
    if r_km <= 0 or zone_radius_km <= 0:
        raise ValueError("R et le rayon de la zone doivent etre > 0")
    if n_f < n_cells:
        raise ValueError("N_f doit etre >= N (au moins un canal par groupe)")
    lat0, lon0 = center
    if not (-85.0 <= lat0 <= 85.0 and -180.0 <= lon0 <= 180.0):
        raise ValueError("Coordonnees du centre invalides")

    offsets = cluster_offsets(n_cells)
    channels_by_group = allocate(n_f, n_cells, strategy)    # leve ValueError si strategie inconnue

    rmax = math.ceil(zone_radius_km / (1.5 * r_km)) + 1
    qmax = math.ceil(zone_radius_km / (SQRT3 * r_km)) + rmax + 1
    points: set[tuple[int, int]] = set()                    # cellules "centre de cluster"
    for r in range(-rmax, rmax + 1):
        for q in range(-qmax, qmax + 1):
            x, y = axial_to_xy_km(q, r, r_km)
            if math.hypot(x, y) <= zone_radius_km:
                dq, dr = offsets[group_of(q, r, n_cells)]
                points.add((q - dq, r - dr))

    def distance_key(p: tuple[int, int]):
        x, y = axial_to_xy_km(p[0], p[1], r_km)
        return round(math.hypot(x, y), 9), p

    ordered = sorted(points, key=distance_key)

    cells: list[MapCell] = []
    for cluster_id, (pq, pr) in enumerate(ordered, start=1):
        for g in sorted(offsets):
            dq, dr = offsets[g]
            q, r = pq + dq, pr + dr
            x, y = axial_to_xy_km(q, r, r_km)
            lat, lon = km_to_latlon(x, y, lat0, lon0)
            verts = tuple(km_to_latlon(vx, vy, lat0, lon0) for vx, vy in hex_vertices(x, y, r_km))
            cells.append(MapCell(
                cell_id=len(cells), cluster_id=cluster_id, group=g, q=q, r=r,
                x_km=x, y_km=y, lat=lat, lon=lon,
                in_zone=math.hypot(x, y) <= zone_radius_km,
                channels=channels_by_group[g], vertices=verts))

    return ClusterMap(N=n_cells, R_km=r_km, n_f=n_f, strategy=strategy,
                      center_lat=lat0, center_lon=lon0, zone_radius_km=zone_radius_km,
                      n_clusters=len(ordered), cells=tuple(cells))


def verify_cluster_map(cmap: ClusterMap, tol: float = 1e-6) -> list[str]:
    """Liste de problemes (vide = carte correcte)."""
    problems: list[str] = []
    for cid in range(1, cmap.n_clusters + 1):
        cells = cmap.cluster_cells(cid)
        if len(cells) != cmap.N or {c.group for c in cells} != set(range(1, cmap.N + 1)):
            problems.append(f"Cluster {cid} : doit contenir les {cmap.N} groupes, une fois chacun")
    keys = [(c.q, c.r) for c in cmap.cells]
    if len(set(keys)) != len(keys):
        problems.append("Cellules en double sur la carte")
    d_km = cmap.D_km
    cells = cmap.cells
    for a in range(len(cells)):
        for b in range(a + 1, len(cells)):
            if cells[a].group == cells[b].group:
                dist = math.hypot(cells[a].x_km - cells[b].x_km, cells[a].y_km - cells[b].y_km)
                if dist < d_km - tol:
                    problems.append(f"Cellules {cells[a].cell_id} et {cells[b].cell_id} "
                                    f"(groupe {cells[a].group}) : {dist:.2f} km < D = {d_km:.2f} km")
    return problems


def convex_hull(points: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    """Enveloppe convexe (Andrew), pour dessiner le contour d'un cluster."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def cluster_hull(cmap: ClusterMap, cluster_id: int) -> list[tuple[float, float]]:
    """Contour (lat, lon) d'un cluster."""
    return convex_hull(v for c in cmap.cluster_cells(cluster_id) for v in c.vertices)


def cells_table(cmap: ClusterMap) -> list[dict]:
    """Une ligne par cellule (CSV)."""
    return [{
        "cell_id": c.cell_id, "cluster": c.cluster_id, "groupe": c.group, "q": c.q, "r": c.r,
        "x_km": round(c.x_km, 3), "y_km": round(c.y_km, 3),
        "lat": round(c.lat, 6), "lon": round(c.lon, 6), "dans_la_zone": c.in_zone,
        "nb_canaux": len(c.channels), "canaux": " ".join(map(str, c.channels)),
    } for c in cmap.cells]


def to_geojson(cmap: ClusterMap) -> dict:
    """FeatureCollection GeoJSON (ouvrable dans QGIS, geojson.io...). Coordonnees FICTIVES."""
    features = []
    for c in cmap.cells:
        ring = [[lon, lat] for lat, lon in c.vertices]
        ring.append(ring[0])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "cell_id": c.cell_id, "cluster": c.cluster_id, "groupe": c.group,
                "dans_la_zone": c.in_zone, "nb_canaux": len(c.channels),
                "canaux": " ".join(map(str, c.channels)),
                "centre_lat": round(c.lat, 6), "centre_lon": round(c.lon, 6),
            },
        })
    return {"type": "FeatureCollection",
            "properties": {"N": cmap.N, "R_km": cmap.R_km, "clusters": cmap.n_clusters,
                           "strategie": cmap.strategy, "coordonnees": "GPS fictives"},
            "features": features}