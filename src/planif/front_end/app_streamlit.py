"""Application Streamlit : modifier / sauvegarder les parametres, voir et exporter les resultats.

Lancer depuis la racine du projet (planif-gsm/), avec (.venv) actif :
    streamlit run src/planif/front_end/app_streamlit.py

Aucun calcul ici : tout vient de planif.pipeline (qui appelle P1, P2, P3).
"""
from __future__ import annotations

import inspect
import tempfile
import json
import math
import streamlit.components.v1 as components
from pathlib import Path

import pandas as pd
import streamlit as st

from planif.back_end.freq_allocation import (STRATEGIES, adjacent_pairs_in_same_group,
                                             build_allocation)
from planif.back_end.params_io import load_params, save_params, validate_params
from planif.back_end.radio_models import is_valid_cluster_size
from planif.back_end.studies import max_density_supported
from planif.back_end import extensions as ext
from planif.front_end import plots_extensions
from planif.front_end.map_html import build_leaflet_html
from planif.contracts import Params
from planif.front_end import plots_plan, plots_radio, plots_studies
from planif.paths import DEFAULT_PARAMS_FILE
from planif.pipeline import build_summary_text, export_all, run_pipeline

VALID_N = [n for n in range(1, 61) if is_valid_cluster_size(n)]
DEFAULT_PL_D0 = 91.52
STRATEGY_LABELS = {"contigue": "Contiguë (blocs)", "entrelacee": "Entrelacée (round-robin)"}

# Compatibilite entre versions de Streamlit (use_container_width -> width="stretch")
STRETCH = ({"width": "stretch"} if "width" in inspect.signature(st.button).parameters
           else {"use_container_width": True})

CSS = """
<style>
.block-container {padding-top: 1.5rem; max-width: 1500px;}
.hero {background: linear-gradient(120deg, #0F2A4A 0%, #1F5C99 100%);
       padding: 1.4rem 1.8rem; border-radius: 14px; margin-bottom: 1rem;}
.hero h1 {margin: 0; font-size: 1.8rem; color: #FFFFFF; padding: 0;}
.hero p {margin: .35rem 0 0 0; color: #DCE6F2; font-size: .95rem;}
[data-testid="stMetric"] {background: #F6F8FB; border: 1px solid #E1E6EE;
       border-radius: 10px; padding: .7rem .9rem;}
[data-testid="stMetricLabel"] p {font-size: .8rem; color: #5B6677;}
[data-testid="stMetricValue"] {color: #0F2A4A;}
.stTabs [data-baseweb="tab"] {font-weight: 600;}
.chip {display: inline-block; padding: .25rem .75rem; margin: 0 .4rem .6rem 0;
       border-radius: 999px; background: #E8EEF7; color: #0F2A4A; font-size: .85rem;
       font-weight: 600;}
.chip.ok {background: #DDF3E4; color: #17653A;}
.chip.bad {background: #FBE0E3; color: #9B1C2C;}
</style>
"""


# ------------------------------------------------------------------ etat des widgets
def _load_into_state(p: Params) -> None:
    """Copie un objet Params dans les widgets (cles 'p_<nom>')."""
    ss = st.session_state
    ss["p_P_BTS_dBm"] = float(p.P_BTS_dBm)
    ss["p_P_MS_dBm"] = float(p.P_MS_dBm)
    ss["p_P_sens_dBm"] = float(p.P_sens_dBm)
    ss["p_N_f"] = int(p.N_f)
    ss["p_f_port_MHz"] = float(p.f_port_MHz)
    ss["p_N"] = int(p.N)
    ss["p_SIR_min_dB"] = float(p.SIR_min_dB)
    ss["p_Dst_ab"] = float(p.Dst_ab)
    ss["p_T_act"] = float(p.T_act)
    ss["p_Pathloss_exp"] = float(p.Pathloss_exp)
    ss["p_d0_km"] = float(p.d0_km)
    ss["p_fixpl"] = p.PL_d0_dB is not None
    ss["p_PL_d0_dB"] = float(p.PL_d0_dB) if p.PL_d0_dB is not None else DEFAULT_PL_D0


def _reload_from_file() -> None:
    _load_into_state(load_params(DEFAULT_PARAMS_FILE))


def _params_from_state() -> Params:
    ss = st.session_state
    return Params(
        P_BTS_dBm=float(ss["p_P_BTS_dBm"]), P_MS_dBm=float(ss["p_P_MS_dBm"]),
        P_sens_dBm=float(ss["p_P_sens_dBm"]), N_f=int(ss["p_N_f"]),
        f_port_MHz=float(ss["p_f_port_MHz"]), N=int(ss["p_N"]),
        SIR_min_dB=float(ss["p_SIR_min_dB"]), Dst_ab=float(ss["p_Dst_ab"]),
        T_act=float(ss["p_T_act"]), Pathloss_exp=float(ss["p_Pathloss_exp"]),
        d0_km=float(ss["p_d0_km"]),
        PL_d0_dB=float(ss["p_PL_d0_dB"]) if ss["p_fixpl"] else None,
    )


# ------------------------------------------------------------------ aides d'affichage
def render_png(draw, *args, **kwargs) -> bytes:
    """Appelle une fonction de trace (..., out_path) et retourne les octets du PNG."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.png"
        draw(*args, path, **kwargs)
        return path.read_bytes()


def show_figure(png: bytes, file_name: str) -> None:
    """Figure dans une carte, adaptee a la largeur de sa colonne, avec bouton de telechargement."""
    with st.container(border=True):
        try:
            st.image(png, width="stretch")
        except Exception:
            st.image(png, use_container_width=True)
        st.download_button("Télécharger (PNG)", png, file_name=file_name, mime="image/png",
                           key=f"dl_{file_name}", **STRETCH)


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(sep=";", index=False).encode("utf-8-sig")


def style_yes_no(df: pd.DataFrame, column: str):
    """Colore la colonne oui/non (vert / rouge)."""
    def _c(v):
        return ("background-color:#DDF3E4;color:#17653A" if v == "oui"
                else "background-color:#FBE0E3;color:#9B1C2C")
    styler = df.style
    apply = getattr(styler, "map", None) or styler.applymap
    return apply(_c, subset=[column])


# ------------------------------------------------------------------ application
def main() -> None:
    st.set_page_config(page_title="Planification GSM", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hero">
          <h1>Planification d'un réseau mobile GSM</h1>
          <p>Dimensionnement radio et plan de fréquences : bilan de liaison, motif de
          réutilisation, plan cellulaire hexagonal et allocation des canaux.</p>
        </div>
        """, unsafe_allow_html=True)

    if "loaded" not in st.session_state:
        _reload_from_file()
        st.session_state["loaded"] = True

    # ---------------- barre laterale : parametres
    with st.sidebar:
        st.header("Paramètres")
        with st.expander("Bilan de liaison", expanded=True):
            st.number_input("P_BTS (dBm)", key="p_P_BTS_dBm", step=1.0)
            st.number_input("P_MS (dBm)", key="p_P_MS_dBm", step=1.0)
            st.number_input("P_sens (dBm)", key="p_P_sens_dBm", step=1.0)
            st.number_input("Fréquence porteuse (MHz)", key="p_f_port_MHz",
                            min_value=1.0, step=10.0)
            st.number_input("Exposant d'affaiblissement n", key="p_Pathloss_exp",
                            min_value=0.1, step=0.1)
            st.number_input("Distance de référence d0 (km)", key="p_d0_km",
                            min_value=0.001, step=0.1, format="%.3f")
            st.checkbox("Fixer PL(d0) (sinon : espace libre)", key="p_fixpl")
            if st.session_state["p_fixpl"]:
                st.number_input("PL(d0) (dB)", key="p_PL_d0_dB", step=0.5)
        with st.expander("Réseau", expanded=True):
            st.selectbox("Motif N (i² + ij + j²)", VALID_N, key="p_N")
            st.number_input("N_f (canaux disponibles)", key="p_N_f", min_value=1, step=1)
            st.number_input("SIR_min (dB)", key="p_SIR_min_dB", step=0.5)
        with st.expander("Trafic", expanded=True):
            st.number_input("Densité d'abonnés (ab./km²)", key="p_Dst_ab",
                            min_value=0.0, step=1.0)
            st.number_input("Taux d'activité T_act", key="p_T_act", min_value=0.0,
                            max_value=1.0, step=0.01, format="%.2f")
        with st.expander("Plan et allocation", expanded=True):
            strategy = st.radio("Stratégie d'allocation", STRATEGIES,
                                index=STRATEGIES.index("entrelacee"),
                                format_func=lambda s: STRATEGY_LABELS[s])
            rows = st.number_input("Lignes de la grille", min_value=1, max_value=15,
                                   value=7, step=1)
            cols = st.number_input("Colonnes de la grille", min_value=1, max_value=15,
                                   value=7, step=1)

        params_ready = True
        try:
            params = _params_from_state()
            validate_params(params)
        except ValueError as exc:
            params_ready = False
            st.error(str(exc))

        c1, c2 = st.columns(2)
        if c1.button("Sauvegarder", disabled=not params_ready, **STRETCH):
            save_params(params, DEFAULT_PARAMS_FILE)
            st.success("params.json sauvegardé.")
        c2.button("Recharger", on_click=_reload_from_file, **STRETCH)

    if not params_ready:
        st.stop()

    result = run_pipeline(params, strategy=strategy, rows=int(rows), cols=int(cols))
    radio = result.radio

    cls = "ok" if radio.SIR_ok else "bad"
    sign = "≥" if radio.SIR_ok else "<"
    st.markdown(
        f'<span class="chip">Motif N = {radio.N}</span>'
        f'<span class="chip">R = {radio.R_km:.2f} km</span>'
        f'<span class="chip">D = {radio.D_km:.2f} km</span>'
        f'<span class="chip {cls}">SIR = {radio.SIR_dB:.2f} dB {sign} {params.SIR_min_dB:g} dB</span>'
        f'<span class="chip">{STRATEGY_LABELS[strategy]}</span>',
        unsafe_allow_html=True)

    tab_radio, tab_plan, tab_alloc, tab_studies, tab_options, tab_export = st.tabs(
        ["Résultats radio", "Plan cellulaire", "Allocation des canaux", "Études",
         "Options avancées", "Export"])

    # ---------------- onglet 1 : radio
    with tab_radio:
        a, b, c, d = st.columns(4)
        a.metric("Rayon de cellule R", f"{radio.R_km:.3f} km")
        b.metric("Distance de réutilisation D", f"{radio.D_km:.3f} km")
        c.metric("SIR", f"{radio.SIR_dB:.2f} dB",
                 delta=f"{radio.SIR_dB - params.SIR_min_dB:+.2f} dB vs seuil")
        d.metric("Canaux / cellule", f"{radio.Canaux_par_cellule:.2f}")
        e, f, g, h = st.columns(4)
        e.metric("MAPL", f"{radio.MAPL_dB:.2f} dB")
        f.metric("Surface d'une cellule", f"{radio.Surface_cellule_km2:.2f} km²")
        g.metric("Abonnés / cellule", f"{radio.Abonnes_cellule:.0f}")
        h.metric("Utilisateurs actifs / cellule", f"{radio.Utilisateurs_actifs_cellule:.0f}")

        if radio.SIR_ok:
            st.success(f"SIR ≥ SIR_min : le motif N = {radio.N} est acceptable.")
        for w in result.warnings:
            st.warning(w)

        st.subheader("Tableau comparatif N = 3, 7, 9")
        df_cmp = pd.DataFrame([{
            "Motif (N)": x.N, "R (km)": round(x.R_km, 3), "D (km)": round(x.D_km, 3),
            "SIR (dB)": round(x.SIR_dB, 2), "Canaux / cellule": round(x.Canaux_par_cellule, 2),
            "Abonnés / cellule": round(x.Abonnes_cellule),
            "Actifs / cellule": round(x.Utilisateurs_actifs_cellule),
            "SIR ≥ SIR_min": "oui" if x.SIR_ok else "non",
        } for x in result.comparison])
        st.dataframe(style_yes_no(df_cmp, "SIR ≥ SIR_min"), hide_index=True)
        st.download_button("Télécharger le tableau (CSV)", csv_bytes(df_cmp),
                           file_name="tableau_comparatif.csv", mime="text/csv")

        st.subheader("Figures")
        left, right = st.columns(2, gap="large")
        with left:
            show_figure(render_png(plots_radio.plot_path_loss_vs_distance, params, radio),
                        "bilan_liaison.png")
        with right:
            show_figure(render_png(plots_radio.plot_sir_vs_pattern, params, result.comparison),
                        "sir_vs_motif.png")

        left, right = st.columns(2, gap="large")
        with left:
            show_figure(render_png(plots_radio.plot_capacity, result.comparison),
                        "canaux_vs_utilisateurs.png")
        with right:
            ok_n = [x.N for x in result.comparison if x.SIR_ok]
            ratio = radio.Utilisateurs_actifs_cellule / radio.Canaux_par_cellule
            with st.container(border=True):
                st.markdown("**Lecture des résultats**")
                st.markdown(
                    "- **Interférence** : le SIR ne dépend que de N et de n, pas de R. "
                    + (f"Motifs conformes parmi ceux comparés : N = {', '.join(map(str, ok_n))}."
                       if ok_n else "Aucun des motifs comparés n'atteint le seuil.")
                    + f"\n- **Capacité** : {radio.Utilisateurs_actifs_cellule:.0f} utilisateurs "
                      f"actifs pour {radio.Canaux_par_cellule:.1f} canaux par cellule "
                      f"(rapport {ratio:.1f})."
                    + f"\n- **Densité maximale supportée** : {result.max_density_ab_km2:.3f} "
                      f"ab./km² (densité actuelle : {params.Dst_ab:g})."
                    + "\n- **Levier de capacité** : réduire R diminue le nombre d'abonnés par "
                      "cellule, mais n'améliore pas le SIR.")

    # ---------------- onglet 2 : plan
    with tab_plan:
        left, right = st.columns([3, 2], gap="large")
        with left:
            show_figure(render_png(plots_plan.plot_plan, result.plan,
                                   allocation=result.allocation),
                        f"plan_{result.plan.rows}x{result.plan.cols}_N{radio.N}.png")
        with right:
            with st.container(border=True):
                st.markdown(f"**Plan {result.plan.rows}×{result.plan.cols}, "
                            f"motif N = {radio.N}**")
                m1, m2 = st.columns(2)
                m1.metric("D théorique", f"{radio.D_km:.3f} km")
                m2.metric("D mesuré (min co-canal)",
                          "n/a" if result.d_measured_km is None
                          else f"{result.d_measured_km:.3f} km")
                st.caption("Hexagones pointe en haut, grille « odd-r », R = rayon centre-sommet. "
                           "Deux cellules voisines sont distantes de √3·R.")
            with st.container(border=True):
                st.markdown("**Groupes de fréquences**")
                st.dataframe(pd.DataFrame([{
                    "Groupe": g, "Nb canaux": len(chs)}
                    for g, chs in sorted(result.allocation.groups.items())]),
                    hide_index=True)

    # ---------------- onglet 3 : allocation
    with tab_alloc:
        st.subheader(f"Allocation {STRATEGY_LABELS[strategy].lower()} : "
                     f"{params.N_f} canaux, {params.N} groupes")
        if result.problems:
            for pb in result.problems:
                st.error(pb)
        else:
            st.success("Vérifications OK : partition exacte des canaux, groupes équilibrés, "
                       "cellules co-canal séparées d'au moins D.")

        both = {s: build_allocation(result.plan, params.N_f, s) for s in STRATEGIES}
        k1, k2 = st.columns(2)
        k1.metric("Paires de canaux consécutifs (contiguë)",
                  adjacent_pairs_in_same_group(both["contigue"].groups))
        k2.metric("Paires de canaux consécutifs (entrelacée)",
                  adjacent_pairs_in_same_group(both["entrelacee"].groups))

        df_groups = pd.DataFrame([{
            "Groupe": g, "Nb canaux": len(chs), "Canaux": " ".join(map(str, chs))}
            for g, chs in sorted(result.allocation.groups.items())])
        st.dataframe(df_groups, hide_index=True)

        show_figure(render_png(plots_studies.plot_allocation_comparison,
                               both["contigue"], both["entrelacee"]),
                    f"allocation_contigue_vs_entrelacee_N{radio.N}.png")

        cell_by_id = {c.cell_id: c for c in result.plan.cells}
        df_cells = pd.DataFrame([{
            "cell_id": a.cell_id, "ligne": cell_by_id[a.cell_id].row,
            "colonne": cell_by_id[a.cell_id].col, "Groupe": a.group,
            "Nb canaux": len(a.channels), "Canaux": " ".join(map(str, a.channels))}
            for a in result.allocation.assignments])
        with st.expander(f"Groupe et canaux de chacune des {len(df_cells)} cellules"):
            st.dataframe(df_cells, hide_index=True)
            st.download_button("Télécharger l'allocation par cellule (CSV)", csv_bytes(df_cells),
                               file_name=f"allocation_cellules_{strategy}_N{radio.N}.csv",
                               mime="text/csv")

    # ---------------- onglet 4 : etudes
    with tab_studies:
        if not result.density_rows:
            st.info("Études non calculées.")
        else:
            st.subheader("Impact de la densité d'abonnés")
            left, right = st.columns([3, 2], gap="large")
            with left:
                show_figure(render_png(plots_studies.plot_density_vs_channels,
                                       list(result.density_rows)), "densite_vs_canaux.png")
            with right:
                with st.container(border=True):
                    st.markdown("**Densité maximale supportée** (1 canal par utilisateur actif)")
                    patterns = result.studies.patterns
                    for col, n_cells in zip(st.columns(len(patterns)), patterns):
                        col.metric(f"N = {n_cells}",
                                   f"{max_density_supported(params, n_cells):.2f}",
                                   help="ab./km²")
                    st.caption(f"En ab./km². Densité actuelle : {params.Dst_ab:g} ab./km².")
            with st.expander("Tableau détaillé (densité × motif)"):
                st.dataframe(pd.DataFrame(list(result.density_rows)), hide_index=True)

            st.subheader(f"Impact de l'environnement (zone = {result.studies.zone_area_km2:g} km²)")
            left, right = st.columns(2, gap="large")
            with left:
                show_figure(render_png(plots_studies.plot_environment_radius_sites,
                                       list(result.env_rows)), "environnement_R_sites.png")
            with right:
                show_figure(render_png(plots_studies.plot_environment_sir,
                                       list(result.env_rows), params.SIR_min_dB),
                            "environnement_sir.png")
            with st.expander("Tableau détaillé (environnement × motif)"):
                st.dataframe(pd.DataFrame(list(result.env_rows)), hide_index=True)
    # ---------------- onglet 5 : options d'amelioration (enonce, section 6)
    with tab_options:
        envs = result.studies.environments if result.studies else {}
        zone_area = result.studies.zone_area_km2 if result.studies else 5000.0

        # ---- 1) plusieurs motifs
        st.subheader("1. Comparaison de plusieurs motifs cellulaires")
        candidates = [n for n in VALID_N if 3 <= n <= params.N_f]
        chosen = st.multiselect("Motifs à comparer", candidates,
                                default=[n for n in ext.DEFAULT_PATTERNS if n in candidates])
        if chosen:
            rows_p = ext.pattern_comparison(params, chosen)
            n_min = next((r["N"] for r in rows_p if r["Motif_minimal"]), None)
            if n_min is None:
                st.warning("Aucun des motifs choisis ne respecte SIR ≥ SIR_min.")
            else:
                st.info(f"Motif minimal valide parmi ceux comparés : **N = {n_min}**. "
                        "Plus N augmente, plus le SIR monte, mais moins il reste de canaux par cellule.")
            df_p = pd.DataFrame(rows_p).drop(columns=["Motif_minimal"])
            df_p["SIR_ok"] = df_p["SIR_ok"].map({True: "oui", False: "non"})
            df_p = df_p.rename(columns={
                "D_sur_R": "D/R", "R_km": "R (km)", "D_km": "D (km)", "SIR_dB": "SIR (dB)",
                "Marge_SIR_dB": "Marge (dB)", "SIR_ok": "SIR ≥ SIR_min",
                "Canaux_par_cellule": "Canaux / cellule", "Actifs_par_cellule": "Actifs / cellule",
                "Actifs_sur_canaux": "Actifs / canaux"})
            st.dataframe(style_yes_no(df_p, "SIR ≥ SIR_min"), hide_index=True)
            st.download_button("Télécharger (CSV)", csv_bytes(df_p),
                               file_name="comparaison_motifs.csv", mime="text/csv")
            l1, r1 = st.columns(2, gap="large")
            with l1:
                show_figure(render_png(plots_extensions.plot_pattern_sir, rows_p,
                                       params.SIR_min_dB), "motifs_sir.png")
            with r1:
                show_figure(render_png(plots_extensions.plot_pattern_capacity, rows_p),
                            "motifs_canaux.png")

        # ---- 2) plusieurs exposants
        st.subheader("2. Comparaison de plusieurs exposants de propagation")
        sweep = ext.exponent_sweep(params, zone_area_km2=zone_area,
                                   patterns=[n for n in (3, 4, 7, 9, 12) if n <= params.N_f])
        l2, r2 = st.columns(2, gap="large")
        with l2:
            show_figure(render_png(plots_extensions.plot_exponent_radius_sites, sweep, envs),
                        "exposant_R_sites.png")
        with r2:
            show_figure(render_png(plots_extensions.plot_exponent_sir, sweep,
                                   params.SIR_min_dB, envs), "exposant_sir.png")
        with st.expander("Tableau détaillé (exposant × motif)"):
            st.dataframe(pd.DataFrame(sweep), hide_index=True)

        # ---- 3) positionnement automatique de clusters
        st.subheader("3. Positionnement automatique de clusters (coordonnées GPS fictives)")
        default_radius = round(math.sqrt(zone_area / math.pi), 1)
        c1, c2, c3 = st.columns(3)
        lat0 = c1.number_input("Latitude du centre (fictive)", value=ext.DEFAULT_CENTER[0],
                               min_value=-80.0, max_value=80.0, step=0.01, format="%.4f",
                               key="map_lat")
        lon0 = c2.number_input("Longitude du centre (fictive)", value=ext.DEFAULT_CENTER[1],
                               min_value=-179.0, max_value=179.0, step=0.01, format="%.4f",
                               key="map_lon")
        zone_r = c3.number_input("Rayon de la zone à couvrir (km)", value=float(default_radius),
                                 min_value=float(radio.R_km), max_value=150.0, step=1.0,
                                 key="map_radius")
        cmap = ext.build_cluster_map(radio.N, radio.R_km, params.N_f, float(zone_r),
                                     (float(lat0), float(lon0)), strategy)
        map_problems = ext.verify_cluster_map(cmap)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Clusters placés", cmap.n_clusters)
        k2.metric("Cellules au total", cmap.n_cells)
        k3.metric("Cellules dans la zone", cmap.n_cells_in_zone)
        k4.metric("Cellules par cluster", cmap.N)
        if map_problems:
            for pb in map_problems[:5]:
                st.error(pb)
        else:
            st.success("Vérifications OK : chaque cluster contient les N groupes, "
                       "et deux cellules co-canal sont distantes d'au moins D.")

        left, right = st.columns(2, gap="large")
        with left:
            show_figure(render_png(plots_extensions.plot_cluster_map, cmap),
                        f"clusters_N{cmap.N}.png")
        with right:
            with st.container(border=True):
                st.markdown("**Carte interactive** (fond de carte, connexion internet requise)")
                html = build_leaflet_html(cmap, f"Plan de fréquences, motif N = {cmap.N}")
                components.html(html, height=560)
        d1, d2, d3 = st.columns(3)
        d1.download_button("Carte interactive (HTML)", html.encode("utf-8"),
                           file_name=f"carte_clusters_N{cmap.N}.html", mime="text/html", **STRETCH)
        d2.download_button("Export GeoJSON", json.dumps(ext.to_geojson(cmap)).encode("utf-8"),
                           file_name=f"clusters_N{cmap.N}.geojson", mime="application/geo+json",
                           **STRETCH)
        d3.download_button("Cellules (CSV)", csv_bytes(pd.DataFrame(ext.cells_table(cmap))),
                           file_name=f"clusters_cellules_N{cmap.N}.csv", mime="text/csv", **STRETCH)
        st.caption("Les coordonnées GPS sont fictives (centre modifiable). Les cellules "
                   "estompées complètent un cluster hors de la zone.")
        
    # ---------------- onglet 5 : export
    with tab_export:
        summary = build_summary_text(result)
        st.code(summary, language="text")
        b1, b2 = st.columns(2)
        b1.download_button("Télécharger la synthèse (.txt)", summary.encode("utf-8"),
                           file_name="synthese.txt", mime="text/plain", **STRETCH)
        if b2.button("Exporter tous les résultats dans results/p4_final/", **STRETCH):
            files = export_all(result)
            st.success(f"{len(files)} fichiers écrits dans {files[0].parent.parent}")
            st.write([str(f.name) for f in files])


if __name__ == "__main__":
    main()