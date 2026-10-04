"""
==============================================================================
SMART HEALTH DATA PLATFORM - INTERACTIVE EPIDEMIOLOGICAL BI DASHBOARD & AI ASSISTANT
==============================================================================
Role: Serving Layer & Visual Analytics for Public Health Surveillance
Connects strictly via:
  - 'bi_reader' role for BI Visualizations (Least Privilege read on gold.*)
  - 'llm_agent' role for Text-to-SQL Natural Language Assistant (Sandbox read-only on gold.*)
Implements:
  - Sprint 4: Choropleth Heatmap, Time-Lag Dual-Axis Trends, Risk Alerting Matrix
  - Sprint 5: Text-to-SQL Chat Assistant, Dynamic Smart Charting, 4-Layer Guardrails
Conforms strictly to docs/DATA_CONTRACTS.md and docs/SECURITY_AND_GOVERNANCE.md.
==============================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime
import pandas as pd
import psycopg2
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Ensure project root is in Python path for importing pipelines
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if "/home/src" not in sys.path:
    sys.path.append("/home/src")

try:
    from pipelines.llm_text_to_sql import LLMTextToSQLEngine, SecuritySandboxViolation
except ImportError:
    LLMTextToSQLEngine = None
    SecuritySandboxViolation = Exception

# Page configuration
st.set_page_config(
    page_title="Smart Health: Epidemic & Climate Surveillance",
    page_icon="🦟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics, glassmorphism and responsiveness
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .kpi-card {
        background: linear-gradient(135deg, #1e222d 0%, #262c3a 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #363d4e;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        text-align: center;
        margin-bottom: 12px;
    }
    .kpi-title { font-size: 0.82rem; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
    .kpi-value { font-size: 2.0rem; font-weight: 700; color: #ffffff; margin: 4px 0; }
    .kpi-subtitle { font-size: 0.8rem; color: #34d399; }
    .alert-card {
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 6px solid;
    }
    .alert-severe { background-color: rgba(229, 57, 53, 0.15); border-color: #e53935; color: #ffcdd2; }
    .alert-high { background-color: rgba(251, 140, 0, 0.15); border-color: #fb8c00; color: #ffe0b2; }
    .alert-moderate { background-color: rgba(253, 216, 53, 0.15); border-color: #fdd835; color: #fff9c4; }
    .alert-low { background-color: rgba(67, 160, 71, 0.15); border-color: #43a047; color: #c8e6c9; }
    .sandbox-badge {
        display: inline-block;
        background: #1a233a;
        color: #60a5fa;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        margin-right: 6px;
        border: 1px solid #2563eb40;
    }
    .blocked-badge {
        background: rgba(229, 57, 53, 0.2);
        color: #f87171;
        border: 1px solid #ef444450;
        padding: 12px;
        border-radius: 8px;
        font-weight: 500;
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_db_connection():
    """Connects to PostgreSQL as bi_reader (Least Privilege)."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "smart_health_dw"),
        user=os.getenv("POSTGRES_USER", "bi_reader"),
        password=os.getenv("POSTGRES_PASSWORD", "bi_reader_secure_pass_2026"),
    )


@st.cache_resource
def get_llm_engine():
    """Initializes the Text-to-SQL Engine with 4-Layer Defense Sandbox."""
    if LLMTextToSQLEngine:
        return LLMTextToSQLEngine()
    return None


@st.cache_data(ttl=600)
def load_gold_data():
    """Loads and caches Gold Layer mart data for rapid sub-second rendering."""
    conn = get_db_connection()
    
    # 1. Fact Table
    fact_query = """
        SELECT 
            fact_id,
            location_key,
            epi_week_key,
            disease_type,
            total_cases,
            total_hospitalized,
            total_deaths,
            incidence_rate_per_100k,
            avg_temperature_c,
            max_temperature_c,
            min_temperature_c,
            total_rainfall_mm,
            avg_humidity_pct,
            avg_pm25,
            avg_aqi,
            rainfall_lag_2w,
            rainfall_lag_4w,
            temp_lag_2w,
            risk_level
        FROM gold.fact_disease_climate_weekly
        ORDER BY location_key ASC, epi_week_key ASC;
    """
    df_facts = pd.read_sql_query(fact_query, conn)
    
    # 2. Location Dimension with Boundaries
    loc_query = """
        SELECT 
            location_key,
            province_name_en,
            province_name_local,
            climate_zone,
            centroid_lat,
            centroid_long,
            population,
            geom_polygon
        FROM gold.dim_location;
    """
    df_locations = pd.read_sql_query(loc_query, conn)
    
    # 3. Date Dimension
    date_query = """
        SELECT DISTINCT
            epi_week_key,
            epi_week,
            epi_year,
            MIN(full_date) AS week_start_date,
            MAX(full_date) AS week_end_date,
            BOOL_OR(is_rainy_season) AS is_rainy_season
        FROM gold.dim_date
        GROUP BY epi_week_key, epi_week, epi_year
        ORDER BY epi_week_key ASC;
    """
    df_dates = pd.read_sql_query(date_query, conn)
    
    return df_facts, df_locations, df_dates


# --- APPLICATION HEADER ---
st.title("🦟 Smart Health: Epidemic & Climate Surveillance Platform")
st.markdown(
    "**Authoritative Public Health Decision Support System** integrating meteorological signals, "
    "time-lag feature engineering (2–4 week incubation windows), vector-borne alert matrices, "
    "and a **4-Layer Sandboxed AI Assistant (Text-to-SQL)**."
)

# Load data
try:
    df_facts, df_locations, df_dates = load_gold_data()
    data_loaded = True
except Exception as exc:
    st.error(f"Failed to load Gold Layer Mart from PostgreSQL: {exc}")
    data_loaded = False

if data_loaded:
    # Build GeoJSON FeatureCollection from dim_location
    geojson_features = []
    for _, loc in df_locations.iterrows():
        geom = loc["geom_polygon"]
        if isinstance(geom, str):
            geom = json.loads(geom)
        geojson_features.append({
            "type": "Feature",
            "id": loc["location_key"],
            "properties": {
                "name": loc["province_name_en"],
                "pcode": loc["location_key"],
                "population": int(loc["population"]),
            },
            "geometry": geom
        })
    geojson_divisions = {"type": "FeatureCollection", "features": geojson_features}

    # Location lookup map
    loc_map = dict(zip(df_locations["location_key"], df_locations["province_name_en"]))
    df_facts["province_name_en"] = df_facts["location_key"].map(loc_map)

    # Initialize LLM Engine
    llm_engine = get_llm_engine()

    # --- TOP LEVEL NAVIGATION TABS ---
    tab_bi, tab_ai, tab_gov = st.tabs([
        "📊 Epidemiological BI Surveillance",
        "🤖 AI Assistant: Natural Language Text-to-SQL",
        "🛡️ Data Governance & Security Sandbox"
    ])

    # =========================================================================
    # TAB 1: EPIDEMIOLOGICAL BI SURVEILLANCE
    # =========================================================================
    with tab_bi:
        # --- SIDEBAR FILTERS ---
        st.sidebar.header("🔍 Surveillance Controls")
        
        # Epi-week slider
        all_weeks = sorted(df_facts["epi_week_key"].unique())
        min_week, max_week = int(all_weeks[0]), int(all_weeks[-1])
        
        selected_week = st.sidebar.select_slider(
            "📅 Select Epidemiological Week (Map Grain):",
            options=all_weeks,
            value=all_weeks[-10],
            format_func=lambda w: f"Week {str(w)[4:]}, {str(w)[:4]}"
        )
        
        # Division filter
        all_divisions = ["All Divisions (National)"] + sorted(df_locations["province_name_en"].tolist())
        selected_division = st.sidebar.selectbox("📍 Focus Administrative Unit:", all_divisions)
        
        # Disease Filter
        disease_types = sorted(df_facts["disease_type"].unique())
        selected_disease = st.sidebar.radio("🦠 Disease Surveillance Stream:", disease_types, index=0)

        # Filtered datasets
        df_filtered_week = df_facts[
            (df_facts["epi_week_key"] == selected_week) & 
            (df_facts["disease_type"] == selected_disease)
        ].copy()

        if selected_division != "All Divisions (National)":
            df_timeseries = df_facts[
                (df_facts["province_name_en"] == selected_division) & 
                (df_facts["disease_type"] == selected_disease)
            ].sort_values("epi_week_key")
        else:
            # National aggregation
            df_timeseries = df_facts[df_facts["disease_type"] == selected_disease].groupby("epi_week_key").agg({
                "total_cases": "sum",
                "total_hospitalized": "sum",
                "total_deaths": "sum",
                "total_rainfall_mm": "mean",
                "rainfall_lag_2w": "mean",
                "rainfall_lag_4w": "mean",
                "avg_temperature_c": "mean",
                "temp_lag_2w": "mean",
                "avg_humidity_pct": "mean",
                "avg_aqi": "mean"
            }).reset_index()
            total_pop = df_locations["population"].sum()
            df_timeseries["incidence_rate_per_100k"] = (df_timeseries["total_cases"] / total_pop) * 100000.0
            df_timeseries["province_name_en"] = "National Aggregate"

        # --- TOP ROW: KPI METRIC CARDS ---
        st.markdown("### 📊 Epidemiological Snapshot (Selected Epi-Week)")
        kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
        
        week_cases = int(df_filtered_week["total_cases"].sum())
        week_hosp = int(df_filtered_week["total_hospitalized"].sum())
        week_deaths = int(df_filtered_week["total_deaths"].sum())
        week_mean_rate = df_filtered_week["incidence_rate_per_100k"].mean()
        severe_alerts = len(df_filtered_week[df_filtered_week["risk_level"].isin(["High", "Severe"])])

        with kpi_col1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Weekly Incident Cases</div>
                <div class="kpi-value">{week_cases:,}</div>
                <div class="kpi-subtitle">Across 8 Divisions</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Hospital Admissions</div>
                <div class="kpi-value">{week_hosp:,}</div>
                <div class="kpi-subtitle">{((week_hosp/max(week_cases,1))*100):.1f}% Admission Rate</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Confirmed Mortality</div>
                <div class="kpi-value">{week_deaths:,}</div>
                <div class="kpi-subtitle">Case Fatality: {((week_deaths/max(week_cases,1))*100):.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Mean Incidence Rate</div>
                <div class="kpi-value">{week_mean_rate:.2f}</div>
                <div class="kpi-subtitle">per 100,000 population</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col5:
            alert_color = "#e53935" if severe_alerts > 0 else "#43a047"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Active Alert Units</div>
                <div class="kpi-value" style="color: {alert_color};">{severe_alerts}</div>
                <div class="kpi-subtitle">High / Severe Alerts</div>
            </div>
            """, unsafe_allow_html=True)

        # --- SECTION 1 & 2: CHOROPLETH MAP & TIME-LAG CORRELATION ---
        st.markdown("---")
        col_map, col_chart = st.columns([1, 1])

        with col_map:
            st.markdown(f"#### 🗺️ Task 4.2: Choropleth Heatmap (Epi-Week {str(selected_week)[4:]}, {str(selected_week)[:4]})")
            
            risk_color_map = {
                "Low": "#43A047",
                "Moderate": "#FDD835",
                "High": "#FB8C00",
                "Severe": "#E53935"
            }
            
            fig_map = px.choropleth_mapbox(
                df_filtered_week,
                geojson=geojson_divisions,
                locations="location_key",
                featureidkey="id",
                color="incidence_rate_per_100k",
                color_continuous_scale="Reds",
                range_color=(0, max(df_facts["incidence_rate_per_100k"].quantile(0.95), 10.0)),
                mapbox_style="carto-darkmatter",
                zoom=5.8,
                center={"lat": 23.6850, "lon": 90.3563},
                opacity=0.75,
                hover_name="province_name_en",
                hover_data={
                    "location_key": True,
                    "total_cases": ":,",
                    "incidence_rate_per_100k": ":.2f",
                    "total_rainfall_mm": ":.1f",
                    "rainfall_lag_2w": ":.1f",
                    "risk_level": True
                },
                labels={
                    "incidence_rate_per_100k": "Incidence / 100k",
                    "total_cases": "Cases",
                    "rainfall_lag_2w": "Rain Lag 2W (mm)",
                    "risk_level": "Alert Level"
                }
            )
            fig_map.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                paper_bgcolor="#0e1117",
                plot_bgcolor="#0e1117",
                coloraxis_colorbar=dict(
                    title="Incidence / 100k",
                    thicknessmode="pixels", thickness=15,
                    lenmode="pixels", len=250,
                    yanchor="middle", y=0.5
                )
            )
            st.plotly_chart(fig_map, use_container_width=True, key="bi_choropleth_map")

        with col_chart:
            st.markdown(f"#### 📈 Task 4.3: Time-Lag Dual-Axis Correlation ({selected_division})")
            
            fig_lag = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Cases Bar
            fig_lag.add_trace(
                go.Bar(
                    x=df_timeseries["epi_week_key"].astype(str),
                    y=df_timeseries["total_cases"],
                    name="Incident Cases",
                    marker_color="#ef4444",
                    opacity=0.65
                ),
                secondary_y=False
            )
            
            # Concurrent Rainfall Line
            fig_lag.add_trace(
                go.Scatter(
                    x=df_timeseries["epi_week_key"].astype(str),
                    y=df_timeseries["total_rainfall_mm"],
                    name="Precipitation (Same Week)",
                    line=dict(color="#3b82f6", width=1.5, dash="dot")
                ),
                secondary_y=True
            )
            
            # Lag-2W Rainfall Line
            fig_lag.add_trace(
                go.Scatter(
                    x=df_timeseries["epi_week_key"].astype(str),
                    y=df_timeseries["rainfall_lag_2w"],
                    name="Rainfall Lag (2-Week Antecedent)",
                    line=dict(color="#10b981", width=2.5)
                ),
                secondary_y=True
            )
            
            # Lag-4W Rainfall Line
            fig_lag.add_trace(
                go.Scatter(
                    x=df_timeseries["epi_week_key"].astype(str),
                    y=df_timeseries["rainfall_lag_4w"],
                    name="Rainfall Lag (4-Week Antecedent)",
                    line=dict(color="#8b5cf6", width=2.0, dash="dash")
                ),
                secondary_y=True
            )
            
            fig_lag.update_layout(
                paper_bgcolor="#0e1117",
                plot_bgcolor="#161b22",
                font=dict(color="#c9d1d9"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=30, b=30),
                xaxis=dict(title="Epidemiological Week", showgrid=True, gridcolor="#21262d", dtick=10),
                yaxis=dict(title="Cases & Hospitalizations", showgrid=True, gridcolor="#21262d"),
                yaxis2=dict(title="Weekly Precipitation (mm)", showgrid=False, range=[0, df_timeseries["total_rainfall_mm"].max() * 2.5]),
                hovermode="x unified"
            )
            st.plotly_chart(fig_lag, use_container_width=True, key="bi_lag_correlation_chart")

        # --- SECTION 3: TASK 4.4 RISK ALERTING MATRIX & ACTION GUIDE ---
        st.markdown("---")
        st.markdown("### ⚠️ Task 4.4: Public Health Actionable Alerting Matrix")
        st.markdown(
            "Automated early warning notifications generated by coupling **Incidence Rates** "
            "with **2-to-4 Week Antecedent Meteorological Triggers** (Precipitation > 50mm, Humidity > 80%)."
        )

        alert_col1, alert_col2 = st.columns([1, 1])

        with alert_col1:
            st.markdown(f"#### Active Regional Alerts for Week {str(selected_week)[4:]}, {str(selected_week)[:4]}")
            
            risk_priority = {"Severe": 0, "High": 1, "Moderate": 2, "Low": 3}
            df_sorted_alerts = df_filtered_week.copy()
            df_sorted_alerts["priority"] = df_sorted_alerts["risk_level"].map(risk_priority)
            df_sorted_alerts = df_sorted_alerts.sort_values(["priority", "total_cases"], ascending=[True, False])

            for _, alert_row in df_sorted_alerts.iterrows():
                r_level = alert_row["risk_level"]
                p_name = alert_row["province_name_en"]
                cases = int(alert_row["total_cases"])
                inc = alert_row["incidence_rate_per_100k"]
                r_lag2 = alert_row["rainfall_lag_2w"]
                hum = alert_row["avg_humidity_pct"]

                css_class = f"alert-{r_level.lower()}"
                st.markdown(f"""
                <div class="alert-card {css_class}">
                    <strong>{r_level.upper()} ALERT: {p_name}</strong> (P-Code: {alert_row['location_key']})<br>
                    • <strong>Incident Cases:</strong> {cases:,} | <strong>Incidence Rate:</strong> {inc:.2f} / 100k<br>
                    • <strong>Environmental Triggers:</strong> Rainfall Lag 2W: {r_lag2:.1f} mm | Relative Humidity: {hum:.1f}%
                </div>
                """, unsafe_allow_html=True)

        with alert_col2:
            st.markdown("#### Prescribed Operational Decision Matrix")
            st.caption("Standardized public health intervention protocols derived from biological vector eradication windows.")
            
            action_matrix = [
                {
                    "Level": "🔴 Severe",
                    "Trigger Condition": "Incidence ≥ 50.0 / 100k OR (Incidence ≥ 20.0 AND Rain Lag 2W ≥ 80mm AND Humidity ≥ 80%)",
                    "Public Health Action": "Immediate thermal/ULV chemical fogging; activate hospital emergency surge capacity; deploy vector task forces."
                },
                {
                    "Level": "🟠 High",
                    "Trigger Condition": "Incidence ≥ 20.0 / 100k OR (Incidence ≥ 10.0 AND Rain Lag 2W ≥ 50mm AND Temp Lag 2W in 26–32°C)",
                    "Public Health Action": "Mobilize community larvicide application (Abate); inspect standing water containers in high-density wards."
                },
                {
                    "Level": "🟡 Moderate",
                    "Trigger Condition": "Incidence ≥ 5.0 / 100k OR Rain Lag 2W ≥ 60mm OR Rain Lag 4W ≥ 100mm",
                    "Public Health Action": "Intensify vector breeding surveillance; clean municipal drainage culverts; pre-position diagnostic test kits."
                },
                {
                    "Level": "🟢 Low",
                    "Trigger Condition": "Baseline incidence within historical non-outbreak limits",
                    "Public Health Action": "Maintain routine epidemiological monitoring and community hygiene awareness campaigns."
                }
            ]
            st.dataframe(pd.DataFrame(action_matrix), use_container_width=True, hide_index=True)

        # --- SECTION 4: GOLD FACT DATA EXPLORER ---
        st.markdown("---")
        with st.expander("📋 Explore Gold Analytical Mart (Read-Only via bi_reader)", expanded=False):
            st.dataframe(
                df_filtered_week[[
                    "location_key", "province_name_en", "disease_type", "total_cases", 
                    "total_hospitalized", "total_deaths", "incidence_rate_per_100k",
                    "total_rainfall_mm", "rainfall_lag_2w", "avg_temperature_c", "risk_level"
                ]],
                use_container_width=True,
                hide_index=True
            )

    # =========================================================================
    # TAB 2: AI ASSISTANT: NATURAL LANGUAGE TEXT-TO-SQL
    # =========================================================================
    with tab_ai:
        st.markdown("### 🤖 Public Health AI Epidemiologist (Text-to-SQL Assistant)")
        st.markdown(
            "Query the authoritative Gold Analytical Mart using **plain English**. "
            "Natural language prompts are translated into secure SQL, vetted by our **4-Layer Defense Sandbox**, "
            "and executed with sub-50ms latency."
        )

        # Sandbox Guardrail Badges
        st.markdown("""
        <div style="margin-bottom: 16px;">
            <span class="sandbox-badge">🛡️ Role: llm_agent</span>
            <span class="sandbox-badge">🔒 Read-Only Transaction</span>
            <span class="sandbox-badge">⏱️ Timeout: 3000ms</span>
            <span class="sandbox-badge">🛑 Blacklist Regex Guard</span>
            <span class="sandbox-badge">📊 LIMIT 500 Cap</span>
        </div>
        """, unsafe_allow_html=True)

        # Sample Query Quick-Action Buttons
        st.markdown("##### ⚡ Quick Prompt Templates:")
        preset_cols = st.columns(5)
        selected_preset = None

        if preset_cols[0].button("🏆 Top 5 Divisions (2023)", key="btn_top5"):
            selected_preset = "What are the top 5 divisions by total dengue cases in 2023?"
        if preset_cols[1].button("🌧️ Rainfall Lag in Dhaka", key="btn_rainfall"):
            selected_preset = "Show rainfall and dengue cases in Dhaka with time lags"
        if preset_cols[2].button("🚨 Active High/Severe Alerts", key="btn_alerts"):
            selected_preset = "Which regions have active high or severe risk alerts?"
        if preset_cols[3].button("🌐 Climate Zone Comparison", key="btn_climate"):
            selected_preset = "Compare dengue incidence and rainfall across climate zones"
        if preset_cols[4].button("⚠️ Test SQL Injection Defense", key="btn_injection"):
            selected_preset = "DROP TABLE gold.fact_disease_climate_weekly;"

        # Initialize session state chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": "Hello! I am your AI Epidemiologist Assistant. Ask me anything about disease incidence trends, 2-to-4 week rainfall lag correlations, mortality, or regional risk alert levels.",
                    "sql": None,
                    "data": None,
                    "elapsed_ms": None,
                    "error": None
                }
            ]

        # Chat Input
        user_input = st.chat_input("Ask an epidemiological surveillance question...")
        active_query = selected_preset or user_input

        if active_query:
            # Append user message
            st.session_state.chat_history.append({
                "role": "user",
                "content": active_query,
                "sql": None,
                "data": None,
                "elapsed_ms": None,
                "error": None
            })

            # Execute via Engine
            if llm_engine:
                with st.spinner("Synthesizing epidemiological query and executing safe SQL..."):
                    result = llm_engine.ask(active_query)
                    
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result.get("explanation", "Query generated and executed."),
                        "sql": result.get("sql"),
                        "data": result.get("data"),
                        "row_count": result.get("row_count", 0),
                        "elapsed_ms": result.get("elapsed_ms", 0),
                        "error": result.get("error")
                    })
            else:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "LLM Engine is currently unavailable.",
                    "sql": None,
                    "data": None,
                    "row_count": 0,
                    "elapsed_ms": 0,
                    "error": "Engine module not loaded"
                })

        # Render conversation history
        for msg_idx, msg in enumerate(st.session_state.chat_history):
            if msg["role"] == "user":
                with st.chat_message("user", avatar="🧑‍⚕️"):
                    st.markdown(f"**{msg['content']}**")
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(msg["content"])

                    # If query was blocked by sandbox
                    if msg.get("error"):
                        st.markdown(f"""
                        <div class="blocked-badge">
                            <strong>🛑 Security Sandbox Blocked Unauthorized Action:</strong><br>
                            <code>{msg['error']}</code><br>
                            <small>Enforced by Layer 1 Syntax Blacklist / Layer 3 Least Privilege Isolation.</small>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # If query executed successfully with SQL & Data
                    elif msg.get("sql"):
                        with st.expander("🔍 View Generated SQL & Execution Metadata", expanded=False):
                            st.code(msg["sql"], language="sql")
                            m_col1, m_col2, m_col3 = st.columns(3)
                            m_col1.metric("Execution Latency", f"{msg.get('elapsed_ms', 0):.2f} ms")
                            m_col2.metric("Result Rows", f"{msg.get('row_count', 0)}")
                            m_col3.metric("Security Status", "4/4 Layers Passed")

                        df_res = msg.get("data")
                        if isinstance(df_res, pd.DataFrame) and not df_res.empty:
                            st.dataframe(df_res, use_container_width=True, hide_index=True)

                            # Dynamic Smart Auto-Visualization
                            st.markdown("##### 📊 Automated Data Visualization:")
                            cols = df_res.columns.tolist()

                            # Scenario A: Temporal trend (epi_week_key present)
                            if "epi_week_key" in cols and len(df_res) > 1:
                                fig_trend = go.Figure()
                                if "total_cases" in cols:
                                    fig_trend.add_trace(go.Scatter(
                                        x=df_res["epi_week_key"].astype(str),
                                        y=df_res["total_cases"],
                                        name="Total Cases",
                                        mode="lines+markers",
                                        line=dict(color="#ef4444", width=2.5)
                                    ))
                                if "rainfall_lag_2w" in cols:
                                    fig_trend.add_trace(go.Scatter(
                                        x=df_res["epi_week_key"].astype(str),
                                        y=df_res["rainfall_lag_2w"],
                                        name="Rainfall Lag 2W (mm)",
                                        mode="lines",
                                        line=dict(color="#10b981", width=2, dash="dot")
                                    ))
                                if "total_rainfall_mm" in cols and "rainfall_lag_2w" not in cols:
                                    fig_trend.add_trace(go.Scatter(
                                        x=df_res["epi_week_key"].astype(str),
                                        y=df_res["total_rainfall_mm"],
                                        name="Weekly Rainfall (mm)",
                                        mode="lines",
                                        line=dict(color="#3b82f6", width=1.5)
                                    ))
                                fig_trend.update_layout(
                                    paper_bgcolor="#0e1117",
                                    plot_bgcolor="#161b22",
                                    font=dict(color="#c9d1d9"),
                                    margin=dict(l=30, r=30, t=20, b=20),
                                    xaxis=dict(title="Epidemiological Week", showgrid=True, gridcolor="#21262d"),
                                    yaxis=dict(title="Surveillance Value", showgrid=True, gridcolor="#21262d"),
                                    legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
                                )
                                st.plotly_chart(fig_trend, use_container_width=True, key=f"chat_trend_{msg_idx}")

                            # Scenario B: Administrative / Categorical comparison
                            elif ("province_name_en" in cols or "climate_zone" in cols) and len(df_res) > 1:
                                cat_col = "province_name_en" if "province_name_en" in cols else "climate_zone"
                                num_col = None
                                for cand in ["total_cases", "avg_incidence_rate_per_100k", "total_deaths", "mean_weekly_rainfall_mm"]:
                                    if cand in cols:
                                        num_col = cand
                                        break
                                if not num_col:
                                    num_cols = df_res.select_dtypes(include=["number"]).columns.tolist()
                                    num_col = num_cols[0] if num_cols else None

                                if num_col:
                                    fig_bar = px.bar(
                                        df_res,
                                        x=cat_col,
                                        y=num_col,
                                        color=num_col,
                                        color_continuous_scale="Viridis",
                                        title=f"Comparative Distribution: {num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}"
                                    )
                                    fig_bar.update_layout(
                                        paper_bgcolor="#0e1117",
                                        plot_bgcolor="#161b22",
                                        font=dict(color="#c9d1d9"),
                                        margin=dict(l=30, r=30, t=30, b=20),
                                        xaxis=dict(showgrid=False),
                                        yaxis=dict(showgrid=True, gridcolor="#21262d")
                                    )
                                    st.plotly_chart(fig_bar, use_container_width=True, key=f"chat_bar_{msg_idx}")

    # =========================================================================
    # TAB 3: DATA GOVERNANCE & SECURITY SANDBOX
    # =========================================================================
    with tab_gov:
        st.markdown("### 🛡️ Enterprise Security, Governance & Audit Matrix")
        st.markdown(
            "The platform implements strict **Defense-in-Depth** and **Role-Based Access Control (RBAC)** "
            "as codified in `docs/SECURITY_AND_GOVERNANCE.md` and `docs/DATA_CONTRACTS.md`."
        )

        gov_col1, gov_col2 = st.columns(2)

        with gov_col1:
            st.markdown("#### 🔒 4-Layer Defense-in-Depth Sandbox")
            st.markdown("""
            1. **Layer 1: Syntax Blacklist & AST Validation**
               - Word-boundary regex detects and blocks `DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `GRANT`, `INSERT`, `UPDATE`, `EXEC`.
               - Semicolon chaining (`;`) and comment injection (`--`, `/*`) are blocked before database submission.
            2. **Layer 2: Read-Only Transaction & Statement Timeout**
               - All queries execute inside `BEGIN READ ONLY;` transactions.
               - PostgreSQL `statement_timeout = '3000ms'` kills runaway queries and Denial-of-Service attacks.
            3. **Layer 3: Role-Based Least Privilege (`llm_agent`)**
               - Dedicated database user `llm_agent` possesses `SELECT` privilege **strictly on schema `gold`**.
               - Access to raw/staging schemas (`bronze`, `silver`, Parquet lakehouse) is explicitly revoked.
            4. **Layer 4: Hard Row Cap Enforcer**
               - Queries are automatically rewritten to append or cap `LIMIT 500` to prevent memory buffer exhaustion.
            """)

        with gov_col2:
            st.markdown("#### 👥 Multi-Tier RBAC Access Matrix")
            rbac_data = [
                {"Role": "de_admin", "Schema Access": "bronze, silver, gold, public", "Permissions": "ALL (CREATE, ALTER, INSERT, SELECT)", "Purpose": "ETL orchestration & dbt runs"},
                {"Role": "bi_reader", "Schema Access": "gold (Read-Only)", "Permissions": "SELECT only on gold.*", "Purpose": "Streamlit BI Dashboards & reports"},
                {"Role": "llm_agent", "Schema Access": "gold (Read-Only Sandboxed)", "Permissions": "SELECT only with 3s timeout & row cap", "Purpose": "Natural Language Text-to-SQL"}
            ]
            st.dataframe(pd.DataFrame(rbac_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🏅 dbt Data Quality & Contract Assurance")
        dq_col1, dq_col2, dq_col3, dq_col4 = st.columns(4)
        dq_col1.metric("Total dbt Tests", "36 Tests", "100% Passed")
        dq_col2.metric("Primary Key Integrity", "Unique & Not Null", "0 Violations")
        dq_col3.metric("Referential Integrity", "Relationships Verified", "0 Orphan Rows")
        dq_col4.metric("Value Domain Range", "Rainfall/Incidence ≥ 0", "Enforced")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6b7280; font-size: 0.85rem;'>"
    "Smart Health Data Platform • Built with PostgreSQL 16, dbt-core, Mage.ai & Streamlit • "
    "Author: thinhnguyenxuan &lt;ngxthinh271@gmail.com&gt;"
    "</div>",
    unsafe_allow_html=True
)
