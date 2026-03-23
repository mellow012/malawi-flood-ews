"""
Malawi Flood EWS — Historical Event Comparison Page
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium


# ── DATA ─────────────────────────────────────────────────────────────────────
@st.cache_data
def get_events() -> pd.DataFrame:
    return pd.DataFrame([
        {'event':'Cyclone Idai',  'year':2019,'date':'March 14, 2019',
         'category':'Tropical Cyclone','flood_area_km2':95.4,
         'rain_event_mm':40.9,'rain_30d_mm':200.8,'rain_peak_mm':23.0,
         'pop_affected':975000,'deaths':59,
         'districts':'Chikwawa, Nsanje, Phalombe',
         'model_auc':0.9984,'model_iou':0.9799,
         'color':'#00d4ff','icon':'🌀'},
        {'event':'Cyclone Freddy','year':2023,'date':'March 11, 2023',
         'category':'Tropical Cyclone','flood_area_km2':130.4,
         'rain_event_mm':131.6,'rain_30d_mm':178.3,'rain_peak_mm':45.2,
         'pop_affected':508800,'deaths':679,
         'districts':'Blantyre, Chikwawa, Nsanje',
         'model_auc':0.9978,'model_iou':None,
         'color':'#ff8800','icon':'🌀'},
        {'event':'Floods 2025',   'year':2025,'date':'January–March 2025',
         'category':'Seasonal Flooding','flood_area_km2':90.4,
         'rain_event_mm':89.2,'rain_30d_mm':165.4,'rain_peak_mm':31.8,
         'pop_affected':142000,'deaths':12,
         'districts':'Chikwawa, Nsanje',
         'model_auc':0.9965,'model_iou':0.9174,
         'color':'#00cc66','icon':'🌧️'},
        {'event':'Auto 2026',     'year':2026,'date':'March 22, 2026',
         'category':'Live Detection','flood_area_km2':128.4,
         'rain_event_mm':None,'rain_30d_mm':None,'rain_peak_mm':None,
         'pop_affected':None,'deaths':None,
         'districts':'Chikwawa, Nsanje',
         'model_auc':None,'model_iou':None,
         'color':'#ff4444','icon':'📡'},
    ])


@st.cache_data
def get_timeline() -> pd.DataFrame:
    return pd.DataFrame([
        {'month':'2019-01','flood_area':0,    'event':'Idai 2019'},
        {'month':'2019-02','flood_area':0,    'event':'Idai 2019'},
        {'month':'2019-03','flood_area':95.4, 'event':'Idai 2019'},
        {'month':'2019-04','flood_area':42.1, 'event':'Idai 2019'},
        {'month':'2019-05','flood_area':12.3, 'event':'Idai 2019'},
        {'month':'2023-01','flood_area':0,    'event':'Freddy 2023'},
        {'month':'2023-02','flood_area':8.2,  'event':'Freddy 2023'},
        {'month':'2023-03','flood_area':130.4,'event':'Freddy 2023'},
        {'month':'2023-04','flood_area':61.2, 'event':'Freddy 2023'},
        {'month':'2023-05','flood_area':18.7, 'event':'Freddy 2023'},
        {'month':'2025-01','flood_area':90.4, 'event':'Floods 2025'},
        {'month':'2025-02','flood_area':78.3, 'event':'Floods 2025'},
        {'month':'2025-03','flood_area':54.1, 'event':'Floods 2025'},
        {'month':'2026-03','flood_area':128.4,'event':'Auto 2026'},
    ])


_EVENT_COLORS: dict[str, str] = {
    'Idai 2019':   '#00d4ff',
    'Freddy 2023': '#ff8800',
    'Floods 2025': '#00cc66',
    'Auto 2026':   '#ff4444',
}


def _color(name: str) -> str:
    return _EVENT_COLORS.get(name, '#8ba3bc')


def _fillcolor(name: str) -> str:
    h = _color(name).lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},0.08)'


def _fmt(val: object, col: str) -> str:
    """Safely format any DataFrame cell value to string."""
    if val is None:
        return '—'
    try:
        f = float(str(val))
        if np.isnan(f):
            return '—'
        if col in ('AUC-ROC', 'IoU'):
            return f"{f:.4f}"
        if col in ('Pop. Affected', 'Deaths', 'Year'):
            return f"{int(f):,}"
        if col in ('Flood Area (km²)', 'Event Rain (mm)', '30d Rain (mm)'):
            return f"{f:.1f}"
        return str(val)
    except (ValueError, TypeError):
        return str(val)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def show() -> None:
    st.markdown("""
    <div class="main-header">
        <h1>📅 Historical Event Comparison</h1>
        <p>Cyclone Idai 2019 · Cyclone Freddy 2023 · Floods 2025 · Live 2026</p>
        <span class="header-badge">4 EVENTS · 7 YEARS · LOWER SHIRE VALLEY</span>
    </div>
    """, unsafe_allow_html=True)

    events_df = get_events()
    timeline  = get_timeline()

    selected: list[str] = st.multiselect(
        "Select events to compare",
        options=events_df['event'].tolist(),
        default=events_df['event'].tolist()
    )
    df = events_df[events_df['event'].isin(selected)]
    if df.empty:
        st.info("Select at least one event.")
        return

    # ── Event cards ───────────────────────────────────────────────────
    st.markdown('<p class="section-header">Event Overview</p>',
                unsafe_allow_html=True)
    cols = st.columns(len(df))
    for col, (_, row) in zip(cols, df.iterrows()):
        with col:
            def _notnull(v: object) -> bool:
                if v is None: return False
                try: return not np.isnan(float(str(v)))
                except (ValueError, TypeError): return v != ''

            color: str      = str(row['color'])
            iou_str: str    = f"{float(str(row['model_iou'])):.4f}"        if _notnull(row['model_iou'])    else '—'
            auc_str: str    = f"{float(str(row['model_auc'])):.4f}"        if _notnull(row['model_auc'])    else '—'
            deaths_str: str = f"{int(float(str(row['deaths']))):,}"        if _notnull(row['deaths'])       else 'monitoring'
            pop_str: str    = f"{int(float(str(row['pop_affected']))):,}"   if _notnull(row['pop_affected']) else 'est. in progress'
            rain_str: str   = f"{float(str(row['rain_event_mm'])):.1f} mm" if _notnull(row['rain_event_mm']) else 'pending'
            st.markdown(f"""
            <div style='background:#0f1f35;border:1px solid {color};
                        border-top:4px solid {color};border-radius:10px;
                        padding:1.2rem;margin-bottom:0.5rem;'>
                <div style='font-size:1.8rem;margin-bottom:0.3rem;'>{row['icon']}</div>
                <div style='color:#fff;font-weight:600;font-size:1rem;'>{row['event']}</div>
                <div style='color:#8ba3bc;font-size:0.78rem;margin:0.2rem 0 0.8rem;'>{row['date']}</div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;font-size:0.78rem;'>
                    <div style='color:#8ba3bc;'>Flood area</div>
                    <div style='color:{color};font-weight:600;font-family:IBM Plex Mono;'>
                        {float(str(row['flood_area_km2'])):.1f} km²</div>
                    <div style='color:#8ba3bc;'>Event rain</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>{rain_str}</div>
                    <div style='color:#8ba3bc;'>Pop. affected</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>{pop_str}</div>
                    <div style='color:#8ba3bc;'>Deaths</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>{deaths_str}</div>
                    <div style='color:#8ba3bc;'>AUC-ROC</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>{auc_str}</div>
                    <div style='color:#8ba3bc;'>IoU</div>
                    <div style='color:#c8d8e8;font-family:IBM Plex Mono;'>{iou_str}</div>
                </div>
                <div style='margin-top:0.8rem;padding-top:0.6rem;
                            border-top:1px solid #1e3a5a;color:#4a6a8a;font-size:0.72rem;'>
                    {row['districts']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p class="section-header">Flood Area Comparison</p>',
                    unsafe_allow_html=True)
        fig_bar = go.Figure()
        for _, row in df.iterrows():
            fig_bar.add_trace(go.Bar(
                x=[str(row['event'])],
                y=[float(str(row['flood_area_km2']))],
                name=str(row['event']),
                marker_color=str(row['color']),
                marker_opacity=0.85))
        for y_val, clr, label in [
            (100, '#ffcc00', 'MEDIUM (100 km²)'),
            (150, '#ff8800', 'HIGH (150 km²)'),
            (300, '#ff4444', 'CRITICAL (300 km²)'),
        ]:
            fig_bar.add_hline(y=y_val, line_dash='dash', line_color=clr,
                              annotation_text=label, annotation_font_color=clr)
        fig_bar.update_layout(
            paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
            font=dict(color='#c8d8e8'),
            xaxis=dict(gridcolor='#1e3a5a'),
            yaxis=dict(gridcolor='#1e3a5a', title='km²'),
            showlegend=False, height=320, margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_bar, width='stretch')

    with col2:
        st.markdown('<p class="section-header">Rainfall vs Flood Area</p>',
                    unsafe_allow_html=True)
        df_rain = df[df['rain_event_mm'].notna()].copy()
        fig_sc  = go.Figure()
        for _, row in df_rain.iterrows():
            fig_sc.add_trace(go.Scatter(
                x=[float(str(row['rain_event_mm']))],
                y=[float(str(row['flood_area_km2']))],
                mode='markers+text',
                marker=dict(size=20, color=str(row['color']), opacity=0.85,
                            line=dict(width=2, color='#ffffff')),
                text=[str(row['event'])],
                textposition='top center',
                textfont=dict(color='#c8d8e8', size=10),
                name=str(row['event'])))
        fig_sc.update_layout(
            paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
            font=dict(color='#c8d8e8'),
            xaxis=dict(gridcolor='#1e3a5a', title='Event rainfall (mm)'),
            yaxis=dict(gridcolor='#1e3a5a', title='Flood area (km²)'),
            showlegend=False, height=320, margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_sc, width='stretch')

    st.markdown("---")

    # ── Timeline ──────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Flood Extent Timeline</p>',
                unsafe_allow_html=True)
    fig_tl = go.Figure()
    for event_name, grp in timeline[
            timeline['event'].isin(selected)].groupby('event'):
        name_str: str = str(event_name)
        fig_tl.add_trace(go.Scatter(
            x=grp['month'], y=grp['flood_area'],
            mode='lines+markers', name=name_str,
            line=dict(color=_color(name_str), width=2),
            marker=dict(size=8), fill='tozeroy',
            fillcolor=_fillcolor(name_str)))
    fig_tl.update_layout(
        paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
        font=dict(color='#c8d8e8'),
        xaxis=dict(gridcolor='#1e3a5a', title='Month'),
        yaxis=dict(gridcolor='#1e3a5a', title='Flood area (km²)'),
        legend=dict(bgcolor='#0f1f35', bordercolor='#1e3a5a'),
        height=280, margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig_tl, width='stretch')

    st.markdown("---")

    # ── Map ───────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Spatial Comparison</p>',
                unsafe_allow_html=True)
    st.caption("Marker size = relative flood area. All events — Lower Shire Valley.")
    m = folium.Map(location=[-16.2, 34.55], zoom_start=8,
                   tiles='CartoDB dark_matter')
    locs_map: dict[str, list[tuple[float, float]]] = {
        'Cyclone Idai':   [(-16.02,34.80),(-16.55,35.00),(-15.92,34.68)],
        'Cyclone Freddy': [(-16.02,34.80),(-15.79,35.03),(-16.33,34.90)],
        'Floods 2025':    [(-16.02,34.80),(-16.55,35.00)],
        'Auto 2026':      [(-16.02,34.80),(-16.55,35.00)],
    }
    for _, row in df.iterrows():
        for lat, lon in locs_map.get(str(row['event']), []):
            folium.CircleMarker(
                location=[lat, lon],
                radius=max(8, float(str(row['flood_area_km2'])) / 8),
                color=str(row['color']), fill=True,
                fill_color=str(row['color']), fill_opacity=0.4, weight=2,
                tooltip=folium.Tooltip(
                    f"<b>{row['event']}</b><br>"
                    f"Flood: {row['flood_area_km2']:.1f} km²<br>"
                    f"Date: {row['date']}")
            ).add_to(m)
    folium.Rectangle(
        bounds=[[-16.80, 34.20], [-15.60, 34.90]],
        color='#38bdf8', fill=False, weight=1, dash_array='6 4'
    ).add_to(m)
    st_folium(m, width=None, height=400, returned_objects=[])

    st.markdown("---")

    # ── Table ─────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Full Comparison Table</p>',
                unsafe_allow_html=True)
    table_df = df[[
        'event', 'year', 'flood_area_km2', 'rain_event_mm',
        'rain_30d_mm', 'pop_affected', 'deaths', 'model_auc', 'model_iou'
    ]].copy()
    table_df.columns = pd.Index([
        'Event', 'Year', 'Flood Area (km²)', 'Event Rain (mm)',
        '30d Rain (mm)', 'Pop. Affected', 'Deaths', 'AUC-ROC', 'IoU'
    ])
    for c in table_df.columns:
        table_df[c] = table_df[c].apply(lambda x, col=c: _fmt(x, col))

    st.dataframe(table_df, width='stretch', hide_index=True)
    st.caption("* Auto 2026 = live rolling detection 2026-03-22. "
               "Population/death figures from ReliefWeb.")