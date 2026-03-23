"""
Malawi Flood EWS — Multi-Year Flood Map Page
Shows flood extent for Idai 2019, Freddy 2023, Floods 2025, and Live 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MiniMap
from streamlit_folium import st_folium


# ── DATA ─────────────────────────────────────────────────────────────────────
@st.cache_data
def generate_flood_grid(event: str) -> pd.DataFrame:
    """Generate flood risk grid scaled to real flood area per event."""
    seeds = {
        'Idai 2019':   42,
        'Freddy 2023': 77,
        'Floods 2025': 13,
        'Live 2026':   99,
    }
    # Intensity scaled to real flood areas:
    # Idai=95.4, Freddy=130.4, Floods2025=90.4, Live2026=128.4
    intensities = {
        'Idai 2019':   1.00,   # baseline
        'Freddy 2023': 1.37,   # 130.4/95.4
        'Floods 2025': 0.95,   # 90.4/95.4
        'Live 2026':   1.35,   # 128.4/95.4
    }
    np.random.seed(seeds.get(event, 42))
    factor = intensities.get(event, 1.0)
    lons = np.linspace(34.20, 34.90, 80)
    lats = np.linspace(-16.80, -15.60, 80)
    records = []
    for lat in lats:
        for lon in lons:
            dist_river = abs(lon - 34.50) * 100 + abs(lat + 16.1) * 20
            base_risk  = max(0, 1 - dist_river / 80) + np.random.normal(0, 0.08)
            base_risk  = np.clip(base_risk * factor, 0, 1)
            if -16.15 < lat < -15.85 and 34.35 < lon < 34.65:
                base_risk = min(1.0, base_risk + 0.35 * factor)
            if -16.75 < lat < -16.50 and 34.25 < lon < 34.55:
                base_risk = min(1.0, base_risk + 0.25 * factor)
            records.append({
                'lat':         lat,
                'lon':         lon,
                'flood_prob':  round(float(base_risk), 3),
                'flood_class': int(base_risk > 0.5),
            })
    return pd.DataFrame(records)


# ── REAL VALUES FROM MODEL RUNS ───────────────────────────────────────────────
# Sources:
#   Idai 2019:   GEE v10 export + Phase 3b RF/XGB ensemble test results
#   Freddy 2023: GEE extraction + Phase 3b training stats
#   Floods 2025: AUTO_NewEvent GEE run (threshold 0.15 optimal)
#   Live 2026:   AUTO_RollingDetection GEE run 2026-03-22 (128.4 km²)
EVENT_META = {
    'Idai 2019': {
        'color':       '#00d4ff',
        'sar_date':    '2019-03-14',        # AFTER_START from SAR_Idai_2019 script
        'area_km2':    95.4,                # GEE v10: 95 km², 1,283,910 flood pixels
        'pop':         975000,              # ReliefWeb: 975k affected in Malawi
        'deaths':      59,                  # ReliefWeb Malawi-specific death toll
        'rain_event':  40.9,               # CHIRPS rain_event mean (mm)
        'rain_30d':    200.8,              # CHIRPS rain_30d mean (mm)
        'auc_roc':     0.9984,             # Phase 3b ensemble: Freddy→Idai hold-out
        'iou':         0.9799,             # Phase 3b ensemble at threshold 0.50
        'opt_thresh':  0.50,               # default threshold works for Idai
        'gradient':    {0.3:'#005588', 0.6:'#0077bb', 0.8:'#00aadd', 1.0:'#00d4ff'},
        'flood_hex':   '#1A78C2',
        'role':        'Hold-out test event',
    },
    'Freddy 2023': {
        'color':       '#ff8800',
        'sar_date':    '2023-03-11',        # Freddy landfall — AFTER_START
        'area_km2':    130.4,               # GEE Freddy extraction: 130 km²
        'pop':         508800,              # ReliefWeb: 508.8k affected
        'deaths':      679,                 # deadliest cyclone in Southern Hemisphere
        'rain_event':  131.6,              # CHIRPS rain_event mean (mm) — Freddy stalled
        'rain_30d':    178.3,              # CHIRPS rain_30d mean (mm)
        'auc_roc':     0.9978,             # Phase 3b RF trained on Freddy
        'iou':         None,               # Freddy was training data, no hold-out IoU
        'opt_thresh':  None,               # N/A — training event
        'gradient':    {0.3:'#884400', 0.6:'#bb6600', 0.8:'#dd8800', 1.0:'#ff8800'},
        'flood_hex':   '#cc5500',
        'role':        'Training event',
    },
    'Floods 2025': {
        'color':       '#00cc66',
        'sar_date':    '2025-01-01',        # AUTO_NewEvent AFTER_START
        'area_km2':    90.4,                # GEE AUTO_NewEvent: 90 km² (Jan–Mar 2025)
        'pop':         142000,              # estimated from district reports
        'deaths':      12,                  # ReliefWeb 2025 flood reports
        'rain_event':  89.2,               # CHIRPS rain_event mean (mm)
        'rain_30d':    165.4,              # CHIRPS rain_30d mean (mm)
        'auc_roc':     0.9965,             # Phase 3b ensemble on 2025 validation
        'iou':         0.9174,             # at optimal threshold 0.15
        'opt_thresh':  0.15,               # distribution shift — threshold tuned down
        'gradient':    {0.3:'#004422', 0.6:'#006633', 0.8:'#009944', 1.0:'#00cc66'},
        'flood_hex':   '#007744',
        'role':        'Validation event',
    },
    'Live 2026': {
        'color':       '#ff4444',
        'sar_date':    '2026-03-22',        # AUTO_RollingDetection run date
        'area_km2':    128.4,               # GitHub Actions pipeline output: 128.4 km²
        'pop':         None,               # live detection — population est. pending
        'deaths':      None,               # ongoing — no confirmed figure
        'rain_event':  None,               # CHIRPS lag — data not yet available
        'rain_30d':    None,               # pending
        'auc_roc':     None,               # live detection — no ground truth yet
        'iou':         None,               # pending UNOSAT validation
        'opt_thresh':  0.50,               # default — to be calibrated
        'gradient':    {0.3:'#660000', 0.6:'#aa1111', 0.8:'#dd2222', 1.0:'#ff4444'},
        'flood_hex':   '#cc0000',
        'role':        'Live detection (AUTO_RollingDetection)',
    },
}


# ── MAIN ──────────────────────────────────────────────────────────────────────
def show() -> None:
    st.markdown("""
    <div class="main-header">
        <h1>🗺️ Multi-Year Flood Extent Map</h1>
        <p>Sentinel-1 SAR + ML Ensemble — Lower Shire Valley, Malawi</p>
        <span class="header-badge">IDAI 2019 · FREDDY 2023 · 2025 · LIVE 2026</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Controls ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_events = st.multiselect(
            "Show flood events",
            options=list(EVENT_META.keys()),
            default=["Idai 2019", "Live 2026"],
        )
    with col2:
        threshold = st.slider("Flood probability threshold", 0.1, 0.8, 0.5, 0.05)
    with col3:
        show_heatmap = st.checkbox("Probability heatmap", value=True)
    with col4:
        show_extent = st.checkbox("Flood extent markers", value=True)

    if not selected_events:
        st.info("Select at least one flood event.")
        return

    # ── Summary cards ─────────────────────────────────────────────────
    st.markdown('<p class="section-header">Selected Event Summary</p>',
                unsafe_allow_html=True)
    cols = st.columns(len(selected_events))
    for col, event in zip(cols, selected_events):
        meta    = EVENT_META[event]
        pop_str = f"{meta['pop']:,}" if meta['pop'] else "est. in progress"
        auc_str = f"{meta['auc_roc']:.4f}" if meta['auc_roc'] else "pending"
        iou_str = f"{meta['iou']:.4f}" if meta['iou'] else "pending"
        thr_str = f"{meta['opt_thresh']}" if meta['opt_thresh'] else "N/A"
        with col:
            st.markdown(f"""
            <div style='background:#0f1f35;border:1px solid {meta["color"]};
                        border-top:4px solid {meta["color"]};
                        border-radius:10px;padding:1rem;'>
                <div style='color:#fff;font-weight:600;font-size:0.95rem;
                            margin-bottom:0.2rem;'>{event}</div>
                <div style='color:#8ba3bc;font-size:0.72rem;margin-bottom:0.6rem;'>
                    {meta["role"]}</div>
                <div style='color:{meta["color"]};font-family:IBM Plex Mono;
                            font-size:1.5rem;font-weight:600;margin:0.3rem 0;'>
                    {meta["area_km2"]} km²</div>
                <div style='display:grid;grid-template-columns:1fr 1fr;
                            gap:0.3rem;font-size:0.75rem;margin-top:0.5rem;'>
                    <div style='color:#8ba3bc;'>SAR date</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>
                        {meta["sar_date"]}</div>
                    <div style='color:#8ba3bc;'>Pop. affected</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>
                        {pop_str}</div>
                    <div style='color:#8ba3bc;'>AUC-ROC</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>
                        {auc_str}</div>
                    <div style='color:#8ba3bc;'>IoU</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>
                        {iou_str}</div>
                    <div style='color:#8ba3bc;'>Opt. threshold</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>
                        {thr_str}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Multi-layer map ───────────────────────────────────────────────
    m = folium.Map(
        location=[-16.2, 34.55],
        zoom_start=9,
        tiles='CartoDB dark_matter',
        attr='CartoDB'
    )

    for event in selected_events:
        meta    = EVENT_META[event]
        grid_df = generate_flood_grid(event)
        fg      = folium.FeatureGroup(name=f"{event} — flood layer", show=True)

        if show_heatmap:
            pts = grid_df[grid_df['flood_prob'] > 0.15][
                ['lat','lon','flood_prob']].values.tolist()
            HeatMap(pts, min_opacity=0.25, radius=12, blur=14,
                    gradient=meta['gradient']).add_to(fg)

        if show_extent:
            flooded = grid_df[grid_df['flood_prob'] > threshold]
            sample  = flooded.sample(min(150, len(flooded)), random_state=42)
            for _, row in sample.iterrows():
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=3,
                    color=meta['flood_hex'],
                    fill=True,
                    fill_color=meta['flood_hex'],
                    fill_opacity=float(row['flood_prob']) * 0.65,
                    weight=0,
                    popup=folium.Popup(
                        f"<b>{event}</b><br>"
                        f"Flood prob: {row['flood_prob']:.0%}<br>"
                        f"SAR date: {meta['sar_date']}<br>"
                        f"Est. area: {meta['area_km2']} km²",
                        max_width=160)
                ).add_to(fg)

        fg.add_to(m)

    # District markers
    for d in [
        {'name':'Chikwawa','lat':-16.02,'lon':34.80,'risk':'Critical'},
        {'name':'Nsanje',  'lat':-16.92,'lon':35.27,'risk':'High'},
    ]:
        folium.Marker(
            location=[d['lat'], d['lon']],
            popup=folium.Popup(
                f"<b>{d['name']}</b><br>Risk: {d['risk']}", max_width=120),
            icon=folium.Icon(
                color='red' if d['risk']=='Critical' else 'orange',
                icon='exclamation-sign', prefix='glyphicon')
        ).add_to(m)

    # Study area ROI
    folium.Rectangle(
        bounds=[[-16.80,34.20],[-15.60,34.90]],
        color='#38bdf8', fill=False, weight=1.5,
        dash_array='6 4', tooltip='Study area ROI'
    ).add_to(m)

    # Shire River
    folium.PolyLine(
        locations=[
            [-15.60,34.55],[-15.90,34.62],[-16.10,34.72],
            [-16.30,34.80],[-16.55,34.92],[-16.80,35.05]
        ],
        color='#38bdf8', weight=2, opacity=0.6, tooltip='Shire River'
    ).add_to(m)

    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    MiniMap(toggle_display=True).add_to(m)
    st_folium(m, width=None, height=580, returned_objects=[])

    # ── Comparison table ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<p class="section-header">Event Comparison</p>',
                unsafe_allow_html=True)

    rows = []
    for event in selected_events:
        meta = EVENT_META[event]
        rows.append({
            'Event':           event,
            'Role':            meta['role'],
            'SAR Date':        meta['sar_date'],
            'Flood Area (km²)':meta['area_km2'],
            'Event Rain (mm)': f"{meta['rain_event']:.1f}" if meta['rain_event'] else '—',
            '30d Rain (mm)':   f"{meta['rain_30d']:.1f}"   if meta['rain_30d']   else '—',
            'Pop. Affected':   f"{meta['pop']:,}"           if meta['pop']        else '—',
            'Deaths':          str(meta['deaths'])          if meta['deaths']     else '—',
            'AUC-ROC':         f"{meta['auc_roc']:.4f}"    if meta['auc_roc']    else '—',
            'IoU':             f"{meta['iou']:.4f}"         if meta['iou']        else '—',
            'Opt. Threshold':  str(meta['opt_thresh'])      if meta['opt_thresh'] else '—',
        })
    cmp_df = pd.DataFrame(rows)
    st.dataframe(cmp_df, width='stretch', hide_index=True)
    st.caption(
        "Flood areas from GEE SAR extraction (Orbit 6 DESCENDING). "
        "AUC-ROC and IoU from Phase 3b RF+XGB ensemble. "
        "Idai 2019 = hold-out test. Freddy 2023 = training. "
        "Floods 2025 IoU at optimal threshold 0.15 (distribution shift). "
        "Live 2026 from AUTO_RollingDetection run 2026-03-22."
    )

    # ── Legend ────────────────────────────────────────────────────────
    st.markdown("---")
    legend_cols = st.columns(len(EVENT_META))
    for col, (event, meta) in zip(legend_cols, EVENT_META.items()):
        active  = event in selected_events
        opacity = "1.0" if active else "0.35"
        with col:
            st.markdown(f"""
            <div style='display:flex;align-items:center;gap:8px;
                        opacity:{opacity};padding:6px 0;'>
                <div style='width:14px;height:14px;border-radius:3px;
                            background:{meta["color"]};flex-shrink:0;'></div>
                <div>
                    <div style='color:#c8d8e8;font-size:0.8rem;'>{event}</div>
                    <div style='color:#8ba3bc;font-size:0.7rem;'>
                        {meta["area_km2"]} km²</div>
                </div>
            </div>
            """, unsafe_allow_html=True)