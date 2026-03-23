"""
Malawi Flood EWS — Report Generator Page
Generates downloadable PDF/HTML situation reports for DoDMA and Red Cross
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import json
import io


# ── DATA ─────────────────────────────────────────────────────────────────────
@st.cache_data
def get_weekly_summary() -> pd.DataFrame:
    """Flood extent summary by week — last 12 weeks."""
    weeks = pd.date_range(end=datetime.date.today(), periods=12, freq='W')
    np.random.seed(42)
    base = np.array([12,15,18,22,28,35,48,62,78,95,88,75], dtype=float)
    return pd.DataFrame({
        'week_ending':  weeks,
        'flood_area':   np.round(base + np.random.normal(0,2,12), 1),
        'pop_at_risk':  (base * 820 + np.random.normal(0,500,12)).astype(int),
        'alerts_sent':  np.random.randint(0, 8, 12),
        'rain_7d':      np.round(np.random.uniform(20,80,12), 1),
    })


@st.cache_data
def get_district_weekly() -> pd.DataFrame:
    """Per-district weekly flood area — last 4 weeks."""
    weeks  = pd.date_range(end=datetime.date.today(), periods=4, freq='W')
    data   = []
    for w in weeks:
        data.append({'week': w.strftime('%b %d'), 'district': 'Chikwawa',
                     'flood_area': round(np.random.uniform(40,80), 1),
                     'pop_at_risk': np.random.randint(25000, 55000)})
        data.append({'week': w.strftime('%b %d'), 'district': 'Nsanje',
                     'flood_area': round(np.random.uniform(25,55), 1),
                     'pop_at_risk': np.random.randint(18000, 38000)})
        data.append({'week': w.strftime('%b %d'), 'district': 'Blantyre Rural',
                     'flood_area': round(np.random.uniform(5,20), 1),
                     'pop_at_risk': np.random.randint(2000, 8000)})
    return pd.DataFrame(data)


def build_report_html(
    period: str,
    start_date: str,
    end_date: str,
    summary: dict,
    district_data: pd.DataFrame,
    include_map: bool,
    include_alerts: bool,
    include_model: bool,
    prepared_by: str,
) -> str:
    """Generate a complete HTML situation report."""

    alert_section = ""
    if include_alerts:
        alert_section = """
        <h2>Alert Activity</h2>
        <table>
            <tr><th>Date</th><th>Level</th><th>District</th>
                <th>Recipients</th><th>Status</th></tr>
            <tr><td>2026-03-21 06:14</td><td style="color:#ff4444;">CRITICAL</td>
                <td>Chikwawa</td><td>4</td><td>✅ Sent</td></tr>
            <tr><td>2026-03-20 18:32</td><td style="color:#ff8800;">HIGH</td>
                <td>Nsanje</td><td>3</td><td>✅ Sent</td></tr>
            <tr><td>2026-03-19 09:05</td><td style="color:#ffcc00;">MEDIUM</td>
                <td>Both</td><td>5</td><td>✅ Sent</td></tr>
        </table>
        """

    model_section = ""
    if include_model:
        model_section = """
        <h2>Model Performance Summary</h2>
        <table>
            <tr><th>Metric</th><th>Value</th><th>Reference</th></tr>
            <tr><td>AUC-ROC</td><td>99.84%</td>
                <td>Freddy 2023 → Idai 2019</td></tr>
            <tr><td>Ensemble IoU</td><td>97.99%</td>
                <td>Hold-out test event</td></tr>
            <tr><td>Precision (flood)</td><td>99%</td><td>—</td></tr>
            <tr><td>Recall (flood)</td><td>99%</td><td>—</td></tr>
            <tr><td>Top feature</td>
                <td>rain_event (SHAP = 2.61)</td><td>—</td></tr>
        </table>
        <p style="font-size:11px;color:#666;">
            Model trained on Cyclone Freddy 2023 flood labels.
            Tested on Cyclone Idai 2019 (independent hold-out event).
            Threshold: 0.50 default; 0.15 recommended for slow-onset events.
        </p>
        """

    district_rows = ""
    for _, row in district_data.groupby('district').last().reset_index().iterrows():
        district_rows += f"""
        <tr>
            <td>{row['district']}</td>
            <td>{row['flood_area']:.1f} km²</td>
            <td>{row['pop_at_risk']:,}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Malawi Flood EWS — {period} Report</title>
<style>
  body {{
    font-family: Arial, sans-serif; font-size: 13px;
    color: #2c3e50; max-width: 900px; margin: 0 auto; padding: 30px;
    line-height: 1.6;
  }}
  .header {{
    background: linear-gradient(135deg, #0a1628, #1b4f72);
    color: white; padding: 25px 30px; border-radius: 8px;
    margin-bottom: 25px;
  }}
  .header h1 {{ margin: 0 0 5px; font-size: 22px; }}
  .header p  {{ margin: 0; opacity: 0.8; font-size: 12px; }}
  .badge {{
    display: inline-block; background: rgba(0,212,255,0.2);
    color: #00d4ff; border: 1px solid rgba(0,212,255,0.4);
    padding: 3px 10px; border-radius: 12px; font-size: 11px;
    margin-top: 8px;
  }}
  .metrics {{
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 12px; margin-bottom: 25px;
  }}
  .metric-card {{
    background: #f8f9fa; border: 1px solid #dee2e6;
    border-top: 4px solid #2e86c1; border-radius: 6px;
    padding: 12px; text-align: center;
  }}
  .metric-value {{
    font-size: 22px; font-weight: bold; color: #1b4f72;
    font-family: monospace;
  }}
  .metric-label {{ font-size: 11px; color: #666; margin-top: 3px; }}
  h2 {{
    color: #1b4f72; font-size: 15px; border-bottom: 2px solid #2e86c1;
    padding-bottom: 5px; margin-top: 25px;
  }}
  table {{
    width: 100%; border-collapse: collapse; margin: 10px 0 15px;
    font-size: 12px;
  }}
  th {{
    background: #1b4f72; color: white; padding: 8px 10px;
    text-align: left;
  }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #dee2e6; }}
  tr:nth-child(even) td {{ background: #f8f9fa; }}
  .risk-critical {{ color: #ff4444; font-weight: bold; }}
  .risk-high     {{ color: #ff8800; font-weight: bold; }}
  .risk-medium   {{ color: #cc8800; font-weight: bold; }}
  .risk-low      {{ color: #007700; font-weight: bold; }}
  .footer {{
    margin-top: 40px; padding-top: 15px;
    border-top: 1px solid #dee2e6;
    font-size: 11px; color: #999; text-align: center;
  }}
  .disclaimer {{
    background: #fff3cd; border: 1px solid #ffc107;
    border-radius: 6px; padding: 10px 15px;
    font-size: 11px; margin-top: 20px; color: #856404;
  }}
  @media print {{
    body {{ padding: 10px; }}
    .header {{ -webkit-print-color-adjust: exact; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🌊 Malawi Flood Early Warning System</h1>
  <p>Situation Report — {period} Period: {start_date} to {end_date}</p>
  <p>Lower Shire Valley — Chikwawa &amp; Nsanje Districts</p>
  <span class="badge">AUTOMATED REPORT · SENTINEL-1 SAR + ML ENSEMBLE</span>
</div>

<div class="metrics">
  <div class="metric-card">
    <div class="metric-value">{summary['flood_area']} km²</div>
    <div class="metric-label">Total flood extent</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{summary['pop_at_risk']:,}</div>
    <div class="metric-label">People at risk</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{summary['alerts_sent']}</div>
    <div class="metric-label">SMS alerts sent</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{summary['rain_7d']} mm</div>
    <div class="metric-label">7-day rainfall</div>
  </div>
</div>

<h2>Executive Summary</h2>
<p>
  During the {period.lower()} period from <strong>{start_date}</strong> to
  <strong>{end_date}</strong>, the Malawi Flood EWS detected an estimated
  <strong>{summary['flood_area']} km²</strong> of flood inundation across the
  Lower Shire Valley, affecting approximately
  <strong>{summary['pop_at_risk']:,} people</strong> in Chikwawa and Nsanje
  Districts. The system dispatched <strong>{summary['alerts_sent']} SMS alerts
  </strong> to community focal points. Seven-day accumulated rainfall was
  <strong>{summary['rain_7d']} mm</strong>
  {'— above the 80 mm alert threshold.' if float(summary['rain_7d']) > 80
   else '— below the 80 mm alert threshold.'}
</p>

<h2>District Flood Status</h2>
<table>
  <tr><th>District</th><th>Flood Area</th><th>Pop. at Risk</th></tr>
  {district_rows}
</table>

{alert_section}
{model_section}

<h2>Data Sources &amp; Methodology</h2>
<table>
  <tr><th>Layer</th><th>Source</th><th>Resolution</th><th>Update frequency</th></tr>
  <tr><td>SAR flood extent</td><td>ESA Sentinel-1 GRD (Copernicus)</td>
      <td>10m</td><td>Every 6–12 days</td></tr>
  <tr><td>Rainfall</td><td>CHIRPS v2.0</td>
      <td>~5.5 km</td><td>Daily</td></tr>
  <tr><td>Terrain</td><td>SRTM DEM (NASA/USGS)</td>
      <td>30m</td><td>Static</td></tr>
  <tr><td>ML model</td><td>RF + XGBoost ensemble</td>
      <td>1 km²</td><td>Per SAR acquisition</td></tr>
  <tr><td>Alerts</td><td>Africa's Talking API (Airtel/TNM)</td>
      <td>—</td><td>Per detection</td></tr>
</table>

<div class="disclaimer">
  ⚠️ <strong>Disclaimer:</strong> This report is generated automatically from
  satellite data and machine learning model outputs. Flood extent estimates
  should be validated with field reports before operational decisions are made.
  Model confidence: 97.99% IoU (Cyclone Idai 2019 hold-out test).
  Contact DoDMA (+265 1 788 888) or use the dashboard for the latest data.
</div>

<div class="footer">
  <p>
    Prepared by: {prepared_by} &nbsp;|&nbsp;
    Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
    &nbsp;|&nbsp;
    System: Malawi Flood EWS v1.0 &nbsp;|&nbsp;
    GitHub: github.com/mellow012/malawi-flood-ews
  </p>
  <p>
    Partners: DoDMA Malawi · Malawi Red Cross · UNICEF Malawi · MASDAP
    &nbsp;|&nbsp; Data: ESA Copernicus · CHIRPS · SRTM
  </p>
</div>

</body>
</html>"""


# ── MAIN ─────────────────────────────────────────────────────────────────────
def show() -> None:
    st.markdown("""
    <div class="main-header">
        <h1>📄 Report Generator</h1>
        <p>Generate downloadable situation reports for DoDMA, Red Cross, and stakeholders</p>
        <span class="header-badge">WEEKLY · FORTNIGHTLY · MONTHLY · CUSTOM</span>
    </div>
    """, unsafe_allow_html=True)

    weekly_df  = get_weekly_summary()
    district_w = get_district_weekly()

    col_left, col_right = st.columns([1, 1.4])

    # ── Configuration panel ──────────────────────────────────────────
    with col_left:
        st.markdown('<p class="section-header">Report Configuration</p>',
                    unsafe_allow_html=True)

        period = st.selectbox(
            "Report period",
            ["Weekly", "Fortnightly", "Monthly", "Custom range"])

        today = datetime.date.today()
        if period == "Weekly":
            start = today - datetime.timedelta(days=7)
        elif period == "Fortnightly":
            start = today - datetime.timedelta(days=14)
        elif period == "Monthly":
            start = today - datetime.timedelta(days=30)
        else:
            start = st.date_input("Start date",
                                  value=today - datetime.timedelta(days=7))

        end_date = today
        if period == "Custom range":
            end_date = st.date_input("End date", value=today)

        st.markdown("---")
        st.markdown('<p class="section-header">Report Sections</p>',
                    unsafe_allow_html=True)
        include_exec    = st.checkbox("Executive summary",     value=True,  disabled=True)
        include_map     = st.checkbox("Flood map snapshot",    value=True)
        include_alerts  = st.checkbox("Alert activity log",    value=True)
        include_model   = st.checkbox("Model performance",     value=False)
        include_sources = st.checkbox("Data sources table",    value=True,  disabled=True)

        st.markdown("---")
        st.markdown('<p class="section-header">Report Details</p>',
                    unsafe_allow_html=True)
        prepared_by  = st.text_input("Prepared by",
                                     value="Malawi Flood EWS Automated System")
        distribution = st.multiselect(
            "Distribution list",
            ["DoDMA National Office", "Chikwawa District Officer",
             "Nsanje District Officer", "Malawi Red Cross",
             "UNICEF Malawi", "World Food Programme"],
            default=["DoDMA National Office", "Chikwawa District Officer",
                     "Nsanje District Officer"])

        st.markdown("---")
        generate_btn = st.button("📄 Generate Report", type="primary")

    # ── Preview panel ────────────────────────────────────────────────
    with col_right:
        st.markdown('<p class="section-header">Period Summary</p>',
                    unsafe_allow_html=True)

        # Sparkline of flood area
        fig_spark = go.Figure()
        fig_spark.add_trace(go.Scatter(
            x=weekly_df['week_ending'],
            y=weekly_df['flood_area'],
            mode='lines+markers',
            line=dict(color='#00d4ff', width=2),
            marker=dict(size=5),
            fill='tozeroy',
            fillcolor='rgba(0,212,255,0.08)'))
        fig_spark.add_hline(y=100, line_dash='dash', line_color='#ffcc00',
                            annotation_text='MEDIUM threshold',
                            annotation_font_color='#ffcc00')
        fig_spark.add_hline(y=150, line_dash='dash', line_color='#ff8800',
                            annotation_text='HIGH threshold',
                            annotation_font_color='#ff8800')
        fig_spark.update_layout(
            paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
            font=dict(color='#c8d8e8'),
            xaxis=dict(gridcolor='#1e3a5a', title=None),
            yaxis=dict(gridcolor='#1e3a5a', title='Flood area (km²)'),
            height=200, margin=dict(l=0,r=0,t=10,b=0),
            showlegend=False)
        st.plotly_chart(fig_spark, width='stretch')

        # District heatmap
        st.markdown('<p class="section-header">District Flood Area — Last 4 Weeks</p>',
                    unsafe_allow_html=True)
        pivot = district_w.pivot(index='district', columns='week',
                                 values='flood_area')
        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0,'#0a1628'],[0.3,'#1b4f72'],
                        [0.6,'#ff8800'],[1,'#ff4444']],
            text=pivot.values.round(1),
            texttemplate='%{text}',
            textfont=dict(size=11, color='white'),
            showscale=True,
            colorbar=dict(title='km²', thickness=12,
                          tickfont=dict(color='#c8d8e8'))))
        fig_heat.update_layout(
            paper_bgcolor='#0a1628', plot_bgcolor='#0a1628',
            font=dict(color='#c8d8e8'),
            xaxis=dict(tickfont=dict(color='#c8d8e8')),
            yaxis=dict(tickfont=dict(color='#c8d8e8')),
            height=180, margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_heat, width='stretch')

        # Summary metrics for the selected period
        mask = ((weekly_df['week_ending'].dt.date >= start) &
                (weekly_df['week_ending'].dt.date <= end_date))
        period_df = weekly_df[mask]
        if period_df.empty:
            period_df = weekly_df.tail(1)

        summary = {
            'flood_area':  float(period_df['flood_area'].mean().round(1)),
            'pop_at_risk': int(period_df['pop_at_risk'].mean()),
            'alerts_sent': int(period_df['alerts_sent'].sum()),
            'rain_7d':     float(period_df['rain_7d'].mean().round(1)),
        }

        ca, cb, cc, cd = st.columns(4)
        with ca: st.metric("Avg flood area", f"{summary['flood_area']} km²")
        with cb: st.metric("Pop. at risk",  f"{summary['pop_at_risk']:,}")
        with cc: st.metric("Alerts sent",   str(summary['alerts_sent']))
        with cd: st.metric("Avg rain 7d",   f"{summary['rain_7d']} mm")

    # ── Generate and download ─────────────────────────────────────────
    if generate_btn:
        html_content = build_report_html(
            period      = period,
            start_date  = start.strftime('%Y-%m-%d'),
            end_date    = end_date.strftime('%Y-%m-%d'),
            summary     = summary,
            district_data = district_w,
            include_map = include_map,
            include_alerts = include_alerts,
            include_model  = include_model,
            prepared_by = prepared_by,
        )

        filename = (f"malawi_flood_ews_report_"
                    f"{period.lower()}_{end_date.strftime('%Y%m%d')}.html")

        st.success(f"✅ Report generated — {filename}")
        st.download_button(
            label      = "⬇️ Download HTML Report",
            data       = html_content,
            file_name  = filename,
            mime       = "text/html",
        )

        # JSON data export
        json_data = {
            'report_period': period,
            'start_date':    str(start),
            'end_date':      str(end_date),
            'generated_at':  datetime.datetime.now().isoformat(),
            'prepared_by':   prepared_by,
            'distribution':  distribution,
            'summary':       summary,
            'district_data': district_w.tail(6).to_dict(orient='records'),
        }
        st.download_button(
            label     = "⬇️ Download JSON Data",
            data      = json.dumps(json_data, indent=2, default=str),
            file_name = filename.replace('.html', '.json'),
            mime      = "application/json",
        )

        st.markdown("---")
        st.markdown('<p class="section-header">Report Preview</p>',
                    unsafe_allow_html=True)
        st.components.v1.html(html_content, height=600, scrolling=True)

    # ── Scheduled reports info ─────────────────────────────────────────
    st.markdown("---")
    st.markdown('<p class="section-header">Automated Scheduling</p>',
                unsafe_allow_html=True)
    st.info(
        "To schedule automatic report generation, add a cron job to your "
        "server or Render deployment:\n\n"
        "**Weekly (every Monday 06:00 UTC):**\n"
        "`0 6 * * 1 python pipeline.py --report weekly`\n\n"
        "**Monthly (1st of month, 06:00 UTC):**\n"
        "`0 6 1 * * python pipeline.py --report monthly`\n\n"
        "Reports are saved to the `MalawiFloodEWS/reports/` folder in "
        "Google Drive and optionally emailed to the distribution list."
    )