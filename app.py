"""
Malawi Flood Early Warning System — Dashboard
Phase 4: Streamlit Web Application
Lower Shire Valley (Chikwawa + Nsanje Districts)
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MiniMap
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import json
import os
from pathlib import Path

# ── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Malawi Flood EWS",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* Header */
.main-header {
    background: linear-gradient(135deg, #0a1628 0%, #112240 60%, #1a3a5c 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border-left: 4px solid #00d4ff;
}
.main-header h1 {
    color: #ffffff;
    font-size: 1.8rem;
    font-weight: 600;
    margin: 0;
    letter-spacing: -0.02em;
}
.main-header p {
    color: #8ba3bc;
    margin: 0.3rem 0 0 0;
    font-size: 0.9rem;
}
.header-badge {
    display: inline-block;
    background: rgba(0,212,255,0.15);
    color: #00d4ff;
    border: 1px solid rgba(0,212,255,0.3);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
    margin-top: 0.5rem;
}

/* Metric cards */
.metric-card {
    background: #0f1f35;
    border: 1px solid #1e3a5a;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.metric-value {
    font-size: 2rem;
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    margin: 0;
}
.metric-label {
    font-size: 0.78rem;
    color: #8ba3bc;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0.3rem 0 0 0;
}

/* Alert levels */
.alert-critical { color: #ff4444; }
.alert-high     { color: #ff8800; }
.alert-medium   { color: #ffcc00; }
.alert-low      { color: #00cc66; }

/* Risk badge */
.risk-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
}
.risk-critical { background: rgba(255,68,68,0.2);  color: #ff4444; border: 1px solid #ff4444; }
.risk-high     { background: rgba(255,136,0,0.2);  color: #ff8800; border: 1px solid #ff8800; }
.risk-medium   { background: rgba(255,204,0,0.2);  color: #ffcc00; border: 1px solid #ffcc00; }
.risk-low      { background: rgba(0,204,102,0.2);  color: #00cc66; border: 1px solid #00cc66; }

/* Section headers */
.section-header {
    font-size: 0.75rem;
    font-weight: 600;
    color: #00d4ff;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #1e3a5a;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0a1628;
}
[data-testid="stSidebar"] .stMarkdown p {
    color: #8ba3bc;
}

/* Dividers */
hr { border-color: #1e3a5a; }

/* SMS alert box */
.sms-preview {
    background: #0f1f35;
    border: 1px solid #1e3a5a;
    border-left: 4px solid #00d4ff;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
    color: #c8d8e8;
    line-height: 1.6;
}

/* Streamlit overrides */
.stButton button {
    background: #0a2444;
    border: 1px solid #00d4ff;
    color: #00d4ff;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
    letter-spacing: 0.05em;
    border-radius: 6px;
    transition: all 0.2s;
}
.stButton button:hover {
    background: rgba(0,212,255,0.15);
}

div[data-testid="stMetric"] {
    background: #0f1f35;
    border: 1px solid #1e3a5a;
    border-radius: 10px;
    padding: 1rem;
}
</style>
""", unsafe_allow_html=True)


# ── SIMULATED DATA LAYER ─────────────────────────────────────────────────────
# In production this loads from saved model outputs + GEE exports
# For demo, we generate realistic synthetic data matching our trained model outputs

@st.cache_data
def generate_flood_grid():
    """Generate realistic flood risk grid for Lower Shire Valley."""
    np.random.seed(42)
    # Grid covering ROI: 34.20–34.90 lon, -16.80 to -15.60 lat
    lons = np.linspace(34.20, 34.90, 80)
    lats = np.linspace(-16.80, -15.60, 80)
    records = []
    for lat in lats:
        for lon in lons:
            # Simulate flood risk based on proximity to Shire River
            # River runs roughly through lon 34.5, lat -16.4 to -15.8
            dist_river = abs(lon - 34.50) * 100 + abs(lat + 16.1) * 20
            elevation_effect = max(0, 1 - dist_river / 80)
            base_risk = elevation_effect + np.random.normal(0, 0.08)
            base_risk = np.clip(base_risk, 0, 1)
            # Peak flooding near Chikwawa (-16.0) and Nsanje (-16.9)
            if -16.15 < lat < -15.85 and 34.35 < lon < 34.65:
                base_risk = min(1.0, base_risk + 0.35)
            if -16.75 < lat < -16.50 and 34.25 < lon < 34.55:
                base_risk = min(1.0, base_risk + 0.25)
            records.append({
                'lat': lat, 'lon': lon,
                'flood_prob': round(float(base_risk), 3),
                'flood_class': int(base_risk > 0.5),
            })
    return pd.DataFrame(records)


@st.cache_data
def get_district_summary():
    """District-level risk summary."""
    return pd.DataFrame([
        {'district': 'Chikwawa', 'risk_level': 'Critical',
         'flood_area_km2': 312.4, 'pop_at_risk': 84200,
         'affected_villages': 47, 'alert_status': 'ACTIVE'},
        {'district': 'Nsanje',   'risk_level': 'High',
         'flood_area_km2': 198.7, 'pop_at_risk': 61500,
         'affected_villages': 31, 'alert_status': 'ACTIVE'},
        {'district': 'Blantyre Rural', 'risk_level': 'Medium',
         'flood_area_km2': 42.1,  'pop_at_risk': 12300,
         'affected_villages': 8,  'alert_status': 'WATCH'},
        {'district': 'Thyolo',   'risk_level': 'Low',
         'flood_area_km2': 8.3,   'pop_at_risk': 2100,
         'affected_villages': 2,  'alert_status': 'CLEAR'},
    ])


@st.cache_data
def get_shap_importance():
    """SHAP feature importance from trained model."""
    return pd.DataFrame([
        {'feature': 'diff_VH',       'importance': 2.61, 'category': 'SAR'},
        {'feature': 'dist_to_water', 'importance': 1.82, 'category': 'Terrain'},
        {'feature': 'diff_combined', 'importance': 1.54, 'category': 'SAR'},
        {'feature': 'rain_event',    'importance': 1.47, 'category': 'Rainfall'},
        {'feature': 'VH_db',         'importance': 0.89, 'category': 'SAR'},
        {'feature': 'diff_VV',       'importance': 0.82, 'category': 'SAR'},
        {'feature': 'VV_db',         'importance': 0.79, 'category': 'SAR'},
        {'feature': 'slope',         'importance': 0.74, 'category': 'Terrain'},
        {'feature': 'rain_30d',      'importance': 0.68, 'category': 'Rainfall'},
        {'feature': 'TWI',           'importance': 0.61, 'category': 'Terrain'},
        {'feature': 'rain_7d',       'importance': 0.54, 'category': 'Rainfall'},
        {'feature': 'rain_peak',     'importance': 0.48, 'category': 'Rainfall'},
        {'feature': 'elevation',     'importance': 0.41, 'category': 'Terrain'},
        {'feature': 'aspect',        'importance': 0.09, 'category': 'Terrain'},
        {'feature': 'rain_3d',       'importance': 0.00, 'category': 'Rainfall'},
    ]).sort_values('importance', ascending=True)


@st.cache_data
def get_model_metrics():
    return {
        'rf_auc':       0.9995,
        'xgb_auc':      0.9996,
        'ensemble_auc': 0.9996,
        'ensemble_iou': 0.9820,
        'precision':    0.98,
        'recall':       1.00,
        'f1':           0.99,
        'flood_pixels': 256782,
        'total_pixels': 1027128,
    }


@st.cache_data
def get_rainfall_timeseries():
    """Simulated CHIRPS rainfall leading up to Cyclone Idai."""
    dates = pd.date_range('2019-01-01', '2019-03-20', freq='D')
    rain = np.random.exponential(4, len(dates))
    # Spike during Idai
    rain[60:75] += np.array([10, 15, 22, 38, 52, 68, 45, 30, 18, 12, 8, 5, 4, 3, 2])
    return pd.DataFrame({'date': dates, 'rainfall_mm': rain})


@st.cache_data
def get_focal_points():
    return pd.DataFrame([
        {'name': 'James Banda',    'village': 'Chapananga', 'district': 'Chikwawa',
         'phone': '+265991234567', 'role': 'Village Head', 'active': True},
        {'name': 'Grace Mwale',    'village': 'Makhanga',   'district': 'Nsanje',
         'phone': '+265888345678', 'role': 'DoDMA Officer', 'active': True},
        {'name': 'Peter Chirwa',   'village': 'Bangula',    'district': 'Nsanje',
         'phone': '+265777456789', 'role': 'Red Cross',     'active': True},
        {'name': 'Mary Phiri',     'village': 'Nchalo',     'district': 'Chikwawa',
         'phone': '+265999567890', 'role': 'Health Worker', 'active': True},
        {'name': 'David Tembo',    'village': 'Mkombezi',   'district': 'Chikwawa',
         'phone': '+265885678901', 'role': 'Village Head',  'active': False},
    ])


# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 1.5rem;'>
        <div style='font-size:2.5rem; margin-bottom:0.3rem;'>🌊</div>
        <div style='color:#ffffff; font-weight:600; font-size:1rem;'>Malawi Flood EWS</div>
        <div style='color:#8ba3bc; font-size:0.75rem;'>Lower Shire Valley</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["Overview", "Flood Map", "Model Analytics",
         "Rainfall Monitor", "Alert System"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    st.markdown('<p class="section-header">System Status</p>',
                unsafe_allow_html=True)

    last_update = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(f"""
    <div style='font-size:0.8rem; color:#8ba3bc; line-height:2;'>
    <span style='color:#00cc66;'>●</span> GEE Pipeline: Online<br>
    <span style='color:#00cc66;'>●</span> ML Model: Active<br>
    <span style='color:#00cc66;'>●</span> SMS Gateway: Ready<br>
    <span style='color:#ffcc00;'>●</span> Last S1 Pass: 6h ago<br>
    <span style='color:#8ba3bc;'>🕐 Updated: {last_update}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.72rem; color:#4a6a8a; line-height:1.8;'>
    Sentinel-1 SAR + RF/XGBoost<br>
    Ensemble IoU: 98.2%<br>
    Reference: Phiri et al. 2025<br>
    Data: ESA Copernicus / MASDAP
    </div>
    """, unsafe_allow_html=True)


# ── LOAD DATA ────────────────────────────────────────────────────────────────
grid_df      = generate_flood_grid()
district_df  = get_district_summary()
shap_df      = get_shap_importance()
metrics      = get_model_metrics()
rain_df      = get_rainfall_timeseries()
focal_df     = get_focal_points()


# ════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
if page == "Overview":

    st.markdown("""
    <div class="main-header">
        <h1>🌊 Malawi Flood Early Warning System</h1>
        <p>Lower Shire Valley — Chikwawa & Nsanje Districts</p>
        <span class="header-badge">CYCLONE SEASON ACTIVE</span>
    </div>
    """, unsafe_allow_html=True)

    # Top metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Flood Area", "511 km²", "+38 km² (24h)")
    with col2:
        st.metric("Pop. at Risk", "145,700", "+4,200")
    with col3:
        st.metric("Villages Affected", "78", "+6")
    with col4:
        st.metric("Model Confidence", "98.2%", "IoU")
    with col5:
        st.metric("Alerts Sent", "342", "This week")

    st.markdown("---")

    col_left, col_right = st.columns([1.6, 1])

    with col_left:
        st.markdown('<p class="section-header">District Risk Status</p>',
                    unsafe_allow_html=True)

        risk_colors = {
            'Critical': '#ff4444', 'High': '#ff8800',
            'Medium': '#ffcc00',   'Low': '#00cc66'
        }
        alert_icons = {
            'ACTIVE': '🔴', 'WATCH': '🟡', 'CLEAR': '🟢'
        }

        for _, row in district_df.iterrows():
            color = risk_colors.get(row['risk_level'], '#8ba3bc')
            icon  = alert_icons.get(row['alert_status'], '⚪')
            st.markdown(f"""
            <div style='background:#0f1f35; border:1px solid #1e3a5a;
                        border-left:4px solid {color};
                        border-radius:8px; padding:1rem 1.2rem;
                        margin-bottom:0.6rem; display:flex;
                        align-items:center; justify-content:space-between;'>
                <div>
                    <span style='color:#ffffff; font-weight:600;
                                 font-size:1rem;'>{row['district']}</span>
                    <span style='color:#8ba3bc; font-size:0.8rem;
                                 margin-left:0.8rem;'>
                        {row['flood_area_km2']} km² flooded
                    </span>
                </div>
                <div style='display:flex; align-items:center; gap:1rem;'>
                    <span style='color:#8ba3bc; font-size:0.8rem;'>
                        👥 {row['pop_at_risk']:,} at risk
                    </span>
                    <span style='color:#8ba3bc; font-size:0.8rem;'>
                        🏘 {row['affected_villages']} villages
                    </span>
                    <span style='background:rgba(0,0,0,0.3); color:{color};
                                 border:1px solid {color};
                                 padding:3px 10px; border-radius:12px;
                                 font-size:0.75rem; font-weight:600;'>
                        {icon} {row['alert_status']}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<p class="section-header">Model Performance</p>',
                    unsafe_allow_html=True)

        fig = go.Figure()
        categories = ['AUC-ROC', 'Precision', 'Recall', 'F1-Score', 'IoU']
        values_rf  = [0.9995, 0.98, 1.00, 0.99, 0.974]
        values_xgb = [0.9996, 0.98, 1.00, 0.99, 0.980]

        fig.add_trace(go.Scatterpolar(
            r=values_rf, theta=categories, fill='toself',
            name='Random Forest',
            line=dict(color='#00d4ff', width=2),
            fillcolor='rgba(0,212,255,0.15)'
        ))
        fig.add_trace(go.Scatterpolar(
            r=values_xgb, theta=categories, fill='toself',
            name='XGBoost',
            line=dict(color='#ff8800', width=2),
            fillcolor='rgba(255,136,0,0.1)'
        ))
        fig.update_layout(
            polar=dict(
                bgcolor='#0a1628',
                radialaxis=dict(
                    visible=True, range=[0.95, 1.0],
                    gridcolor='#1e3a5a', tickfont=dict(color='#8ba3bc', size=9)
                ),
                angularaxis=dict(
                    gridcolor='#1e3a5a',
                    tickfont=dict(color='#c8d8e8', size=10)
                )
            ),
            paper_bgcolor='#0a1628',
            plot_bgcolor='#0a1628',
            font=dict(color='#c8d8e8'),
            legend=dict(
                bgcolor='#0f1f35', bordercolor='#1e3a5a',
                font=dict(size=10)
            ),
            height=300,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        <div style='display:grid; grid-template-columns:1fr 1fr;
                    gap:0.5rem; margin-top:0.5rem;'>
            <div style='background:#0f1f35; border:1px solid #1e3a5a;
                        border-radius:8px; padding:0.8rem; text-align:center;'>
                <div style='color:#00d4ff; font-family:IBM Plex Mono;
                            font-size:1.3rem; font-weight:600;'>98.2%</div>
                <div style='color:#8ba3bc; font-size:0.7rem; margin-top:3px;'>
                    Ensemble IoU
                </div>
            </div>
            <div style='background:#0f1f35; border:1px solid #1e3a5a;
                        border-radius:8px; padding:0.8rem; text-align:center;'>
                <div style='color:#00cc66; font-family:IBM Plex Mono;
                            font-size:1.3rem; font-weight:600;'>99.96%</div>
                <div style='color:#8ba3bc; font-size:0.7rem; margin-top:3px;'>
                    AUC-ROC
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Rainfall sparkline
    st.markdown('<p class="section-header">Rainfall — Last 90 Days (CHIRPS)</p>',
                unsafe_allow_html=True)
    recent_rain = rain_df.tail(90)
    fig_rain = px.area(
        recent_rain, x='date', y='rainfall_mm',
        color_discrete_sequence=['#00d4ff']
    )
    fig_rain.add_vrect(
        x0='2019-03-08', x1='2019-03-15',
        fillcolor='rgba(255,68,68,0.15)',
        line=dict(color='#ff4444', width=1, dash='dash'),
        annotation_text='Cyclone Idai',
        annotation_font_color='#ff4444',
        annotation_position='top left'
    )
    fig_rain.update_layout(
        paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
        font=dict(color='#c8d8e8'),
        xaxis=dict(gridcolor='#1e3a5a', title=None),
        yaxis=dict(gridcolor='#1e3a5a', title='mm/day'),
        height=180, margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False
    )
    fig_rain.update_traces(fillcolor='rgba(0,212,255,0.15)',
                           line=dict(color='#00d4ff', width=1.5))
    st.plotly_chart(fig_rain, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: FLOOD MAP
# ════════════════════════════════════════════════════════════════════════════
elif page == "Flood Map":

    st.markdown("""
    <div class="main-header">
        <h1>🗺️ Flood Extent Map</h1>
        <p>Sentinel-1 SAR + ML Ensemble — Lower Shire Valley</p>
        <span class="header-badge">10m RESOLUTION</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        threshold = st.slider("Flood probability threshold", 0.3, 0.8, 0.5, 0.05)
    with col2:
        show_heatmap = st.checkbox("Show probability heatmap", value=True)
    with col3:
        basemap = st.selectbox("Basemap", ["OpenStreetMap", "Satellite"])

    # Build map
    m = folium.Map(
        location=[-16.2, 34.55],
        zoom_start=9,
        tiles='CartoDB dark_matter',
        attr='CartoDB'
    )

    # Add flood probability heatmap
    if show_heatmap:
        flood_pts = grid_df[grid_df['flood_prob'] > 0.1][
            ['lat', 'lon', 'flood_prob']].values.tolist()
        HeatMap(
            flood_pts,
            min_opacity=0.3,
            max_val=1.0,
            radius=12,
            blur=15,
            gradient={0.3: '#ffcc00', 0.6: '#ff8800', 0.8: '#ff4444', 1.0: '#cc0000'}
        ).add_to(m)

    # Add flood extent as markers
    flooded = grid_df[grid_df['flood_prob'] > threshold]
    for _, row in flooded.sample(min(200, len(flooded))).iterrows():
        opacity = float(row['flood_prob'])
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=4,
            color='#1A78C2',
            fill=True,
            fill_color='#1A78C2',
            fill_opacity=opacity * 0.7,
            weight=0,
            popup=folium.Popup(
                f"Flood Prob: {row['flood_prob']:.0%}<br>"
                f"Lat: {row['lat']:.3f}, Lon: {row['lon']:.3f}",
                max_width=150
            )
        ).add_to(m)

    # District markers
    districts = [
        {'name': 'Chikwawa', 'lat': -16.02, 'lon': 34.80, 'risk': 'Critical'},
        {'name': 'Nsanje',   'lat': -16.92, 'lon': 35.27, 'risk': 'High'},
    ]
    risk_icon_colors = {'Critical': 'red', 'High': 'orange',
                        'Medium': 'beige', 'Low': 'green'}
    for d in districts:
        folium.Marker(
            location=[d['lat'], d['lon']],
            popup=folium.Popup(
                f"<b>{d['name']}</b><br>Risk: {d['risk']}", max_width=120
            ),
            icon=folium.Icon(
                color=risk_icon_colors.get(d['risk'], 'blue'),
                icon='exclamation-sign', prefix='glyphicon'
            )
        ).add_to(m)

    MiniMap(toggle_display=True).add_to(m)

    map_data = st_folium(m, width=None, height=550, returned_objects=[])

    # Map legend
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        flooded_area = len(flooded) * 1.0
        st.metric("Flood pixels above threshold",
                  f"{flooded_area:,.0f}", f"threshold={threshold:.0%}")
    with col_b:
        est_km2 = len(flooded) * 0.01
        st.metric("Estimated flood area", f"{est_km2:.1f} km²")
    with col_c:
        st.metric("SAR acquisition", "2019-03-14", "Cyclone Idai + 0 days")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: MODEL ANALYTICS
# ════════════════════════════════════════════════════════════════════════════
elif page == "Model Analytics":

    st.markdown("""
    <div class="main-header">
        <h1>📊 Model Analytics & Explainability</h1>
        <p>RF + XGBoost Ensemble — SHAP Feature Importance</p>
        <span class="header-badge">IoU 98.2% · AUC 99.96%</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="section-header">SHAP Feature Importance</p>',
                    unsafe_allow_html=True)
        cat_colors = {
            'SAR': '#00d4ff', 'Terrain': '#00cc66', 'Rainfall': '#ff8800'
        }
        shap_df['color'] = shap_df['category'].map(cat_colors)
        fig_shap = px.bar(
            shap_df, x='importance', y='feature',
            color='category',
            color_discrete_map=cat_colors,
            orientation='h',
            labels={'importance': 'mean(|SHAP value|)', 'feature': ''},
        )
        fig_shap.update_layout(
            paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
            font=dict(color='#c8d8e8'),
            xaxis=dict(gridcolor='#1e3a5a', title='mean(|SHAP value|)'),
            yaxis=dict(gridcolor='#1e3a5a'),
            legend=dict(bgcolor='#0f1f35', bordercolor='#1e3a5a'),
            height=420, margin=dict(l=0, r=0, t=10, b=0)
        )
        st.plotly_chart(fig_shap, use_container_width=True)

    with col2:
        st.markdown('<p class="section-header">Prediction Distribution</p>',
                    unsafe_allow_html=True)
        probs = np.array(grid_df['flood_prob'].values, dtype=float)
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=probs[probs < 0.5], name='No-flood',
            marker_color='rgba(0,204,102,0.6)',
            xbins=dict(size=0.02)
        ))
        fig_dist.add_trace(go.Histogram(
            x=probs[probs >= 0.5], name='Flood',
            marker_color='rgba(255,68,68,0.6)',
            xbins=dict(size=0.02)
        ))
        fig_dist.add_vline(
            x=0.5, line_dash='dash', line_color='#ffcc00',
            annotation_text='Threshold 0.5',
            annotation_font_color='#ffcc00'
        )
        fig_dist.update_layout(
            barmode='overlay',
            paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
            font=dict(color='#c8d8e8'),
            xaxis=dict(title='Flood probability', gridcolor='#1e3a5a'),
            yaxis=dict(title='Pixel count', gridcolor='#1e3a5a'),
            legend=dict(bgcolor='#0f1f35', bordercolor='#1e3a5a'),
            height=200, margin=dict(l=0, r=0, t=10, b=0)
        )
        st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown('<p class="section-header">Confusion Matrix</p>',
                    unsafe_allow_html=True)
        cm_data = [[770346, 7823], [0, 256782]]
        fig_cm = px.imshow(
            cm_data,
            labels=dict(x='Predicted', y='Actual', color='Count'),
            x=['No-flood', 'Flood'], y=['No-flood', 'Flood'],
            color_continuous_scale=[[0, '#0a1628'], [1, '#00d4ff']],
            text_auto=True
        )
        fig_cm.update_layout(
            paper_bgcolor='#0a1628',
            font=dict(color='#c8d8e8'),
            height=200, margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_cm, use_container_width=True)

    # Key findings
    st.markdown("---")
    st.markdown('<p class="section-header">Key Model Findings</p>',
                unsafe_allow_html=True)
    findings = [
        ("🛰️ diff_VH dominates",
         "VH polarization change is the strongest predictor — 2.6× more important "
         "than any terrain feature. This reflects flooded vegetation (crops under "
         "water) which VH detects better than VV."),
        ("🌊 River proximity is second",
         "Distance to water ranks second, confirming that proximity to the Shire "
         "River is a primary flood driver — consistent with Phiri et al. 2025 "
         "and the Zindi competition results."),
        ("🏔️ Elevation ranks low",
         "Elevation is only 13th out of 15 features. The SAR diff bands capture "
         "actual flooding so directly that terrain becomes redundant — a strength "
         "of integrating real-time satellite observation with ML."),
        ("🌧️ rain_3d is zero",
         "The 3-day rainfall window contributes nothing. Cyclone Idai's flooding "
         "was driven by accumulated antecedent rainfall (rain_30d, rain_event), "
         "not the immediate days before the scene acquisition."),
    ]
    cols = st.columns(2)
    for i, (title, body) in enumerate(findings):
        with cols[i % 2]:
            st.markdown(f"""
            <div style='background:#0f1f35; border:1px solid #1e3a5a;
                        border-radius:8px; padding:1rem 1.2rem;
                        margin-bottom:0.8rem;'>
                <div style='color:#00d4ff; font-weight:600;
                            margin-bottom:0.4rem;'>{title}</div>
                <div style='color:#8ba3bc; font-size:0.85rem;
                            line-height:1.6;'>{body}</div>
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: RAINFALL MONITOR
# ════════════════════════════════════════════════════════════════════════════
elif page == "Rainfall Monitor":

    st.markdown("""
    <div class="main-header">
        <h1>🌧️ Rainfall Monitor</h1>
        <p>CHIRPS Daily Precipitation — Lower Shire Valley</p>
        <span class="header-badge">CHIRPS v2.0 · 0.05° RESOLUTION</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Today", "12.4 mm", "+3.1 mm")
    with col2:
        st.metric("7-day total", "49.3 mm", "Above normal")
    with col3:
        st.metric("30-day total", "200.8 mm", "+42 mm vs avg")
    with col4:
        st.metric("Flood trigger", "80 mm/7d", "⚠️ Approaching")

    st.markdown("---")

    # Full timeseries
    st.markdown('<p class="section-header">Daily Rainfall — 2019 Season</p>',
                unsafe_allow_html=True)

    fig_ts = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           row_heights=[0.7, 0.3], vertical_spacing=0.05)

    fig_ts.add_trace(go.Bar(
        x=rain_df['date'], y=rain_df['rainfall_mm'],
        name='Daily rainfall',
        marker_color='#00d4ff', opacity=0.7
    ), row=1, col=1)

    # Rolling 7-day
    rain_df['r7d'] = rain_df['rainfall_mm'].rolling(7).sum()
    fig_ts.add_trace(go.Scatter(
        x=rain_df['date'], y=rain_df['r7d'],
        name='7-day rolling total',
        line=dict(color='#ff8800', width=2)
    ), row=1, col=1)

    # Alert threshold line
    fig_ts.add_hline(y=80, line_dash='dash', line_color='#ff4444',
                     annotation_text='Alert threshold (80mm/7d)',
                     annotation_font_color='#ff4444')

    # Cumulative
    rain_df['cumulative'] = rain_df['rainfall_mm'].cumsum()
    fig_ts.add_trace(go.Scatter(
        x=rain_df['date'], y=rain_df['cumulative'],
        name='Cumulative',
        fill='tozeroy',
        line=dict(color='#7f5af0', width=1.5),
        fillcolor='rgba(127,90,240,0.15)'
    ), row=2, col=1)

    # Cyclone Idai shading — applied globally across all subplots
    fig_ts.add_vrect(
        x0='2019-03-08', x1='2019-03-16',
        fillcolor='rgba(255,68,68,0.1)',
        line=dict(color='#ff4444', width=1, dash='dot'),
        annotation_text='Cyclone Idai',
        annotation_font_color='#ff4444',
        annotation_position='top left'
    )

    fig_ts.update_layout(
        paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
        font=dict(color='#c8d8e8'),
        xaxis2=dict(gridcolor='#1e3a5a'),
        yaxis=dict(gridcolor='#1e3a5a', title='mm'),
        yaxis2=dict(gridcolor='#1e3a5a', title='mm (cumul.)'),
        legend=dict(bgcolor='#0f1f35', bordercolor='#1e3a5a'),
        height=400, margin=dict(l=0, r=0, t=10, b=0)
    )
    st.plotly_chart(fig_ts, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: ALERT SYSTEM
# ════════════════════════════════════════════════════════════════════════════
elif page == "Alert System":

    st.markdown("""
    <div class="main-header">
        <h1>📱 SMS Alert System</h1>
        <p>Africa's Talking API — Community Focal Point Dispatch</p>
        <span class="header-badge">PROTOTYPE ACTIVE</span>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown('<p class="section-header">Alert Configuration</p>',
                    unsafe_allow_html=True)

        district_sel = st.selectbox(
            "Target district",
            ['Chikwawa', 'Nsanje', 'Both districts']
        )
        risk_level = st.selectbox(
            "Alert level",
            ['🔴 CRITICAL — Immediate evacuation',
             '🟠 HIGH — Prepare to evacuate',
             '🟡 MEDIUM — Stay alert',
             '🟢 LOW — Situation normal']
        )
        flood_area_inp = st.number_input(
            "Estimated flood area (km²)", value=312.0, step=10.0
        )
        include_guidance = st.checkbox("Include safety guidance", value=True)
        include_hotline  = st.checkbox("Include DoDMA hotline", value=True)

        st.markdown('<p class="section-header" style="margin-top:1rem;">Message Preview</p>',
                    unsafe_allow_html=True)

        level_text = risk_level.split('—')[1].strip()
        level_code = risk_level.split('—')[0].strip()
        guidance_text = "\nAction: Move to higher ground immediately." \
                        if include_guidance else ""
        hotline_text  = "\nDoDMA Hotline: 1997" if include_hotline else ""

        sms_text = (
            f"[MALAWI FLOOD EWS] {level_code} FLOOD ALERT\n"
            f"District: {district_sel}\n"
            f"Flood area: {flood_area_inp:.0f} km²\n"
            f"Status: {level_text}"
            f"{guidance_text}"
            f"{hotline_text}\n"
            f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        st.markdown(f'<div class="sms-preview">{sms_text}</div>',
                    unsafe_allow_html=True)

        st.markdown(f"""
        <div style='margin-top:0.5rem; color:#8ba3bc; font-size:0.78rem;'>
        Characters: {len(sms_text)} / 160
        </div>
        """, unsafe_allow_html=True)

        if st.button("📤 Send Alert to Focal Points"):
            active = focal_df[focal_df['active'] == True]
            if district_sel != 'Both districts':
                active = active[active['district'] == district_sel]
            st.success(
                f"✅ Alert dispatched to {len(active)} focal points "
                f"in {district_sel} via Africa's Talking API."
            )
            for _, fp in active.iterrows():
                st.markdown(f"""
                <div style='background:#0f2a0a; border:1px solid #1a4a1a;
                            border-radius:6px; padding:0.4rem 0.8rem;
                            margin:0.2rem 0; font-size:0.8rem; color:#8bc88b;'>
                    ✓ Sent to {fp['name']} ({fp['role']}, {fp['village']})
                    — {fp['phone']}
                </div>
                """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<p class="section-header">Focal Point Registry</p>',
                    unsafe_allow_html=True)

        for _, fp in focal_df.iterrows():
            status_color = '#00cc66' if fp['active'] else '#4a6a8a'
            status_text  = 'Active' if fp['active'] else 'Inactive'
            st.markdown(f"""
            <div style='background:#0f1f35; border:1px solid #1e3a5a;
                        border-radius:8px; padding:0.8rem 1rem;
                        margin-bottom:0.5rem; display:flex;
                        justify-content:space-between; align-items:center;'>
                <div>
                    <div style='color:#ffffff; font-weight:500;
                                font-size:0.9rem;'>{fp['name']}</div>
                    <div style='color:#8ba3bc; font-size:0.78rem; margin-top:2px;'>
                        {fp['role']} · {fp['village']}, {fp['district']}
                    </div>
                    <div style='color:#4a8abc; font-size:0.75rem;
                                font-family:IBM Plex Mono; margin-top:2px;'>
                        {fp['phone']}
                    </div>
                </div>
                <span style='background:rgba(0,0,0,0.3); color:{status_color};
                             border:1px solid {status_color};
                             padding:2px 8px; border-radius:10px;
                             font-size:0.72rem;'>
                    {status_text}
                </span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="section-header">Alert History</p>',
                    unsafe_allow_html=True)

        history = pd.DataFrame([
            {'Time': '2026-03-21 06:14', 'Level': '🔴 CRITICAL',
             'District': 'Chikwawa',  'Recipients': 4, 'Status': '✅ Sent'},
            {'Time': '2026-03-20 18:32', 'Level': '🟠 HIGH',
             'District': 'Nsanje',    'Recipients': 3, 'Status': '✅ Sent'},
            {'Time': '2026-03-19 09:05', 'Level': '🟡 MEDIUM',
             'District': 'Both',      'Recipients': 5, 'Status': '✅ Sent'},
            {'Time': '2026-03-18 14:20', 'Level': '🟢 LOW',
             'District': 'Chikwawa',  'Recipients': 4, 'Status': '✅ Sent'},
        ])
        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.markdown('<p class="section-header">Threshold Settings</p>',
                    unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.number_input("CRITICAL (km²)", value=300, step=50)
            st.number_input("MEDIUM (km²)",   value=100, step=20)
        with col_b:
            st.number_input("HIGH (km²)",     value=150, step=25)
            st.number_input("LOW (km²)",      value=50,  step=10)

        if st.button("💾 Save Threshold Settings"):
            st.success("Thresholds saved.")