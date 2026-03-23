"""
Malawi Flood EWS — Situation Report Generator
Generates downloadable PDF-style text reports for DoDMA and Red Cross
"""

import streamlit as st
import pandas as pd
import datetime


# ── Shared data for reports ───────────────────────────────────────────────────
_LIVE = {
    'flood_area_km2': 128.4, 'alert_level': 'HIGH',
    'last_updated': '2026-03-22 03:09', 'sar_pass': '2026-03-22',
    'pop_at_risk': 145700, 'villages': 78,
    'chikwawa_km2': 78.3, 'nsanje_km2': 50.1,
}

_DISTRICT_DATA = [
    {'district':'Chikwawa',       'risk':'HIGH',  'flood_km2':78.3, 'pop':84200,  'villages':47, 'status':'ACTIVE'},
    {'district':'Nsanje',         'risk':'HIGH',  'flood_km2':50.1, 'pop':61500,  'villages':31, 'status':'ACTIVE'},
    {'district':'Blantyre Rural', 'risk':'MEDIUM','flood_km2':8.3,  'pop':12300,  'villages':8,  'status':'WATCH'},
    {'district':'Thyolo',         'risk':'LOW',   'flood_km2':0.0,  'pop':2100,   'villages':0,  'status':'CLEAR'},
]

_FOCAL_POINTS = [
    {'name':'James Banda', 'role':'Village Head',  'district':'Chikwawa','phone':'+265991234567'},
    {'name':'Grace Mwale', 'role':'DoDMA Officer', 'district':'Nsanje',  'phone':'+265888345678'},
    {'name':'Peter Chirwa','role':'Red Cross',     'district':'Nsanje',  'phone':'+265777456789'},
    {'name':'Mary Phiri',  'role':'Health Worker', 'district':'Chikwawa','phone':'+265999567890'},
]


# ── Report builders ───────────────────────────────────────────────────────────
def _build_sitrep(report_date: str, author: str, include_forecast: bool) -> str:
    districts_txt = "\n".join([
        f"  - {d['district']}: {d['flood_km2']} km² flooded, "
        f"{d['pop']:,} people at risk, {d['villages']} villages — {d['status']}"
        for d in _DISTRICT_DATA
    ])
    focal_txt = "\n".join([
        f"  - {f['name']} ({f['role']}, {f['district']}): {f['phone']}"
        for f in _FOCAL_POINTS
    ])
    forecast_section = ""
    if include_forecast:
        forecast_section = """
5. FORECAST (next 48 hours)
   - Rainfall: 15–25 mm expected across Lower Shire Valley
   - River levels: Shire River at Chikwawa Bridge expected to remain HIGH
   - Flood extent: Risk of further expansion by 10–20 km²
   - Recommendation: Maintain HIGH alert level; prepare contingency for CRITICAL

"""
    return f"""MALAWI DISASTER OPERATIONS MANAGEMENT AUTHORITY (DoDMA)
DEPARTMENT OF CLIMATE CHANGE AND METEOROLOGICAL SERVICES
═══════════════════════════════════════════════════════════════

FLOOD SITUATION REPORT
Lower Shire Valley — Chikwawa & Nsanje Districts

Report Date:   {report_date}
Report Time:   {datetime.datetime.now().strftime('%H:%M')} UTC
Prepared by:   {author}
Data Source:   Sentinel-1 SAR + RF/XGBoost Ensemble (Malawi Flood EWS)
SAR Pass:      {_LIVE['sar_pass']}
Alert Level:   {_LIVE['alert_level']}

───────────────────────────────────────────────────────────────

1. CURRENT SITUATION OVERVIEW

   Total flooded area:   {_LIVE['flood_area_km2']} km²
   Population at risk:   {_LIVE['pop_at_risk']:,} people
   Villages affected:    {_LIVE['villages']}
   Districts on alert:   Chikwawa (HIGH), Nsanje (HIGH)
   Last model update:    {_LIVE['last_updated']} UTC

2. DISTRICT-LEVEL STATUS

{districts_txt}

3. PRIORITY ACTIONS REQUIRED

   a) IMMEDIATE (within 6 hours)
      - Activate flood shelters in Chapananga, Makhanga, and Bangula
      - Deploy SMS alerts to all active focal points
      - Station monitoring teams at Shire River gauge stations
      - Advise communities within 5 km of Shire River to prepare evacuation

   b) SHORT-TERM (within 24 hours)
      - Submit district-level damage assessments to DoDMA headquarters
      - Coordinate with Red Cross Malawi for emergency supply prepositioning
      - Restrict motor vehicle access to low-lying roads near floodplain
      - Conduct headcount at all evacuation shelters

   c) COORDINATION
      - Report to DoDMA National Hotline: 1997
      - Red Cross Malawi Emergency: +265 1 758 110
      - Chikwawa DEC: +265 993 000 001
      - Nsanje DEC: +265 993 000 002

{forecast_section}
4. FOCAL POINT CONTACTS

{focal_txt}

───────────────────────────────────────────────────────────────

5. MODEL TECHNICAL NOTE

   Detection method:  Sentinel-1 SAR C-band (VV+VH polarisation)
   ML model:          Random Forest + XGBoost Ensemble
   Accuracy (AUC):    99.84%
   Spatial acc (IoU): 97.99%
   Training event:    Cyclone Freddy 2023
   Validation event:  Cyclone Idai 2019 (hold-out)
   Pipeline:          AUTO_RollingDetection (GitHub Actions)
   Repository:        github.com/mellow012/malawi-flood-ews

───────────────────────────────────────────────────────────────
END OF SITUATION REPORT
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
Malawi Flood Early Warning System
"""


def _build_alert_bulletin(alert_level: str, districts: list[str]) -> str:
    level_actions = {
        'CRITICAL': 'EVACUATE IMMEDIATELY. Move to designated flood shelters now.',
        'HIGH':     'PREPARE TO EVACUATE. Move valuables to safety and be ready to move.',
        'MEDIUM':   'STAY ALERT. Monitor water levels and follow official guidance.',
        'LOW':      'No immediate action required. Continue monitoring.',
    }
    return f"""MALAWI FLOOD EARLY WARNING SYSTEM
FLOOD ALERT BULLETIN
{'='*50}

ALERT LEVEL: {alert_level}
DATE/TIME:   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
AREA:        {', '.join(districts)}
SOURCE:      DoDMA / Malawi Flood EWS

ACTION REQUIRED:
{level_actions.get(alert_level, 'Monitor situation.')}

CURRENT CONDITIONS:
- Flooded area:     {_LIVE['flood_area_km2']} km²
- People at risk:   {_LIVE['pop_at_risk']:,}
- Shire River:      RISING — above seasonal average

INSTRUCTIONS FOR COMMUNITY MEMBERS:
1. Move to higher ground if water is rising near your home
2. Do not attempt to cross flooded roads or rivers
3. Keep children and elderly away from water
4. Bring livestock and valuables to safety
5. Listen for updates on MBC Radio and community announcements

EMERGENCY CONTACTS:
- DoDMA Hotline:    1997 (free call)
- Red Cross:        +265 1 758 110
- Ambulance:        998

Issued by: Department of Disaster Management Affairs (DoDMA)
{'='*50}
"""


# ── MAIN ──────────────────────────────────────────────────────────────────────
def show() -> None:
    st.markdown("""
    <div class="main-header">
        <h1>📄 Report Generator</h1>
        <p>Generate situation reports and alert bulletins for DoDMA, Red Cross, and field teams</p>
        <span class="header-badge">SITREP · ALERT BULLETIN · FIELD BRIEF</span>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Situation Report", "📢 Alert Bulletin", "📊 Summary Stats"])

    # ── Tab 1: Situation Report ───────────────────────────────────────
    with tab1:
        col_cfg, col_preview = st.columns([1, 1.5])
        with col_cfg:
            st.markdown('<p class="section-header">Report Configuration</p>', unsafe_allow_html=True)
            report_date    = st.date_input("Report date", value=datetime.date.today())
            author         = st.text_input("Prepared by", value="DoDMA Duty Officer")
            include_forecast = st.checkbox("Include 48-hour forecast section", value=True)
            st.markdown("---")
            st.markdown('<p class="section-header">Include Sections</p>', unsafe_allow_html=True)
            inc_districts  = st.checkbox("District status table", value=True)
            inc_actions    = st.checkbox("Priority actions", value=True)
            inc_focal      = st.checkbox("Focal point contacts", value=True)
            inc_technical  = st.checkbox("Model technical note", value=True)
            st.markdown("<br>", unsafe_allow_html=True)
            generate_btn = st.button("📄 Generate Situation Report", use_container_width=True)

        with col_preview:
            st.markdown('<p class="section-header">Report Preview</p>', unsafe_allow_html=True)
            report_text = _build_sitrep(
                report_date=str(report_date),
                author=author,
                include_forecast=include_forecast,
            )
            st.text_area("", value=report_text, height=480, label_visibility="collapsed")
            st.download_button(
                label="⬇️ Download as .txt",
                data=report_text,
                file_name=f"malawi_flood_sitrep_{report_date}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    # ── Tab 2: Alert Bulletin ─────────────────────────────────────────
    with tab2:
        col_cfg2, col_prev2 = st.columns([1, 1.5])
        with col_cfg2:
            st.markdown('<p class="section-header">Bulletin Configuration</p>', unsafe_allow_html=True)
            alert_level = st.selectbox("Alert level", ["HIGH", "CRITICAL", "MEDIUM", "LOW"])
            districts   = st.multiselect("Affected districts",
                                         ["Chikwawa","Nsanje","Blantyre Rural","Thyolo","Phalombe"],
                                         default=["Chikwawa","Nsanje"])
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style='background:#1a0a00;border:1px solid #ff6600;border-radius:8px;
                        padding:0.8rem 1rem;font-size:0.82rem;color:#c8d8e8;line-height:1.8;'>
                <span style='color:#ff6600;font-weight:600;'>Alert level: {alert_level}</span><br>
                Districts: {', '.join(districts) if districts else '—'}<br>
                Flood area: {_LIVE['flood_area_km2']} km²<br>
                Pop. at risk: {_LIVE['pop_at_risk']:,}
            </div>
            """, unsafe_allow_html=True)

        with col_prev2:
            st.markdown('<p class="section-header">Bulletin Preview</p>', unsafe_allow_html=True)
            bulletin_text = _build_alert_bulletin(alert_level, districts or ["Chikwawa","Nsanje"])
            st.text_area("", value=bulletin_text, height=480, label_visibility="collapsed")
            st.download_button(
                label="⬇️ Download Alert Bulletin",
                data=bulletin_text,
                file_name=f"malawi_flood_bulletin_{datetime.date.today()}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    # ── Tab 3: Summary Stats ──────────────────────────────────────────
    with tab3:
        st.markdown('<p class="section-header">Current Situation at a Glance</p>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        for col, (val, label, color) in zip([c1,c2,c3,c4],[
            (f"{_LIVE['flood_area_km2']} km²", "Total flooded",    "#ff6600"),
            (f"{_LIVE['pop_at_risk']:,}",        "People at risk",   "#ffcc00"),
            (str(_LIVE['villages']),             "Villages affected","#ff6600"),
            (_LIVE['alert_level'],               "Alert level",      "#ff4444"),
        ]):
            with col:
                st.markdown(f"""
                <div class="stat-pill">
                    <div class="stat-pill-val" style='color:{color};'>{val}</div>
                    <div class="stat-pill-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-header">District Summary</p>', unsafe_allow_html=True)
        dist_df = pd.DataFrame(_DISTRICT_DATA)
        dist_df.columns = pd.Index(['District','Risk','Flood (km²)','Pop. at Risk','Villages','Status'])
        st.dataframe(dist_df[['District','Risk','Flood (km²)','Pop. at Risk','Villages','Status']],
                     use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown('<p class="section-header">Recent Reports Issued</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([
            {"Date":"2026-03-22","Type":"Situation Report","Author":"DoDMA Duty Officer","Alert":"HIGH"},
            {"Date":"2026-03-21","Type":"Alert Bulletin",  "Author":"DoDMA Duty Officer","Alert":"HIGH"},
            {"Date":"2026-03-20","Type":"Situation Report","Author":"Grace Mwale",        "Alert":"MEDIUM"},
            {"Date":"2026-03-19","Type":"Alert Bulletin",  "Author":"DoDMA Duty Officer","Alert":"MEDIUM"},
        ]), use_container_width=True, hide_index=True)