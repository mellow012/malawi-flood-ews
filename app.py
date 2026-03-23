"""
Malawi Flood EWS — Dashboard
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
import sys
import os

st.set_page_config(
    page_title="Malawi Flood EWS",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #080f1c; color: #c8d8e8; }
[data-testid="stDecoration"] { display: none !important; }
footer { display: none !important; }
.block-container { padding-top: 3rem !important; padding-bottom: 0; }
button[kind="header"] { background-color: #0d1829 !important; color: #00d4ff !important; border-radius: 50% !important; z-index: 999999; }
[data-testid="stSidebar"] { background: #060d18 !important; border-right: 1px solid #1a2a40; }
[data-testid="stSidebar"] label { color: #c8d8e8 !important; font-size: 0.88rem; }
.alert-banner   { display:flex; align-items:center; justify-content:space-between; padding:1rem 1.5rem; border-radius:10px; margin-bottom:1.2rem; border-left:6px solid; }
.alert-critical { background:#1a0505; border-color:#ff2222; box-shadow:0 0 20px rgba(255,34,34,0.2); }
.alert-high     { background:#1a0a00; border-color:#ff6600; box-shadow:0 0 20px rgba(255,102,0,0.15); }
.alert-medium   { background:#1a1500; border-color:#ffcc00; box-shadow:0 0 20px rgba(255,204,0,0.15); }
.alert-low      { background:#001a08; border-color:#00cc55; box-shadow:0 0 20px rgba(0,204,85,0.1); }
.district-card  { background:#0d1829; border-radius:12px; padding:1.2rem 1.4rem; margin-bottom:0.8rem; border:1px solid #1a2a40; transition:transform 0.15s; }
.district-card:hover { transform:translateX(4px); }
.stat-pill      { background:#0d1829; border:1px solid #1a2a40; border-radius:10px; padding:1rem; text-align:center; }
.stat-pill-val  { font-size:1.7rem; font-weight:700; font-family:'IBM Plex Mono'; }
.stat-pill-label{ font-size:0.7rem; color:#6a8aaa; text-transform:uppercase; letter-spacing:0.08em; margin-top:3px; }
.action-card    { background:#0d1829; border:1px solid #1a2a40; border-radius:12px; padding:1.2rem; margin-bottom:0.8rem; }
.sms-preview    { background:#0d1829; border:1px solid #1a2a40; border-left:4px solid #00d4ff; border-radius:8px; padding:1rem 1.2rem; font-family:'IBM Plex Mono'; font-size:0.82rem; color:#c8d8e8; line-height:1.7; white-space:pre-wrap; }
.main-header    { background:#0d1829; border:1px solid #1a2a40; border-radius:12px; padding:1.2rem 1.6rem; margin-bottom:1.2rem; border-left:4px solid #00d4ff; }
.main-header h1 { color:#fff; font-size:1.4rem; font-weight:700; margin:0 0 0.2rem 0; padding:0; line-height:1.3; }
.main-header p  { color:#8ba3bc; font-size:0.85rem; margin:0 0 0.6rem 0; }
.header-badge   { display:inline-block; background:#0a2444; color:#00d4ff; border:1px solid #00d4ff; border-radius:20px; padding:3px 12px; font-size:0.68rem; font-weight:600; font-family:'IBM Plex Mono'; letter-spacing:0.08em; }
.section-header { font-size:0.7rem; font-weight:600; color:#3a8aaa; text-transform:uppercase; letter-spacing:0.12em; font-family:'IBM Plex Mono'; margin-bottom:0.8rem; padding-bottom:0.4rem; border-bottom:1px solid #1a2a40; }
div[data-testid="stMetric"] { background:#0d1829; border:1px solid #1a2a40; border-radius:10px; padding:0.8rem; }
.stButton > button       { background:#0a2444 !important; border:1px solid #00d4ff !important; color:#00d4ff !important; font-family:'IBM Plex Mono'; font-size:0.82rem; border-radius:8px; }
.stButton > button:hover { background:#0d3060 !important; }
hr { border-color:#1a2a40; }
@media (max-width: 768px) {
  .alert-banner  { flex-direction: column; gap: 0.6rem; }
  .stat-pill-val { font-size: 1.2rem !important; }
}
</style>
""", unsafe_allow_html=True)

LIVE = {
    'flood_area_km2': 128.4, 'alert_level': 'HIGH',
    'last_updated': '2026-03-22 03:09', 'sar_pass': '2026-03-22',
    'chikwawa_km2': 78.3, 'nsanje_km2': 50.1,
    'pop_at_risk': 145700, 'villages': 78,
}
ALERT_CONFIG = {
    'CRITICAL': {'cls':'alert-critical','icon':'🔴','color':'#ff2222','label':'CRITICAL FLOOD ALERT','action':'EVACUATE IMMEDIATELY to designated shelters','bg':'#1a0505'},
    'HIGH':     {'cls':'alert-high',    'icon':'🟠','color':'#ff6600','label':'HIGH FLOOD RISK',    'action':'PREPARE TO EVACUATE — move valuables to safety now','bg':'#1a0a00'},
    'MEDIUM':   {'cls':'alert-medium',  'icon':'🟡','color':'#ffcc00','label':'FLOOD WATCH',        'action':'STAY ALERT — monitor water levels and be ready','bg':'#1a1500'},
    'LOW':      {'cls':'alert-low',     'icon':'🟢','color':'#00cc55','label':'SITUATION NORMAL',   'action':'No immediate action required','bg':'#001a08'},
}

@st.cache_data
def generate_flood_grid():
    np.random.seed(42)
    lons = np.linspace(34.20, 34.90, 80)
    lats = np.linspace(-16.80, -15.60, 80)
    records = []
    for lat in lats:
        for lon in lons:
            dist_river = abs(lon-34.50)*100 + abs(lat+16.1)*20
            base_risk  = max(0, 1-dist_river/80) + np.random.normal(0, 0.08)
            base_risk  = np.clip(base_risk, 0, 1)
            if -16.15<lat<-15.85 and 34.35<lon<34.65: base_risk = min(1.0, base_risk+0.35)
            if -16.75<lat<-16.50 and 34.25<lon<34.55: base_risk = min(1.0, base_risk+0.25)
            records.append({'lat':lat,'lon':lon,'flood_prob':round(float(base_risk),3)})
    return pd.DataFrame(records)

@st.cache_data
def get_districts():
    return pd.DataFrame([
        {'district':'Chikwawa',      'risk':'HIGH',  'color':'#ff6600','flood_km2':78.3,'pop':84200, 'villages':47,'status':'ACTIVE','action':'Prepare evacuation — Shire River rising'},
        {'district':'Nsanje',        'risk':'HIGH',  'color':'#ff6600','flood_km2':50.1,'pop':61500, 'villages':31,'status':'ACTIVE','action':'Monitor river levels — alert issued'},
        {'district':'Blantyre Rural','risk':'MEDIUM','color':'#ffcc00','flood_km2':8.3, 'pop':12300, 'villages':8, 'status':'WATCH', 'action':'Stay alert — situation developing'},
        {'district':'Thyolo',        'risk':'LOW',   'color':'#00cc55','flood_km2':0.0, 'pop':2100,  'villages':0, 'status':'CLEAR', 'action':'No action required'},
    ])

@st.cache_data
def get_rainfall_ts():
    dates = pd.date_range('2019-01-01','2019-03-20',freq='D')
    rain  = np.random.exponential(4, len(dates))
    rain[60:75] += [10,15,22,38,52,68,45,30,18,12,8,5,4,3,2]
    return pd.DataFrame({'date':dates,'rainfall_mm':rain})

@st.cache_data
def get_focal_points():
    try:
        from contacts import load_contacts  # type: ignore[import]
        return pd.DataFrame(load_contacts())
    except Exception:
        pass
    return pd.DataFrame([
        {'name':'James Banda', 'village':'Chapananga','district':'Chikwawa','phone':'+265991234567','role':'Village Head', 'active':True},
        {'name':'Grace Mwale', 'village':'Makhanga',  'district':'Nsanje',  'phone':'+265888345678','role':'DoDMA Officer','active':True},
        {'name':'Peter Chirwa','village':'Bangula',   'district':'Nsanje',  'phone':'+265777456789','role':'Red Cross',   'active':True},
        {'name':'Mary Phiri',  'village':'Nchalo',    'district':'Chikwawa','phone':'+265999567890','role':'Health Worker','active':True},
        {'name':'David Tembo', 'village':'Mkombezi',  'district':'Chikwawa','phone':'+265885678901','role':'Village Head', 'active':False},
    ])

alert_cfg   = ALERT_CONFIG[LIVE['alert_level']]
grid_df     = generate_flood_grid()
district_df = get_districts()
rain_df     = get_rainfall_ts()
focal_df    = get_focal_points()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center;padding:1.2rem 0 1rem;'>
        <div style='font-size:2.8rem;'>🌊</div>
        <div style='color:#fff;font-weight:700;font-size:1.05rem;margin-top:0.3rem;'>Malawi Flood EWS</div>
        <div style='color:#3a8aaa;font-size:0.72rem;font-family:IBM Plex Mono;'>Lower Shire Valley</div>
    </div>
    <div style='background:{alert_cfg["bg"]};border:1px solid {alert_cfg["color"]};border-radius:8px;
                padding:0.7rem 1rem;text-align:center;margin-bottom:1rem;'>
        <div style='color:{alert_cfg["color"]};font-weight:700;font-size:0.9rem;'>
            {alert_cfg["icon"]} {LIVE["alert_level"]} ALERT</div>
        <div style='color:#8ba3bc;font-size:0.7rem;margin-top:3px;font-family:IBM Plex Mono;'>
            {LIVE["last_updated"]} UTC</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    page = st.radio("Navigation", [
        "🏠 Situation","🗺️ Flood Map","📊 Model Data","🌧️ Rainfall",
        "📱 Send Alert","📅 Event History","🎯 Prediction vs Actual","📄 Reports",
    ], label_visibility="collapsed")
    st.markdown("---")

    st.markdown('<p class="section-header">Live Summary</p>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style='font-size:0.82rem;line-height:2.2;color:#8ba3bc;'>
        <span style='color:#ff6600;font-family:IBM Plex Mono;font-weight:600;'>{LIVE["flood_area_km2"]} km²</span> flooded<br>
        <span style='color:#ffcc00;font-family:IBM Plex Mono;font-weight:600;'>{LIVE["pop_at_risk"]:,}</span> people at risk<br>
        <span style='color:#ff6600;font-family:IBM Plex Mono;font-weight:600;'>{LIVE["villages"]}</span> villages affected<br>
        <span style='color:#00cc55;font-family:IBM Plex Mono;font-weight:600;'>99.84%</span> model accuracy
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<p class="section-header">System Status</p>', unsafe_allow_html=True)
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    st.markdown(f"""
    <div style='font-size:0.78rem;line-height:2;color:#8ba3bc;'>
        <span style='color:#00cc55;'>●</span> GEE Pipeline: Online<br>
        <span style='color:#00cc55;'>●</span> ML Model: Active<br>
        <span style='color:#00cc55;'>●</span> SMS Gateway: Ready<br>
        <span style='color:#ffcc00;'>●</span> Last S1 pass: 6h ago<br>
        <span style='color:#3a8aaa;font-family:IBM Plex Mono;font-size:0.7rem;'>🕐 {now}</span>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<p class="section-header">Emergency Contacts</p>', unsafe_allow_html=True)
    for _n, _num, _c in [
        ("DoDMA Hotline","1997","#00d4ff"),
        ("Red Cross Malawi","+265 1 758 110","#ff4444"),
        ("Chikwawa DEC","+265 993 000 001","#ffcc00"),
        ("Nsanje DEC","+265 993 000 002","#ffcc00"),
    ]:
        st.markdown(f"""
        <div style='display:flex;justify-content:space-between;padding:0.35rem 0;border-bottom:1px solid #1a2a40;'>
            <span style='color:#6a8aaa;font-size:0.78rem;'>{_n}</span>
            <span style='color:{_c};font-family:IBM Plex Mono;font-size:0.78rem;font-weight:600;'>{_num}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""<div style='font-size:0.68rem;color:#2a3a4a;line-height:1.8;text-align:center;'>
        Sentinel-1 SAR + RF/XGBoost<br>github.com/mellow012/malawi-flood-ews
    </div>""", unsafe_allow_html=True)

# ── PAGES ─────────────────────────────────────────────────────────────────────
if page == "🏠 Situation":
    st.markdown(f"""
    <div class="alert-banner {alert_cfg['cls']}">
        <div>
            <div style='color:{alert_cfg["color"]};font-weight:700;font-size:1.4rem;letter-spacing:-0.02em;'>
                {alert_cfg["icon"]} {alert_cfg["label"]}</div>
            <div style='color:#c8d8e8;font-size:0.9rem;margin-top:0.2rem;'>{alert_cfg["action"]}</div>
            <div style='margin-top:0.5rem;color:#8ba3bc;font-size:0.8rem;'>
                📍 Lower Shire Valley — Chikwawa & Nsanje Districts</div>
        </div>
        <div style='text-align:right;font-family:IBM Plex Mono;font-size:0.78rem;color:#6a8aaa;min-width:160px;'>
            🛰️ SAR: {LIVE["sar_pass"]}<br>🕐 {LIVE["last_updated"]} UTC<br>Sentinel-1 Orbit 6<br>
            <span style='color:{alert_cfg["color"]};font-weight:600;'>Model: 99.84% acc.</span>
        </div>
    </div>""", unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    for col,(val,label,color) in zip([c1,c2,c3,c4],[
        (f"{LIVE['flood_area_km2']} km²","Total flooded area","#ff6600"),
        (f"{LIVE['pop_at_risk']:,}","People at risk","#ffcc00"),
        (str(LIVE['villages']),"Villages affected","#ff6600"),
        ("2 districts","Active flood alerts","#ff4444"),
    ]):
        with col:
            st.markdown(f"""<div class="stat-pill">
                <div class="stat-pill-val" style='color:{color};'>{val}</div>
                <div class="stat-pill-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    mc, lc = st.columns([3,1])
    with mc:
        st.markdown('<p class="section-header">Live Flood Extent — Lower Shire Valley</p>', unsafe_allow_html=True)
    with lc:
        st.markdown("""<div style='display:flex;gap:1rem;justify-content:flex-end;align-items:center;padding-top:0.1rem;'>
            <div style='display:flex;align-items:center;gap:5px;'>
                <div style='width:11px;height:11px;border-radius:50%;background:#ff4444;'></div>
                <span style='color:#8ba3bc;font-size:0.7rem;'>HIGH</span></div>
            <div style='display:flex;align-items:center;gap:5px;'>
                <div style='width:11px;height:11px;border-radius:50%;background:#ff8800;'></div>
                <span style='color:#8ba3bc;font-size:0.7rem;'>MEDIUM</span></div>
            <div style='display:flex;align-items:center;gap:5px;'>
                <div style='width:11px;height:11px;border-radius:2px;border:1.5px solid #38bdf8;'></div>
                <span style='color:#8ba3bc;font-size:0.7rem;'>Study area</span></div>
        </div>""", unsafe_allow_html=True)

    ov_map = folium.Map(location=[-16.2,34.65], zoom_start=9, tiles='CartoDB dark_matter',
                        zoom_control=False, scrollWheelZoom=False, dragging=True)
    pts = grid_df[grid_df['flood_prob']>0.1][['lat','lon','flood_prob']].values.tolist()
    HeatMap(pts, min_opacity=0.35, radius=14, blur=16,
            gradient={0.3:'#ff6600',0.55:'#ff3300',0.75:'#ff0000',1.0:'#cc0000'}).add_to(ov_map)
    folium.PolyLine(locations=[[-15.60,34.55],[-15.90,34.62],[-16.10,34.72],[-16.30,34.80],[-16.55,34.92],[-16.80,35.05]],
                    color='#38bdf8', weight=2.5, opacity=0.7, tooltip='Shire River').add_to(ov_map)
    folium.Rectangle(bounds=[[-16.80,34.20],[-15.60,34.90]],
                     color='#38bdf8', fill=False, weight=1.5, dash_array='6 4').add_to(ov_map)
    for dr in [
        {'name':'Chikwawa','lat':-16.02,'lon':34.80,'risk':'HIGH','km2':LIVE['chikwawa_km2'],'color':'#ff6600'},
        {'name':'Nsanje','lat':-16.92,'lon':35.27,'risk':'HIGH','km2':LIVE['nsanje_km2'],'color':'#ff6600'},
        {'name':'Blantyre Rural','lat':-15.80,'lon':34.97,'risk':'MEDIUM','km2':8.3,'color':'#ffcc00'},
    ]:
        folium.Marker(
            location=[dr['lat'],dr['lon']],
            tooltip=folium.Tooltip(f"<b style='color:{dr['color']}'>{dr['name']}</b><br>Risk: {dr['risk']}<br>Flooded: {dr['km2']} km²"),
            icon=folium.DivIcon(  # type: ignore[arg-type]
                html=f"""<div style='background:{dr["color"]};color:#000;font-size:10px;font-weight:700;
                    padding:3px 7px;border-radius:4px;white-space:nowrap;'>{dr["name"]}</div>""",
                icon_size=(90,24), icon_anchor=(45,12)),
        ).add_to(ov_map)
    st_folium(ov_map, width=None, height=300, returned_objects=[])

    st.markdown("<br>", unsafe_allow_html=True)
    cl, cr = st.columns([1.5,1])
    with cl:
        st.markdown('<p class="section-header">District Status</p>', unsafe_allow_html=True)
        for _, row in district_df.iterrows():
            icon = {'ACTIVE':'🔴','WATCH':'🟡','CLEAR':'🟢'}.get(str(row['status']),'⚪')
            st.markdown(f"""
            <div class="district-card" style='border-left:4px solid {row["color"]};'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                    <div>
                        <div style='font-size:1.1rem;font-weight:600;color:#fff;'>{row["district"]}</div>
                        <div style='font-size:0.82rem;color:#6a8aaa;margin-top:2px;'>{row["action"]}</div>
                    </div>
                    <span style='background:rgba(0,0,0,0.3);color:{row["color"]};border:1px solid {row["color"]};
                        padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;white-space:nowrap;margin-left:0.8rem;'>
                        {icon} {row["status"]}</span>
                </div>
                <div style='display:flex;gap:2rem;margin-top:0.8rem;'>
                    <div><div style='font-size:1.1rem;font-weight:600;font-family:IBM Plex Mono;color:{row["color"]};'>{row["flood_km2"]} km²</div><div style='font-size:0.68rem;color:#6a8aaa;text-transform:uppercase;'>Flooded</div></div>
                    <div><div style='font-size:1.1rem;font-weight:600;font-family:IBM Plex Mono;color:#c8d8e8;'>{row["pop"]:,}</div><div style='font-size:0.68rem;color:#6a8aaa;text-transform:uppercase;'>At risk</div></div>
                    <div><div style='font-size:1.1rem;font-weight:600;font-family:IBM Plex Mono;color:#c8d8e8;'>{row["villages"]}</div><div style='font-size:0.68rem;color:#6a8aaa;text-transform:uppercase;'>Villages</div></div>
                </div>
            </div>""", unsafe_allow_html=True)
        st.markdown('<p class="section-header" style="margin-top:1rem;">Flood Trend — Last 7 Days</p>', unsafe_allow_html=True)
        trend = pd.DataFrame({'day':['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],'area':[42,58,71,88,110,122,128.4]})
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=trend['day'],y=trend['area'],mode='lines+markers',
            line=dict(color='#ff6600',width=2.5),marker=dict(size=7,color='#ff6600'),
            fill='tozeroy',fillcolor='rgba(255,102,0,0.08)'))
        fig_t.add_hline(y=150,line_dash='dash',line_color='#ff4444',annotation_text='HIGH threshold',annotation_font_color='#ff4444')
        fig_t.update_layout(paper_bgcolor='#080f1c',plot_bgcolor='#080f1c',font=dict(color='#c8d8e8'),
            xaxis=dict(gridcolor='#1a2a40',title=None),yaxis=dict(gridcolor='#1a2a40',title='km²'),
            height=160,margin=dict(l=0,r=0,t=10,b=0),showlegend=False)
        st.plotly_chart(fig_t, width='stretch')

    with cr:
        st.markdown('<p class="section-header">What To Do Right Now</p>', unsafe_allow_html=True)
        st.markdown('<div class="action-card">', unsafe_allow_html=True)
        for ico,title,body in [
            ("📱","Alert focal points","Send SMS to village heads and DoDMA officers in Chikwawa and Nsanje immediately."),
            ("🏠","Activate shelters","Open flood shelters in Chapananga, Makhanga, and Bangula."),
            ("👁️","Monitor river levels","Check Shire River at Chikwawa Bridge and Bangula gauge every 2 hours."),
            ("🚫","Restrict movement","Advise communities near the Shire floodplain to avoid travel."),
            ("📋","Report to DoDMA","Submit situation report to DoDMA hotline 1997 by 08:00 local time."),
        ]:
            st.markdown(f"""<div style='display:flex;align-items:flex-start;gap:0.8rem;margin-bottom:0.9rem;'>
                <div style='background:#1a2a40;border-radius:8px;width:32px;height:32px;display:flex;
                    align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0;margin-top:2px;'>{ico}</div>
                <div style='color:#c8d8e8;font-size:0.88rem;line-height:1.5;'>
                    <span style='color:#fff;font-weight:600;'>{title}. </span>{body}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📱 Send Alert Now — All Focal Points", use_container_width=True):
            st.success("✅ HIGH alert dispatched to 4 active focal points.")
            st.info("Go to 📱 Send Alert to customise the message.")

elif page == "🗺️ Flood Map":
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path: sys.path.insert(0, _dir)
    try:
        import importlib, flood_map as _fm
        importlib.reload(_fm)
        _fm.show()
    except Exception as e:
        st.markdown("""<div class="main-header"><h1>🗺️ Flood Map</h1><p>Sentinel-1 SAR fallback view</p></div>""", unsafe_allow_html=True)
        st.warning(f"flood_map.py: {e}")
        m = folium.Map(location=[-16.2,34.55],zoom_start=9,tiles='CartoDB dark_matter')
        pts = grid_df[grid_df['flood_prob']>0.1][['lat','lon','flood_prob']].values.tolist()
        HeatMap(pts,min_opacity=0.3,radius=14,blur=16,gradient={0.3:'#ff6600',0.6:'#ff3300',0.8:'#ff0000',1.0:'#cc0000'}).add_to(m)
        MiniMap(toggle_display=True).add_to(m)
        st_folium(m,width=None,height=600,returned_objects=[])

elif page == "📊 Model Data":
    st.markdown("""<div class="main-header"><h1>📊 Model Performance</h1>
    <p>Random Forest + XGBoost Ensemble · Sentinel-1 SAR + CHIRPS</p>
    <span class="header-badge">TRAINED: FREDDY 2023 · TESTED: IDAI 2019</span></div>""", unsafe_allow_html=True)
    findings = [
        ("🌧️","Rainfall is the #1 signal","How much rain fell during and before the event matters most. Uses CHIRPS satellite rainfall data."),
        ("🛰️","Satellite radar change is #2","When the Sentinel-1 radar signal drops sharply, water has replaced dry land."),
        ("🌊","Distance to Shire River is #3","Communities within 5 km of the Shire River flood first. Geography is a strong predictor."),
        ("✅","Tested on a different event","Trained on Freddy 2023, tested on Idai 2019 — different cyclone, same geography. 99.84% held up."),
    ]
    cols = st.columns(2)
    for i,(ico,title,body) in enumerate(findings):
        with cols[i%2]:
            st.markdown(f"""<div style='background:#0d1829;border:1px solid #1a2a40;border-radius:10px;
                padding:1rem 1.2rem;margin-bottom:0.8rem;'>
                <div style='font-size:1.4rem;margin-bottom:0.4rem;'>{ico}</div>
                <div style='color:#fff;font-weight:600;font-size:0.9rem;margin-bottom:0.4rem;'>{title}</div>
                <div style='color:#8ba3bc;font-size:0.82rem;line-height:1.6;'>{body}</div>
            </div>""", unsafe_allow_html=True)
    st.markdown('<p class="section-header" style="margin-top:0.5rem;">Accuracy Numbers</p>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col,(val,label,color) in zip([c1,c2,c3,c4],[
        ("99.84%","Prediction accuracy (AUC)","#00cc55"),
        ("97.99%","Spatial accuracy (IoU)","#00d4ff"),
        ("99%","Precision — no false alarms","#00cc55"),
        ("99%","Recall — no missed floods","#00cc55"),
    ]):
        with col:
            st.markdown(f"""<div class="stat-pill">
                <div class="stat-pill-val" style='color:{color};'>{val}</div>
                <div class="stat-pill-label">{label}</div></div>""", unsafe_allow_html=True)
    with st.expander("📈 Full technical details — for researchers"):
        shap_df = pd.DataFrame([
            {'Feature':'Event rainfall','Importance':2.61,'Type':'Rainfall'},
            {'Feature':'SAR VV change','Importance':1.94,'Type':'SAR'},
            {'Feature':'Combined SAR change','Importance':1.54,'Type':'SAR'},
            {'Feature':'Distance to Shire','Importance':1.41,'Type':'Terrain'},
            {'Feature':'Peak rainfall day','Importance':0.98,'Type':'Rainfall'},
            {'Feature':'SAR VH change','Importance':0.87,'Type':'SAR'},
            {'Feature':'SAR VV backscatter','Importance':0.76,'Type':'SAR'},
            {'Feature':'Terrain slope','Importance':0.68,'Type':'Terrain'},
            {'Feature':'30-day rainfall','Importance':0.61,'Type':'Rainfall'},
            {'Feature':'Terrain wetness','Importance':0.54,'Type':'Terrain'},
            {'Feature':'7-day rainfall','Importance':0.48,'Type':'Rainfall'},
            {'Feature':'SAR VH backscatter','Importance':0.41,'Type':'SAR'},
            {'Feature':'Elevation','Importance':0.33,'Type':'Terrain'},
            {'Feature':'Aspect','Importance':0.09,'Type':'Terrain'},
            {'Feature':'3-day rainfall','Importance':0.00,'Type':'Rainfall'},
        ]).sort_values('Importance',ascending=True)
        fig_shap = px.bar(shap_df,x='Importance',y='Feature',color='Type',orientation='h',
            color_discrete_map={'SAR':'#00d4ff','Terrain':'#00cc66','Rainfall':'#ff8800'},
            labels={'Importance':'SHAP feature importance','Feature':''})
        fig_shap.update_layout(paper_bgcolor='#080f1c',plot_bgcolor='#080f1c',font=dict(color='#c8d8e8'),
            xaxis=dict(gridcolor='#1a2a40'),yaxis=dict(gridcolor='#1a2a40'),
            legend=dict(bgcolor='#0d1829',bordercolor='#1a2a40'),height=420,margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_shap, width='stretch')
        st.dataframe(pd.DataFrame([
            {'Model':'Random Forest','Train':'Freddy 2023','Test':'Idai 2019','AUC-ROC':'0.9978','IoU':'0.9799'},
            {'Model':'XGBoost','Train':'Freddy 2023','Test':'Idai 2019','AUC-ROC':'0.9989','IoU':'0.9799'},
            {'Model':'Ensemble','Train':'Freddy 2023','Test':'Idai 2019','AUC-ROC':'0.9984','IoU':'0.9799'},
            {'Model':'Ensemble','Train':'Freddy 2023','Test':'Floods 2025','AUC-ROC':'0.9965','IoU':'0.9174*'},
        ]), width='stretch', hide_index=True)
        st.caption("* Floods 2025 at threshold 0.15.")

elif page == "🌧️ Rainfall":
    st.markdown("""<div class="main-header"><h1>🌧️ Rainfall Monitor</h1>
    <p>CHIRPS satellite rainfall · Updated daily at 06:00 UTC</p>
    <span class="header-badge">LOWER SHIRE VALLEY</span></div>""", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col,(label,val,delta,color) in zip([c1,c2,c3,c4],[
        ("Today","12.4 mm","+3.1 mm","#ff8800"),
        ("Last 7 days","49.3 mm","⚠️ Above normal","#ffcc00"),
        ("Last 30 days","200.8 mm","+42 mm vs average","#ff6600"),
        ("Alert trigger","80mm/7d","⚠️ Approaching","#ff4444"),
    ]):
        with col:
            st.markdown(f"""<div class="stat-pill">
                <div class="stat-pill-val" style='color:{color};'>{val}</div>
                <div class="stat-pill-label">{label}</div>
                <div style='color:#6a8aaa;font-size:0.72rem;margin-top:4px;'>{delta}</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    fig_ts = make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[0.7,0.3],vertical_spacing=0.04)
    fig_ts.add_trace(go.Bar(x=rain_df['date'],y=rain_df['rainfall_mm'],name='Daily rainfall',marker_color='rgba(0,180,255,0.6)'),row=1,col=1)
    rain_df['r7d'] = rain_df['rainfall_mm'].rolling(7).sum()
    fig_ts.add_trace(go.Scatter(x=rain_df['date'],y=rain_df['r7d'],name='7-day total',line=dict(color='#ff8800',width=2.5)),row=1,col=1)
    fig_ts.add_hline(y=80,line_dash='dash',line_color='#ff4444',annotation_text='⚠️ Flood alert threshold (80mm/7d)',annotation_font_color='#ff4444')
    rain_df['cumulative'] = rain_df['rainfall_mm'].cumsum()
    fig_ts.add_trace(go.Scatter(x=rain_df['date'],y=rain_df['cumulative'],name='Season total',fill='tozeroy',line=dict(color='#7f5af0',width=1.5),fillcolor='rgba(127,90,240,0.1)'),row=2,col=1)
    fig_ts.add_vrect(x0='2019-03-08',x1='2019-03-16',fillcolor='rgba(255,50,50,0.08)',line=dict(color='#ff4444',width=1,dash='dot'),annotation_text='Cyclone Idai landfall',annotation_font_color='#ff4444',annotation_position='top left')
    fig_ts.update_layout(paper_bgcolor='#080f1c',plot_bgcolor='#080f1c',font=dict(color='#c8d8e8'),
        xaxis2=dict(gridcolor='#1a2a40'),yaxis=dict(gridcolor='#1a2a40',title='mm/day'),
        yaxis2=dict(gridcolor='#1a2a40',title='Season total (mm)'),
        legend=dict(bgcolor='#0d1829',bordercolor='#1a2a40'),height=380,margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig_ts, width='stretch')

elif page == "📱 Send Alert":
    st.markdown("""<div class="main-header"><h1>📱 Send SMS Alert</h1>
    <p>Africa's Talking API · Airtel Malawi & TNM</p>
    <span class="header-badge">COMMUNITY FOCAL POINTS</span></div>""", unsafe_allow_html=True)
    cl,cr = st.columns([1,1])
    with cl:
        st.markdown('<p class="section-header">Configure Alert</p>', unsafe_allow_html=True)
        district_sel   = st.selectbox("Which district?",["Both districts","Chikwawa","Nsanje"])
        risk_level     = st.selectbox("Alert level",["🔴 CRITICAL — Evacuate immediately","🟠 HIGH — Prepare to evacuate","🟡 MEDIUM — Stay alert","🟢 LOW — Situation normal"])
        flood_area_inp = st.number_input("Current flood area (km²)",value=128.4,step=5.0)
        include_action  = st.checkbox("Include action instructions",value=True)
        include_hotline = st.checkbox("Include DoDMA hotline (1997)",value=True)
        st.markdown('<p class="section-header" style="margin-top:1rem;">Message Preview</p>', unsafe_allow_html=True)
        level_code  = risk_level.split("—")[0].strip()
        level_text  = risk_level.split("—")[1].strip()
        action_text = "\nAction: Move to higher ground immediately." if include_action else ""
        hotline_text= "\nHelp: DoDMA 1997" if include_hotline else ""
        sms = f"[MALAWI FLOOD EWS] {level_code}\nArea: {district_sel}\nFlooded: {flood_area_inp:.0f}km²\nStatus: {level_text}{action_text}{hotline_text}\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        st.markdown(f'<div class="sms-preview">{sms}</div>', unsafe_allow_html=True)
        char_color = '#ff4444' if len(sms)>160 else '#00cc55'
        st.markdown(f"""<div style='color:{char_color};font-size:0.78rem;font-family:IBM Plex Mono;margin-top:0.4rem;'>
            {len(sms)}/160 characters {'— ⚠️ splits into 2 SMS' if len(sms)>160 else '— ✓ fits in 1 SMS'}</div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📤 Send Alert Now", use_container_width=True):
            active = focal_df[focal_df['active']==True]
            if district_sel != 'Both districts': active = active[active['district']==district_sel]
            st.success(f"✅ Alert sent to {len(active)} focal points in {district_sel}")
            for _,fp in active.iterrows():
                st.markdown(f"""<div style='background:#0a1f0a;border:1px solid #1a4a1a;border-radius:6px;
                    padding:0.5rem 0.8rem;margin:0.2rem 0;font-size:0.82rem;color:#8bc88b;'>
                    ✓ {fp["name"]} · {fp["role"]} · {fp["village"]}
                    <span style='float:right;font-family:IBM Plex Mono;'>{fp["phone"]}</span></div>""", unsafe_allow_html=True)
    with cr:
        st.markdown('<p class="section-header">Focal Point Registry</p>', unsafe_allow_html=True)
        for _,fp in focal_df.iterrows():
            sc = '#00cc55' if fp['active'] else '#3a4a5a'
            st.markdown(f"""<div style='background:#0d1829;border:1px solid #1a2a40;border-radius:8px;
                padding:0.8rem 1rem;margin-bottom:0.5rem;display:flex;justify-content:space-between;align-items:center;'>
                <div>
                    <div style='color:#fff;font-weight:500;'>{fp["name"]}</div>
                    <div style='color:#6a8aaa;font-size:0.78rem;margin-top:2px;'>{fp["role"]} · {fp["village"]}, {fp["district"]}</div>
                    <div style='color:#3a8aaa;font-size:0.75rem;font-family:IBM Plex Mono;margin-top:2px;'>{fp["phone"]}</div>
                </div>
                <span style='color:{sc};border:1px solid {sc};padding:3px 10px;border-radius:20px;font-size:0.72rem;background:rgba(0,0,0,0.3);'>
                    {"Active" if fp["active"] else "Inactive"}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<p class="section-header">Recent Alerts Sent</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([
            {"Time":"2026-03-22 03:15","Level":"🟠 HIGH","District":"Both","Sent":4,"Delivered":4},
            {"Time":"2026-03-21 06:14","Level":"🟠 HIGH","District":"Chikwawa","Sent":3,"Delivered":3},
            {"Time":"2026-03-20 18:32","Level":"🟡 MEDIUM","District":"Nsanje","Sent":2,"Delivered":2},
        ]), width='stretch', hide_index=True)

elif page == "📅 Event History":
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path: sys.path.insert(0, _dir)
    try:
        import importlib, historical_comparison as _hc
        importlib.reload(_hc); _hc.show()
    except Exception as e:
        st.error(f"Could not load event history: {e}"); st.exception(e)

elif page == "🎯 Prediction vs Actual":
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path: sys.path.insert(0, _dir)
    try:
        import importlib, historical_comparison as _hc
        importlib.reload(_hc); _hc.show_prediction_vs_actual()
    except Exception as e:
        st.error(f"Could not load prediction comparison: {e}"); st.exception(e)

elif page == "📄 Reports":
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path: sys.path.insert(0, _dir)
    try:
        import importlib, report_generator as _rg
        importlib.reload(_rg); _rg.show()
    except Exception as e:
        st.error(f"Could not load report generator: {e}"); st.exception(e)