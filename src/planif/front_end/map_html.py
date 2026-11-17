"""Carte interactive (Leaflet + fond de carte) du positionnement des clusters.

Le fichier HTML est autonome : il s'ouvre dans un navigateur (connexion internet requise pour
le fond de carte) ou s'affiche dans l'application Streamlit. Coordonnees GPS FICTIVES.
"""
from __future__ import annotations

import json

from planif.back_end.extensions import ClusterMap, cluster_hull
from planif.front_end.style import group_colors

_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Plan de fréquences</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
html, body { height: 100%; margin: 0; padding: 0; }
#map { width: 100%; height: 550px; background: #e5e7eb; }
.legend{background:#fff;padding:8px 10px;border-radius:8px;font:12px/1.6 sans-serif;
        box-shadow:0 1px 6px rgba(0,0,0,.3)}
.sw{display:inline-block;width:12px;height:12px;margin-right:6px;border:1px solid #fff;
    vertical-align:middle}
.cl{background:#1F2937;color:#fff;border-radius:10px;padding:1px 7px;font:bold 12px sans-serif;
    white-space:nowrap;display:inline-block;transform:translate(-50%,-120%)}
.leaflet-tooltip.gl{background:none;border:none;box-shadow:none;font-weight:bold;color:#1F2937;
    font-size:12px}
.leaflet-tooltip.gl::before{display:none}
</style></head>
<body><div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
try {
  const DATA = __DATA__;
  const map = L.map('map').setView([DATA.center[0], DATA.center[1]], 9);

  // Fond de carte ArcGIS (fonctionne dans les iframes Streamlit sans blocage Referer)
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 18,
    attribution: 'Tiles &copy; Esri'
  }).addTo(map);

  const bounds = L.latLngBounds([]);

  DATA.cells.forEach(c => {
    const poly = L.polygon(c.ring, {color: '#ffffff', weight: 1.2,
        fillColor: DATA.colors[String(c.group)], fillOpacity: c.in_zone ? 0.7 : 0.3});
    poly.bindPopup('<b>Cellule ' + c.id + '</b><br>Cluster C' + c.cluster + '<br>Groupe ' + c.group +
                   '<br>Canaux : ' + c.channels);
    poly.bindTooltip(String(c.group), {permanent: true, direction: 'center', className: 'gl'});
    poly.addTo(map);
    c.ring.forEach(p => bounds.extend(p));
  });

  DATA.clusters.forEach(h => {
    L.polygon(h.hull, {color: '#1F2937', weight: 3, dashArray: '6 4', fill: false}).addTo(map);
    L.marker(h.label, {icon: L.divIcon({className: '', html: '<span class="cl">C' + h.id + '</span>',
                                         iconSize: [0, 0]}), interactive: false}).addTo(map);
  });

  const zone = L.circle([DATA.center[0], DATA.center[1]],
      {radius: DATA.zone_m, color: '#D1495B', weight: 2, dashArray: '8 6', fill: false}).addTo(map);
  bounds.extend(zone.getBounds());

  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.1));
  }

  const legend = L.control({position: 'bottomright'});
  legend.onAdd = () => {
    const d = L.DomUtil.create('div', 'legend');
    let h = '<b>' + DATA.title + '</b><br>N = ' + DATA.N + ' | ' + DATA.n_clusters +
            ' clusters | R = ' + DATA.R_km.toFixed(2) + ' km<br>';
    Object.keys(DATA.colors).forEach(g => {
      h += '<span class="sw" style="background:' + DATA.colors[g] + '"></span>Groupe ' + g + '<br>';
    });
    h += '<span class="sw" style="background:#fff;border:2px dashed #1F2937"></span>Cluster<br>' +
         '<span class="sw" style="background:#fff;border:2px dashed #D1495B"></span>Zone à couvrir<br>' +
         '<i>Coordonnées GPS fictives</i>';
    d.innerHTML = h;
    return d;
  };
  legend.addTo(map);

  setTimeout(() => { map.invalidateSize(); }, 200);
} catch (err) {
  document.getElementById('map').innerHTML =
    '<div style="padding:20px;color:#9B1C2C;font-family:sans-serif;"><b>Erreur JS :</b> ' + err.message + '</div>';
}
</script></body></html>
"""


def build_leaflet_html(cmap: ClusterMap, title: str = "Plan de fréquences") -> str:
    colors = group_colors(cmap.N)
    cells = [{
        "id": c.cell_id, "cluster": c.cluster_id, "group": c.group, "in_zone": c.in_zone,
        "channels": " ".join(map(str, c.channels)),
        "ring": [[round(lat, 6), round(lon, 6)] for lat, lon in c.vertices],
    } for c in cmap.cells]

    clusters = []
    for cid in range(1, cmap.n_clusters + 1):
        hull = cluster_hull(cmap, cid)
        top = max(hull)
        clusters.append({"id": cid, "hull": [[round(la, 6), round(lo, 6)] for la, lo in hull],
                         "label": [round(top[0], 6), round(top[1], 6)]})

    data = {
        "title": title, "N": cmap.N, "R_km": cmap.R_km, "n_clusters": cmap.n_clusters,
        "center": [cmap.center_lat, cmap.center_lon], "zone_m": cmap.zone_radius_km * 1000.0,
        "colors": {str(g): colors[g] for g in range(1, cmap.N + 1)},
        "cells": cells, "clusters": clusters,
    }
    return _TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))