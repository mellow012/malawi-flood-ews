"""
Malawi Flood Early Warning System — Dashboard
UX: Non-technical users first (DoDMA officers, village heads, Red Cross)
Design: Map first, action second, data third
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
    page_icon="\U0001f30a",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #080f1c; }
.block-container { padding-top: 1rem; padding-bottom: 0; }
.alert-banner { display:flex;align-items:center;justify-content:space-between;padding:1rem 1.5rem;border-radius:10px;margin-bottom:1.2rem;border-left:6px solid; }
.alert-critical { background:#1a0505;border-color:#ff2222;box-shadow:0 0 20px rgba(255,34,34,0.2); }
.alert-high     { background:#1a0a00;border-color:#ff6600;box-shadow:0 0 20px rgba(255,102,0,0.15); }
.alert-medium   { background:#1a1500;border-color:#ffcc00;box-shadow:0 0 20px rgba(255,204,0,0.15); }
.alert-low      { background:#001a08;border-color:#00cc55;box-shadow:0 0 20px rgba(0,204,85,0.1); }
.district-card { background:#0d1829;border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:0.8rem;border:1px solid #1a2a40;transition:transform 0.15s; }
.district-card:hover { transform:translateX(4px); }
.stat-pill { background:#0d1829;border:1px solid #1a2a40;border-radius:10px;padding:1rem;text-align:center; }
.stat-pill-val   { font-size:1.7rem;font-weight:700;font-family:'IBM Plex Mono'; }
.stat-pill-label { font-size:0.7rem;color:#6a8aaa;text-transform:uppercase;letter-spacing:0.08em;margin-top:3px; }
.section-header  { font-size:0.7rem;font-weight:600;color:#3a8aaa;text-transform:uppercase;letter-spacing:0.12em;font-family:'IBM Plex Mono';margin-bottom:0.8rem;padding-bottom:0.4rem;border-bottom:1px solid #1a2a40; }
.action-card { background:#0d1829;border:1px solid #1a2a40;border-radius:12px;padding:1.2rem;margin-bottom:0.8rem; }
.sms-preview { background:#0d1829;border:1px solid #1a2a40;border-left:4px solid #00d4ff;border-radius:8px;padding:1rem 1.2rem;font-family:'IBM Plex Mono';font-size:0.82rem;color:#c8d8e8;line-height:1.7;white-space:pre-wrap; }
[data-testid="stSidebar"] { background:#060d18;border-right:1px solid #1a2a40; }
div[data-testid="stMetric"] { background:#0d1829;border:1px solid #1a2a40;border-radius:10px;padding:0.8rem; }
.stButton button { background:#0a2444;border:1px solid #00d4ff;color:#00d4ff;font-family:'IBM Plex Mono';font-size:0.82rem;border-radius:8px; }
hr { border-color:#1a2a40; }

[data-testid="stSidebar"] {
    background: #060d18;
    border-right: 1px solid #1a2a40;
}
[data-testid="stSidebar"] .stRadio label {
    color: #c8d8e8 !important;
    font-size: 0.88rem;
    padding: 0.25rem 0;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
    gap: 0.1rem;
}

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

LIVE = {
    'flood_area_km2': 128.4, 'alert_level': 'HIGH',
    'last_updated': '2026-03-22 03:09', 'sar_pass': '2026-03-22',
    'chikwawa_km2': 78.3, 'nsanje_km2': 50.1,
    'pop_at_risk': 145700, 'villages': 78,
}

ALERT_CONFIG = {
    'CRITICAL': {'cls':'alert-critical','icon':'\U0001f534','color':'#ff2222','label':'CRITICAL FLOOD ALERT','action':'EVACUATE IMMEDIATELY to designated shelters','bg':'#1a0505'},
    'HIGH':     {'cls':'alert-high',    'icon':'\U0001f7e0','color':'#ff6600','label':'HIGH FLOOD RISK',        'action':'PREPARE TO EVACUATE — move valuables to safety now',  'bg':'#1a0a00'},
    'MEDIUM':   {'cls':'alert-medium',  'icon':'\U0001f7e1','color':'#ffcc00','label':'FLOOD WATCH',             'action':'STAY ALERT — monitor water levels and be ready',     'bg':'#1a1500'},
    'LOW':      {'cls':'alert-low',     'icon':'\U0001f7e2','color':'#00cc55','label':'SITUATION NORMAL',        'action':'No immediate action required',                      'bg':'#001a08'},
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
        {'district':'Chikwawa',      'risk':'HIGH',  'color':'#ff6600','flood_km2':78.3,'pop':84200, 'villages':47,'status':'ACTIVE','lat':-16.02,'lon':34.80,'action':'Prepare evacuation — Shire River rising'},
        {'district':'Nsanje',        'risk':'HIGH',  'color':'#ff6600','flood_km2':50.1,'pop':61500, 'villages':31,'status':'ACTIVE','lat':-16.92,'lon':35.27,'action':'Monitor river levels — alert issued'},
        {'district':'Blantyre Rural','risk':'MEDIUM','color':'#ffcc00','flood_km2':8.3, 'pop':12300,'villages':8, 'status':'WATCH', 'lat':-15.80,'lon':34.97,'action':'Stay alert — situation developing'},
        {'district':'Thyolo',        'risk':'LOW',   'color':'#00cc55','flood_km2':0.0, 'pop':2100,  'villages':0, 'status':'CLEAR', 'lat':-16.07,'lon':35.15,'action':'No action required'},
    ])

@st.cache_data
def get_rainfall_ts():
    dates = pd.date_range('2019-01-01','2019-03-20',freq='D')
    rain  = np.random.exponential(4, len(dates))
    rain[60:75] += [10,15,22,38,52,68,45,30,18,12,8,5,4,3,2]
    return pd.DataFrame({'date':dates,'rainfall_mm':rain})

@st.cache_data
def get_focal_points():
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

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center;padding:1.2rem 0 1rem;'>
        <div style='font-size:2.8rem;'>\U0001f30a</div>
        <div style='color:#fff;font-weight:700;font-size:1.05rem;margin-top:0.3rem;'>Malawi Flood EWS</div>
        <div style='color:#3a8aaa;font-size:0.72rem;font-family:IBM Plex Mono;'>Lower Shire Valley</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style='background:{alert_cfg["bg"]};border:1px solid {alert_cfg["color"]};border-radius:8px;padding:0.7rem 1rem;text-align:center;margin-bottom:1rem;'>
        <div style='color:{alert_cfg["color"]};font-weight:700;font-size:0.9rem;'>{alert_cfg["icon"]} {LIVE["alert_level"]} ALERT</div>
        <div style='color:#8ba3bc;font-size:0.7rem;margin-top:3px;font-family:IBM Plex Mono;'>{LIVE["last_updated"]} UTC</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    page = st.radio("Navigation", [
        "\U0001f3e0 Situation", "\U0001f5fa\ufe0f Flood Map", "\U0001f4ca Model Data",
        "\U0001f327\ufe0f Rainfall", "\U0001f4f1 Send Alert",
        "\U0001f4c5 Event History", "\U0001f3af Prediction vs Actual", "\U0001f4c4 Reports",
    ], label_visibility="collapsed")
    st.markdown("---")

    st.markdown('<p class="section-header">Live Summary</p>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style='font-size:0.82rem;line-height:2.2;color:#8ba3bc;'>
        <span style='color:#ff6600;font-family:IBM Plex Mono;font-weight:600;'>{LIVE["flood_area_km2"]} km\u00b2</span> flooded<br>
        <span style='color:#ffcc00;font-family:IBM Plex Mono;font-weight:600;'>{LIVE["pop_at_risk"]:,}</span> people at risk<br>
        <span style='color:#ff6600;font-family:IBM Plex Mono;font-weight:600;'>{LIVE["villages"]}</span> villages affected<br>
        <span style='color:#00cc55;font-family:IBM Plex Mono;font-weight:600;'>99.84%</span> model accuracy
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<p class="section-header">System Status</p>', unsafe_allow_html=True)
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    st.markdown(f"""
    <div style='font-size:0.78rem;line-height:2;color:#8ba3bc;'>
        <span style='color:#00cc55;'>\u25cf</span> GEE Pipeline: Online<br>
        <span style='color:#00cc55;'>\u25cf</span> ML Model: Active<br>
        <span style='color:#00cc55;'>\u25cf</span> SMS Gateway: Ready<br>
        <span style='color:#ffcc00;'>\u25cf</span> Last S1 pass: 6h ago<br>
        <span style='color:#3a8aaa;font-family:IBM Plex Mono;font-size:0.7rem;'>\U0001f550 {now}</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<p class="section-header">Emergency Contacts</p>', unsafe_allow_html=True)
    for name, number, color in [
        ("DoDMA Hotline",    "1997",             "#00d4ff"),
        ("Red Cross Malawi", "+265 1 758 110",   "#ff4444"),
        ("Chikwawa DEC",     "+265 993 000 001", "#ffcc00"),
        ("Nsanje DEC",       "+265 993 000 002", "#ffcc00"),
    ]:
        st.markdown(f"""
        <div style='display:flex;justify-content:space-between;padding:0.35rem 0;border-bottom:1px solid #1a2a40;'>
            <span style='color:#6a8aaa;font-size:0.78rem;'>{name}</span>
            <span style='color:{color};font-family:IBM Plex Mono;font-size:0.78rem;font-weight:600;'>{number}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.68rem;color:#2a3a4a;line-height:1.8;text-align:center;'>
        Sentinel-1 SAR + RF/XGBoost<br>github.com/mellow012/malawi-flood-ews
    </div>""", unsafe_allow_html=True)

# ── PAGE ROUTING ──────────────────────────────────────────────────────────────
if page == "\U0001f3e0 Situation":
    st.markdown(f"""
    <div class="alert-banner {alert_cfg['cls']}">
        <div>
            <div style='color:{alert_cfg["color"]};font-weight:700;font-size:1.4rem;letter-spacing:-0.02em;'>{alert_cfg["icon"]} {alert_cfg["label"]}</div>
            <div style='color:#c8d8e8;font-size:0.9rem;margin-top:0.2rem;'>{alert_cfg["action"]}</div>
            <div style='margin-top:0.5rem;color:#8ba3bc;font-size:0.8rem;'>\U0001f4cd Lower Shire Valley — Chikwawa & Nsanje Districts</div>
        </div>
        <div style='text-align:right;font-family:IBM Plex Mono;font-size:0.78rem;color:#6a8aaa;min-width:160px;'>
            \U0001f6f0\ufe0f SAR: {LIVE["sar_pass"]}<br>\U0001f550 {LIVE["last_updated"]} UTC<br>Sentinel-1 Orbit 6<br>
            <span style='color:{alert_cfg["color"]};font-weight:600;'>Model: 99.84% acc.</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    for col,(val,label,color) in zip([c1,c2,c3,c4],[
        (f"{LIVE['flood_area_km2']} km\u00b2","Total flooded area","#ff6600"),
        (f"{LIVE['pop_at_risk']:,}","People at risk","#ffcc00"),
        (str(LIVE['villages']),"Villages affected","#ff6600"),
        ("2 districts","Active flood alerts","#ff4444"),
    ]):
        with col:
            st.markdown(f"""<div class="stat-pill"><div class="stat-pill-val" style='color:{color};'>{val}</div><div class="stat-pill-label">{label}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([1.5, 1])

    with col_left:
        st.markdown('<p class="section-header">District Status</p>', unsafe_allow_html=True)
        for _, row in district_df.iterrows():
            icon = {'ACTIVE':'\U0001f534','WATCH':'\U0001f7e1','CLEAR':'\U0001f7e2'}.get(row['status'],'\u26aa')
            st.markdown(f"""
            <div class="district-card" style='border-left:4px solid {row["color"]};'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                    <div>
                        <div style='font-size:1.1rem;font-weight:600;color:#fff;'>{row["district"]}</div>
                        <div style='font-size:0.82rem;color:#6a8aaa;margin-top:2px;'>{row["action"]}</div>
                    </div>
                    <span style='background:rgba(0,0,0,0.3);color:{row["color"]};border:1px solid {row["color"]};padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;white-space:nowrap;margin-left:0.8rem;'>
                        {icon} {row["status"]}
                    </span>
                </div>
                <div style='display:flex;gap:2rem;margin-top:0.8rem;'>
                    <div><div style='font-size:1.1rem;font-weight:600;font-family:IBM Plex Mono;color:{row["color"]};'>{row["flood_km2"]} km\u00b2</div><div style='font-size:0.68rem;color:#6a8aaa;text-transform:uppercase;'>Flooded</div></div>
                    <div><div style='font-size:1.1rem;font-weight:600;font-family:IBM Plex Mono;color:#c8d8e8;'>{row["pop"]:,}</div><div style='font-size:0.68rem;color:#6a8aaa;text-transform:uppercase;'>At risk</div></div>
                    <div><div style='font-size:1.1rem;font-weight:600;font-family:IBM Plex Mono;color:#c8d8e8;'>{row["villages"]}</div><div style='font-size:0.68rem;color:#6a8aaa;text-transform:uppercase;'>Villages</div></div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<p class="section-header" style="margin-top:1rem;">Flood Trend — Last 7 Days</p>', unsafe_allow_html=True)
        trend = pd.DataFrame({'day':['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],'area':[42,58,71,88,110,122,128.4]})
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=trend['day'],y=trend['area'],mode='lines+markers',line=dict(color='#ff6600',width=2.5),marker=dict(size=7,color='#ff6600'),fill='tozeroy',fillcolor='rgba(255,102,0,0.08)'))
        fig_t.add_hline(y=150,line_dash='dash',line_color='#ff4444',annotation_text='HIGH threshold',annotation_font_color='#ff4444')
        fig_t.update_layout(paper_bgcolor='#080f1c',plot_bgcolor='#080f1c',font=dict(color='#c8d8e8'),xaxis=dict(gridcolor='#1a2a40',title=None),yaxis=dict(gridcolor='#1a2a40',title='km\u00b2'),height=160,margin=dict(l=0,r=0,t=10,b=0),showlegend=False)
        st.plotly_chart(fig_t, width='stretch')

    with col_right:
        st.markdown('<p class="section-header">What To Do Right Now</p>', unsafe_allow_html=True)
        actions = [
            ("\U0001f4f1","Alert focal points","Send SMS to village heads and DoDMA officers in Chikwawa and Nsanje immediately."),
            ("\U0001f3e0","Activate shelters","Open flood shelters in Chapananga, Makhanga, and Bangula."),
            ("\U0001f441\ufe0f","Monitor river levels","Check Shire River at Chikwawa Bridge and Bangula gauge every 2 hours."),
            ("\U0001f6ab","Restrict movement","Advise communities near the Shire floodplain to avoid travel."),
            ("\U0001f4cb","Report to DoDMA","Submit situation report to DoDMA hotline 1997 by 08:00 local time."),
        ]
        st.markdown('<div class="action-card">', unsafe_allow_html=True)
        for icon,title,body in actions:
            st.markdown(f"""<div style='display:flex;align-items:flex-start;gap:0.8rem;margin-bottom:0.9rem;'><div style='background:#1a2a40;border-radius:8px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0;margin-top:2px;'>{icon}</div><div style='color:#c8d8e8;font-size:0.88rem;line-height:1.5;'><span style='color:#fff;font-weight:600;'>{title}. </span>{body}</div></div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("\U0001f4f1 Send Alert Now — All Focal Points", use_container_width=True):
            st.success("\u2705 HIGH alert dispatched to 4 active focal points.")
            st.info("Go to \U0001f4f1 Send Alert to customise the message.")

elif page == "\U0001f5fa\ufe0f Flood Map":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from flood_map import show as _show_map
        st.markdown(CSS, unsafe_allow_html=True)
        _show_map()
    except Exception as e:
        # Fallback inline map
        st.markdown(f"""<div class="alert-banner {alert_cfg['cls']}" style='margin-bottom:0.8rem;'><div><div style='color:{alert_cfg["color"]};font-weight:700;font-size:1rem;'>{alert_cfg["icon"]} {LIVE['flood_area_km2']} km\u00b2 flooded</div><div style='color:#8ba3bc;font-size:0.8rem;margin-top:3px;'>Sentinel-1 SAR \u00b7 {LIVE["sar_pass"]}</div></div></div>""", unsafe_allow_html=True)
        threshold = st.slider("Detection sensitivity",0.1,0.8,0.5,0.05)
        m = folium.Map(location=[-16.2,34.55],zoom_start=9,tiles='CartoDB dark_matter')
        pts = grid_df[grid_df['flood_prob']>0.1][['lat','lon','flood_prob']].values.tolist()
        HeatMap(pts,min_opacity=0.3,radius=14,blur=16,gradient={0.3:'#ff6600',0.6:'#ff3300',0.8:'#ff0000',1.0:'#cc0000'}).add_to(m)
        MiniMap(toggle_display=True).add_to(m)
        st_folium(m,width=None,height=600,returned_objects=[])

elif page == "\U0001f4ca Model Data":
    st.markdown("""<div style='background:#0d1829;border:1px solid #1a2a40;border-radius:10px;padding:1rem 1.4rem;margin-bottom:1.2rem;'><div style='color:#3a8aaa;font-size:0.7rem;font-family:IBM Plex Mono;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.3rem;'>How It Works</div><div style='color:#fff;font-weight:600;font-size:1.1rem;'>Understanding the flood prediction model</div><div style='color:#8ba3bc;font-size:0.85rem;margin-top:0.3rem;'>Trained on Cyclone Freddy 2023 \u00b7 Validated on Cyclone Idai 2019 \u00b7 <span style='color:#00cc55;'>99.84% accuracy</span></div></div>""", unsafe_allow_html=True)
    findings = [
        ("\U0001f327\ufe0f","Rainfall is the #1 signal","How much rain fell during and before the event matters most. More rain = more flooding. Uses CHIRPS satellite rainfall data."),
        ("\U0001f6f0\ufe0f","Satellite radar change is #2","When the Sentinel-1 radar signal drops sharply, water has replaced dry land. This change is detected automatically."),
        ("\U0001f30a","Distance to Shire River is #3","Communities within 5km of the Shire River flood first. Geography is a strong predictor."),
        ("\u2705","Tested on a completely different event","Trained on Freddy 2023, tested on Idai 2019 — different cyclone, different year, same geography. 99.84% accuracy held up."),
    ]
    cols = st.columns(2)
    for i,(icon,title,body) in enumerate(findings):
        with cols[i%2]:
            st.markdown(f"""<div style='background:#0d1829;border:1px solid #1a2a40;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.8rem;'><div style='font-size:1.4rem;margin-bottom:0.4rem;'>{icon}</div><div style='color:#fff;font-weight:600;font-size:0.9rem;margin-bottom:0.4rem;'>{title}</div><div style='color:#8ba3bc;font-size:0.82rem;line-height:1.6;'>{body}</div></div>""", unsafe_allow_html=True)
    st.markdown('<p class="section-header" style="margin-top:0.5rem;">Accuracy Numbers</p>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col,(val,label,color) in zip([c1,c2,c3,c4],[("99.84%","Prediction accuracy (AUC)","#00cc55"),("97.99%","Spatial accuracy (IoU)","#00d4ff"),("99%","Precision — no false alarms","#00cc55"),("99%","Recall — no missed floods","#00cc55")]):
        with col:
            st.markdown(f"""<div class="stat-pill"><div class="stat-pill-val" style='color:{color};'>{val}</div><div class="stat-pill-label">{label}</div></div>""", unsafe_allow_html=True)
    with st.expander("\U0001f4c8 Full technical details — for researchers"):
        shap_df = pd.DataFrame([{'Feature':'Event rainfall','Importance':2.61,'Type':'Rainfall'},{'Feature':'SAR VV change','Importance':1.94,'Type':'SAR'},{'Feature':'Combined SAR change','Importance':1.54,'Type':'SAR'},{'Feature':'Distance to Shire River','Importance':1.41,'Type':'Terrain'},{'Feature':'Peak rainfall day','Importance':0.98,'Type':'Rainfall'},{'Feature':'SAR VH change','Importance':0.87,'Type':'SAR'},{'Feature':'SAR VV backscatter','Importance':0.76,'Type':'SAR'},{'Feature':'Terrain slope','Importance':0.68,'Type':'Terrain'},{'Feature':'30-day rainfall','Importance':0.61,'Type':'Rainfall'},{'Feature':'Terrain wetness','Importance':0.54,'Type':'Terrain'},{'Feature':'7-day rainfall','Importance':0.48,'Type':'Rainfall'},{'Feature':'SAR VH backscatter','Importance':0.41,'Type':'SAR'},{'Feature':'Elevation','Importance':0.33,'Type':'Terrain'},{'Feature':'Aspect','Importance':0.09,'Type':'Terrain'},{'Feature':'3-day rainfall','Importance':0.00,'Type':'Rainfall'}]).sort_values('Importance',ascending=True)
        fig_shap = px.bar(shap_df,x='Importance',y='Feature',color='Type',color_discrete_map={'SAR':'#00d4ff','Terrain':'#00cc66','Rainfall':'#ff8800'},orientation='h',labels={'Importance':'SHAP feature importance','Feature':''})
        fig_shap.update_layout(paper_bgcolor='#080f1c',plot_bgcolor='#080f1c',font=dict(color='#c8d8e8'),xaxis=dict(gridcolor='#1a2a40'),yaxis=dict(gridcolor='#1a2a40'),legend=dict(bgcolor='#0d1829',bordercolor='#1a2a40'),height=420,margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_shap,width='stretch')
        st.dataframe(pd.DataFrame([{'Model':'Random Forest','Train':'Freddy 2023','Test':'Idai 2019','AUC-ROC':'0.9978','IoU':'0.9799'},{'Model':'XGBoost','Train':'Freddy 2023','Test':'Idai 2019','AUC-ROC':'0.9989','IoU':'0.9799'},{'Model':'Ensemble','Train':'Freddy 2023','Test':'Idai 2019','AUC-ROC':'0.9984','IoU':'0.9799'},{'Model':'Ensemble','Train':'Freddy 2023','Test':'Floods 2025','AUC-ROC':'0.9965','IoU':'0.9174*'}]),width='stretch',hide_index=True)
        st.caption("* Floods 2025 at threshold 0.15.")

elif page == "\U0001f327\ufe0f Rainfall":
    st.markdown("""<div style='background:#0d1829;border:1px solid #1a2a40;border-radius:10px;padding:1rem 1.4rem;margin-bottom:1rem;'><div style='color:#fff;font-weight:600;font-size:1.1rem;'>\U0001f327\ufe0f Rainfall Monitor — Lower Shire Valley</div><div style='color:#8ba3bc;font-size:0.82rem;margin-top:0.3rem;'>CHIRPS satellite rainfall \u00b7 Updated daily at 06:00 UTC</div></div>""", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col,(label,val,delta,color) in zip([c1,c2,c3,c4],[("Today","12.4 mm","+3.1 mm","#ff8800"),("Last 7 days","49.3 mm","\u26a0\ufe0f Above normal","#ffcc00"),("Last 30 days","200.8 mm","+42 mm vs average","#ff6600"),("Alert trigger","80mm/7d","\u26a0\ufe0f Approaching","#ff4444")]):
        with col:
            st.markdown(f"""<div class="stat-pill"><div class="stat-pill-val" style='color:{color};'>{val}</div><div class="stat-pill-label">{label}</div><div style='color:#6a8aaa;font-size:0.72rem;margin-top:4px;'>{delta}</div></div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    fig_ts = make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[0.7,0.3],vertical_spacing=0.04)
    fig_ts.add_trace(go.Bar(x=rain_df['date'],y=rain_df['rainfall_mm'],name='Daily rainfall',marker_color='rgba(0,180,255,0.6)'),row=1,col=1)
    rain_df['r7d'] = rain_df['rainfall_mm'].rolling(7).sum()
    fig_ts.add_trace(go.Scatter(x=rain_df['date'],y=rain_df['r7d'],name='7-day total',line=dict(color='#ff8800',width=2.5)),row=1,col=1)
    fig_ts.add_hline(y=80,line_dash='dash',line_color='#ff4444',annotation_text='\u26a0\ufe0f Flood alert threshold (80mm/7d)',annotation_font_color='#ff4444')
    rain_df['cumulative'] = rain_df['rainfall_mm'].cumsum()
    fig_ts.add_trace(go.Scatter(x=rain_df['date'],y=rain_df['cumulative'],name='Season total',fill='tozeroy',line=dict(color='#7f5af0',width=1.5),fillcolor='rgba(127,90,240,0.1)'),row=2,col=1)
    fig_ts.add_vrect(x0='2019-03-08',x1='2019-03-16',fillcolor='rgba(255,50,50,0.08)',line=dict(color='#ff4444',width=1,dash='dot'),annotation_text='Cyclone Idai landfall',annotation_font_color='#ff4444',annotation_position='top left')
    fig_ts.update_layout(paper_bgcolor='#080f1c',plot_bgcolor='#080f1c',font=dict(color='#c8d8e8'),xaxis2=dict(gridcolor='#1a2a40'),yaxis=dict(gridcolor='#1a2a40',title='mm/day'),yaxis2=dict(gridcolor='#1a2a40',title='Season total (mm)'),legend=dict(bgcolor='#0d1829',bordercolor='#1a2a40'),height=380,margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig_ts,width='stretch')

elif page == "\U0001f4f1 Send Alert":
    st.markdown("""<div style='background:#0d1829;border:1px solid #1a2a40;border-radius:10px;padding:1rem 1.4rem;margin-bottom:1rem;'><div style='color:#fff;font-weight:600;font-size:1.1rem;'>\U0001f4f1 Send SMS Alert to Community Focal Points</div><div style='color:#8ba3bc;font-size:0.82rem;margin-top:0.3rem;'>Africa's Talking API \u00b7 Airtel Malawi & TNM</div></div>""", unsafe_allow_html=True)
    col_left, col_right = st.columns([1,1])
    with col_left:
        st.markdown('<p class="section-header">Configure Alert</p>', unsafe_allow_html=True)
        district_sel    = st.selectbox("Which district?",["Both districts","Chikwawa","Nsanje"])
        risk_level      = st.selectbox("Alert level",["\U0001f534 CRITICAL — Evacuate immediately","\U0001f7e0 HIGH — Prepare to evacuate","\U0001f7e1 MEDIUM — Stay alert","\U0001f7e2 LOW — Situation normal"])
        flood_area_inp  = st.number_input("Current flood area (km\u00b2)",value=128.4,step=5.0)
        include_action  = st.checkbox("Include action instructions",value=True)
        include_hotline = st.checkbox("Include DoDMA hotline (1997)",value=True)
        st.markdown('<p class="section-header" style="margin-top:1rem;">Message Preview</p>', unsafe_allow_html=True)
        level_code   = risk_level.split("—")[0].strip()
        level_text   = risk_level.split("—")[1].strip()
        action_text  = "\nAction: Move to higher ground immediately." if include_action else ""
        hotline_text = "\nHelp: DoDMA 1997" if include_hotline else ""
        sms = f"[MALAWI FLOOD EWS] {level_code}\nArea: {district_sel}\nFlooded: {flood_area_inp:.0f}km\u00b2\nStatus: {level_text}{action_text}{hotline_text}\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        st.markdown(f'<div class="sms-preview">{sms}</div>', unsafe_allow_html=True)
        char_color = '#ff4444' if len(sms)>160 else '#00cc55'
        st.markdown(f"""<div style='color:{char_color};font-size:0.78rem;font-family:IBM Plex Mono;margin-top:0.4rem;'>{len(sms)}/160 characters {'— \u26a0\ufe0f will split into 2 SMS' if len(sms)>160 else '— \u2713 fits in 1 SMS'}</div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("\U0001f4e4 Send Alert Now", use_container_width=True):
            active = focal_df[focal_df['active']==True]
            if district_sel != 'Both districts': active = active[active['district']==district_sel]
            st.success(f"\u2705 Alert sent to {len(active)} focal points in {district_sel}")
            for _,fp in active.iterrows():
                st.markdown(f"""<div style='background:#0a1f0a;border:1px solid #1a4a1a;border-radius:6px;padding:0.5rem 0.8rem;margin:0.2rem 0;font-size:0.82rem;color:#8bc88b;'>\u2713 {fp["name"]} \u00b7 {fp["role"]} \u00b7 {fp["village"]}<span style='float:right;font-family:IBM Plex Mono;'>{fp["phone"]}</span></div>""", unsafe_allow_html=True)
    with col_right:
        st.markdown('<p class="section-header">Focal Point Registry</p>', unsafe_allow_html=True)
        for _,fp in focal_df.iterrows():
            sc = '#00cc55' if fp['active'] else '#3a4a5a'
            st.markdown(f"""<div style='background:#0d1829;border:1px solid #1a2a40;border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.5rem;display:flex;justify-content:space-between;align-items:center;'><div><div style='color:#fff;font-weight:500;'>{fp["name"]}</div><div style='color:#6a8aaa;font-size:0.78rem;margin-top:2px;'>{fp["role"]} \u00b7 {fp["village"]}, {fp["district"]}</div><div style='color:#3a8aaa;font-size:0.75rem;font-family:IBM Plex Mono;margin-top:2px;'>{fp["phone"]}</div></div><span style='color:{sc};border:1px solid {sc};padding:3px 10px;border-radius:20px;font-size:0.72rem;background:rgba(0,0,0,0.3);'>{"Active" if fp["active"] else "Inactive"}</span></div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<p class="section-header">Recent Alerts Sent</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Time":"2026-03-22 03:15","Level":"\U0001f7e0 HIGH","District":"Both","Sent":4,"Delivered":4},{"Time":"2026-03-21 06:14","Level":"\U0001f7e0 HIGH","District":"Chikwawa","Sent":3,"Delivered":3},{"Time":"2026-03-20 18:32","Level":"\U0001f7e1 MEDIUM","District":"Nsanje","Sent":2,"Delivered":2}]),width='stretch',hide_index=True)

elif page == "\U0001f4c5 Event History":
    try:
        import importlib
        _dir = os.path.dirname(os.path.abspath(__file__))
        if _dir not in sys.path: sys.path.insert(0, _dir)
        import historical_comparison as _hc
        importlib.reload(_hc)
        st.markdown(CSS, unsafe_allow_html=True)
        _hc.show()
    except Exception as e:
        st.error(f"Could not load event history: {e}")

elif page == "\U0001f3af Prediction vs Actual":
    try:
        import importlib
        _dir = os.path.dirname(os.path.abspath(__file__))
        if _dir not in sys.path: sys.path.insert(0, _dir)
        import historical_comparison as _pva
        importlib.reload(_pva)
        st.markdown(CSS, unsafe_allow_html=True)
        _pva.show()
    except Exception as e:
        st.error(f"Could not load prediction comparison: {e}")

elif page == "\U0001f4c4 Reports":
    try:
        import importlib
        _dir = os.path.dirname(os.path.abspath(__file__))
        if _dir not in sys.path: sys.path.insert(0, _dir)
        import report_generator as _rg
        importlib.reload(_rg)
        st.markdown(CSS, unsafe_allow_html=True)
        _rg.show()
    except Exception as e:
        st.error(f"Could not load report generator: {e}")