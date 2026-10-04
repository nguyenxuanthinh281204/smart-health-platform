"""
==============================================================================
SMART HEALTH DATA PLATFORM - INTERACTIVE EPIDEMIOLOGICAL BI DASHBOARD
==============================================================================
Role: Serving Layer & Visual Analytics for Public Health Surveillance
Connects strictly via 'bi_reader' role per docs/SECURITY_AND_GOVERNANCE.md.
Implements:
  - Task 4.1: Gold Layer connection via bi_reader
  - Task 4.2: Interactive Epidemiological Choropleth Heatmap
  - Task 4.3: Time-Lag Dual-Axis Correlation Visualizations (2W/4W Lags)
  - Task 4.4: Real-time Rule-based Risk Alerting Matrix & Action Guide

Conforms strictly to docs/DATA_CONTRACTS.md and docs/DOMAIN_RULES_AND_METRICS.md.
==============================================================================
"""

import os
import json
import logging
from datetime import datetime
import pandas as pd
import psycopg2
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Page configuration
st.set_page_config(
    page_title="Smart Health: Epidemic & Climate Surveillance",
    page_icon="🦟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics and responsiveness
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .kpi-card {
        background: linear-gradient(135deg, #1e222d 0%, #262c3a 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #363d4e;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        text-align: center;
        margin-bottom: 12px;
    }
    .kpi-title { font-size: 0.85rem; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
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
    "time-lag feature engineering (2–4 week incubation windows), and vector-borne outbreak alert matrices."
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
        # Compute national weighted incidence rate
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
        
        # Color mapping by risk level
        risk_color_map = {
            "Low": "#43A047",       # Green
            "Moderate": "#FDD835",  # Yellow
            "High": "#FB8C00",      # Orange
            "Severe": "#E53935"      # Red
        }
        
        fig_map = px.choropleth_mapbox(
            df_filtered_week,
            geojson=geojson_divisions,
            locations="location_key",
            color="risk_level",
            color_discrete_map=risk_color_map,
            featureidkey="id",
            center={"lat": 23.6850, "lon": 90.3563},
            mapbox_style="carto-darkmatter",
            zoom=5.8,
            hover_name="province_name_en",
            hover_data={
                "location_key": True,
                "total_cases": ":,",
                "incidence_rate_per_100k": ":.2f",
                "total_rainfall_mm": ":.1f mm",
                "risk_level": True
            },
            labels={
                "risk_level": "Risk Level",
                "incidence_rate_per_100k": "Incidence / 100k",
                "total_cases": "New Cases"
            }
        )
        fig_map.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            paper_bgcolor="#0e1117",
            plot_bgcolor="#0e1117",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with col_chart:
        st.markdown(f"#### 📈 Task 4.3: Time-Lag Correlation ({selected_division})")
        st.caption("Visualizing the 2–4 week lag between peak rainfall events and subsequent dengue case surges.")

        fig_lag = make_subplots(specs=[[{"secondary_y": True}]])

        # Trace 1: Weekly Rainfall (Bar Chart on Secondary Axis)
        fig_lag.add_trace(
            go.Bar(
                x=df_timeseries["epi_week_key"].astype(str),
                y=df_timeseries["total_rainfall_mm"],
                name="Rainfall (mm)",
                marker_color="rgba(33, 150, 243, 0.4)",
                hoverinfo="x+y"
            ),
            secondary_y=True,
        )

        # Trace 2: 2-Week Lagged Rainfall (Dotted line on Secondary Axis)
        fig_lag.add_trace(
            go.Scatter(
                x=df_timeseries["epi_week_key"].astype(str),
                y=df_timeseries["rainfall_lag_2w"],
                name="Rainfall Lag 2W (mm)",
                line=dict(color="#64b5f6", width=2, dash="dot"),
                hoverinfo="x+y"
            ),
            secondary_y=True,
        )

        # Trace 3: Weekly New Cases (Solid Line on Primary Axis)
        fig_lag.add_trace(
            go.Scatter(
                x=df_timeseries["epi_week_key"].astype(str),
                y=df_timeseries["total_cases"],
                name="Incident Cases",
                line=dict(color="#ef5350", width=3),
                mode="lines+markers",
                marker=dict(size=4),
                hoverinfo="x+y"
            ),
            secondary_y=False,
        )

        # Trace 4: Hospital Admissions
        fig_lag.add_trace(
            go.Scatter(
                x=df_timeseries["epi_week_key"].astype(str),
                y=df_timeseries["total_hospitalized"],
                name="Hospital Admissions",
                line=dict(color="#ffa726", width=2, dash="dash"),
                hoverinfo="x+y"
            ),
            secondary_y=False,
        )

        fig_lag.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0e1117",
            plot_bgcolor="#161b22",
            height=450,
            margin={"r": 20, "t": 20, "l": 20, "b": 20},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, title="Epi-Week Key (YYYYWW)", nticks=15),
            yaxis=dict(title="Cases & Hospitalizations", showgrid=True, gridcolor="#21262d"),
            yaxis2=dict(title="Weekly Precipitation (mm)", showgrid=False, range=[0, df_timeseries["total_rainfall_mm"].max() * 2.5]),
            hovermode="x unified"
        )
        st.plotly_chart(fig_lag, use_container_width=True)

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
        
        # Sort divisions by risk severity
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

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6b7280; font-size: 0.85rem;'>"
    "Smart Health Data Platform • Built with PostgreSQL 16, dbt-core, Mage.ai & Streamlit • "
    "Principal Architect: Lead Data Engineer & AI Specialist"
    "</div>",
    unsafe_allow_html=True
)
