---
description: Modern UI/UX Design System and Aesthetics Directive for Smart Health Platform
globs: ["bi_dashboard/**/*", "**/*streamlit*", "**/*ui*"]
alwaysApply: true
---

# MODERN HEALTH DATA PLATFORM - UI/UX DESIGN SYSTEM DIRECTIVE

> **Mandate for AI Coding Agents:**  
> When constructing frontend applications, Streamlit dashboards, or BI visual components, NEVER produce generic, unstyled interfaces (e.g., standard browser tables or default gray Streamlit metrics). Always apply this **Executive Command Center Design System** to create a stunning, high-impact aesthetic.

---

## 1. COLOR PALETTE & DESIGN TOKENS

```css
:root {
  /* Background Layers */
  --bg-primary: #0B0F19;       /* Deep obsidian canvas */
  --bg-secondary: #111827;     /* Elevated panel surface */
  --bg-card: rgba(17, 24, 39, 0.75); /* Glassmorphism card fill */
  --border-glass: rgba(255, 255, 255, 0.08); /* Subtle card border */

  /* Primary Brand Accents */
  --accent-cyan: #06B6D4;      /* Data flow & water/climate accent */
  --accent-indigo: #6366F1;    /* Deep analytical highlight */
  --accent-purple: #8B5CF6;    /* Secondary intelligence accent */

  /* Public Health Epidemic Severity Signals */
  --status-severe: #EF4444;    /* Red Alert: Severe Outbreak */
  --status-high: #F97316;      /* Orange: Emerging Surge */
  --status-moderate: #FBBF24;  /* Yellow: Early Climate Indicator Warning */
  --status-low: #10B981;       /* Emerald Green: Baseline / Safe */

  /* Text & Typography */
  --text-main: #F9FAFB;
  --text-muted: #9CA3AF;
  --text-dim: #6B7280;
}
```

---

## 2. STREAMLIT INJECTABLE CSS (GLASSMORPHISM & GLOW EFFECTS)

Every Streamlit view in `bi_dashboard/app.py` must inject the following design styling:

```python
import streamlit as st

def apply_modern_command_center_theme():
    st.markdown("""
    <style>
        /* Import Premium Modern Typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, sans-serif;
            color: #F9FAFB;
        }

        h1, h2, h3, .metric-title {
            font-family: 'Outfit', sans-serif !important;
            letter-spacing: -0.02em;
        }

        /* Glassmorphism Metric Cards */
        .glass-card {
            background: rgba(17, 24, 39, 0.7);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .glass-card:hover {
            transform: translateY(-2px);
            border-color: rgba(6, 182, 212, 0.35);
        }

        /* Severe Alert Pulse Animation */
        .badge-severe {
            background: rgba(239, 68, 68, 0.15);
            color: #EF4444;
            border: 1px solid rgba(239, 68, 68, 0.4);
            border-radius: 8px;
            padding: 4px 10px;
            font-weight: 600;
            display: inline-block;
            box-shadow: 0 0 12px rgba(239, 68, 68, 0.25);
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #0B0F19;
        }
        ::-webkit-scrollbar-thumb {
            background: #1F2937;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #06B6D4;
        }
    </style>
    """, unsafe_allow_html=True)
```

---

## 3. GEOSPATIAL VISUALIZATION (PYDECK 3D & MAPBOX)

For the Epidemiological Heatmap, use `pydeck` with dark-mode vector basemaps and dynamic extrusion:

```python
import pydeck as pdk

def build_3d_epidemic_choropleth(geojson_data, current_epi_week):
    """
    Renders 3D extruded provincial polygons where height represents Incidence Rate 
    and color signifies stratified risk level.
    """
    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson_data,
        opacity=0.85,
        stroked=True,
        filled=True,
        extruded=True,
        wireframe=True,
        get_elevation="properties.elevation_height",  # Scaled by Incidence Rate
        elevation_scale=50,
        get_fill_color="properties.fill_color_rgb",  # [R, G, B, 200]
        get_line_color=[255, 255, 255, 60],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True
    )

    view_state = pdk.ViewState(
        latitude=23.6850,
        longitude=90.3563,
        zoom=6.5,
        pitch=45,
        bearing=10
    )

    tooltip = {
        "html": """
        <div style="background-color: #111827; color: white; padding: 10px; border-radius: 8px; border: 1px solid #374151; font-family: Inter;">
            <b style="font-size: 14px; color: #06B6D4;">{province_name}</b><br/>
            <span>Incidence Rate: <b>{incidence_rate_per_100k}</b> / 100k</span><br/>
            <span>Rainfall (2W Lag): <b>{rainfall_lag_2w} mm</b></span><br/>
            <span>Risk Status: <b style="color: {risk_color_hex};">{risk_level}</b></span>
        </div>
        """,
        "style": {"zIndex": "1000"}
    }

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v11",
        tooltip=tooltip
    )
```

---

## 4. DUAL-AXIS TIME-LAG CORRELATION CHARTS (PLOTLY DARK GLASS)

To illustrate the biological time-lag relationship between rainfall and hospitalization surges:

```python
import plotly.graph_objects as go

def plot_time_lag_correlation(df_weekly):
    fig = go.Figure()

    # Left Y-Axis: Cumulative Precipitation (mm) - Cyan Bar Chart
    fig.add_trace(go.Bar(
        x=df_weekly['epi_week_label'],
        y=df_weekly['total_rainfall_mm'],
        name="Rainfall (mm)",
        marker=dict(color='rgba(6, 182, 212, 0.45)', line=dict(color='#06B6D4', width=1.5)),
        yaxis="y1"
    ))

    # Right Y-Axis: Dengue Hospitalizations - Crimson Line Chart with Glowing Shadow
    fig.add_trace(go.Scatter(
        x=df_weekly['epi_week_label'],
        y=df_weekly['total_cases'],
        name="Dengue Incident Cases",
        mode='lines+markers',
        line=dict(color='#EF4444', width=3, shape='spline'),
        marker=dict(size=6, color='#EF4444', line=dict(width=2, color='#FFFFFF')),
        yaxis="y2"
    ))

    # Dark Glass Layout Configuration
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(11, 15, 25, 0.0)',
        plot_bgcolor='rgba(17, 24, 39, 0.5)',
        font=dict(family="Inter", color="#9CA3AF"),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(
            title=dict(text="Cumulative Rainfall (mm)", font=dict(color="#06B6D4")),
            gridcolor="rgba(255, 255, 255, 0.05)"
        ),
        yaxis2=dict(
            title=dict(text="Weekly Case Counts", font=dict(color="#EF4444")),
            overlaying="y",
            side="right",
            showgrid=False
        )
    )
    return fig
```

---

## 5. CONVERSATIONAL AI CHAT INTERFACE (TEXT-TO-SQL)

When building the LLM Assistant view:
1. Display conversation messages using `st.chat_message("user")` and `st.chat_message("assistant", avatar="🩺")`.
2. Wrap generated SQL queries inside an expandable glass container (`st.expander("🔍 View Generated SQL Query", expanded=False)`).
3. Provide one-click suggestion chips (e.g., *"Show top 5 provinces with highest 2-week rain lag"*, *"Calculate current dengue incidence rate in Dhaka"*).
