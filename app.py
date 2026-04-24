import streamlit as st
import pandas as pd
import plotly.express as px
import os
import utils
import styles

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(layout="wide")

# =====================================================
# DATA SETTINGS & URL LOGIC
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
MAP_ADM1_FILE = os.path.join(BASE_DIR, "pak_admbnda_adm1_wfp_20220909.shp")
MAP_ADM2_FILE = os.path.join(BASE_DIR, "pak_admbnda_adm2_wfp_20220909.shp")
SUMMARY_FILE = os.path.join(BASE_DIR, "summary_stats.xlsx")

params = st.query_params
selected_icm = params.get("icm")
if isinstance(selected_icm, list): selected_icm = selected_icm[0]
if not selected_icm:
    st.error("No dashboard selected (use ?icm=filename.csv in URL)")
    st.stop()

file_path = os.path.join(DATA_FOLDER, selected_icm.strip())

# =====================================================
# LOAD DATA
# =====================================================
adm1_gdf, adm2_gdf = utils.load_and_prepare_maps(MAP_ADM1_FILE, MAP_ADM2_FILE)
df = utils.preprocess_main_df(utils.load_data(file_path))
summary_df = utils.preprocess_summary_df(utils.load_summary(SUMMARY_FILE))
icm_clean = utils.detect_icm_title(df)

english_q = df["English Question"].dropna().iloc[0] if "English Question" in df.columns else ""
urdu_q = df["Urdu Question"].dropna().iloc[0] if "Urdu Question" in df.columns else ""

# =====================================================
# HEADER
# =====================================================
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Nastaliq+Urdu&display=swap" rel="stylesheet">
<h2 style="margin-bottom:8px; font-family:'Inter',sans-serif; font-weight:600;">{icm_clean} - Interactive Dashboard</h2>
<div style="margin-bottom:5px; font-size:20px; font-family:'Times New Roman',serif; color:#222; line-height:1.5;">{english_q}</div>
<div style="font-size:18px; font-family:'Noto Nastaliq Urdu',serif; direction:rtl; text-align:right; margin-bottom:10px; line-height:1.8;">{urdu_q}</div>
<hr style="margin-top:10px;">
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR FILTERS (FIXED LOGIC)
# =====================================================
st.sidebar.header("Filters")

FILTER_CONFIG = [
    ("zPR", "Province"), ("Division_Display", "Division"), ("District", "District"),
    ("d1_gender", "Gender"), ("d2_age", "Age"), ("d3_education", "Education"),
    ("d6_religion", "Religion"), ("d5_language", "Language"), ("Year", "Year"),
    ("TVS", "TVS (Ask Count)")
]

# Initialize filter state if not present
if "filters" not in st.session_state:
    st.session_state["filters"] = {col: [] for col, _ in FILTER_CONFIG}

# 👉 FIX: Sync session state keys with the filters dictionary at the START of the run
# This ensures that when a user unselects something, ALL widgets see the change immediately.
for col, _ in FILTER_CONFIG:
    key = f"f_{col}"
    if key in st.session_state:
        st.session_state["filters"][col] = st.session_state[key]

filters = st.session_state["filters"]

def apply_filters_local(dataframe, filters_dict, exclude=None):
    temp = dataframe
    for col, selected in filters_dict.items():
        if col == exclude: continue
        if selected and col in temp.columns:
            temp = temp[temp[col].isin(selected)]
    return temp

# Render filters
for col, label in FILTER_CONFIG:
    if col not in df.columns: continue
    
    # Calculate options based on the CURRENT synced state of other filters
    temp_df = apply_filters_local(df, filters, exclude=col)
    options = sorted(temp_df[col].dropna().unique().tolist())
    
    # Standard multiselect - key handles the persistence
    st.sidebar.multiselect(
        f"{label} ({len(options)})", 
        options=options, 
        key=f"f_{col}"
    )

# Final filtered data
filtered_df = apply_filters_local(df, filters)

filtered_summary_df = summary_df.copy()
if "Division_Display" in filtered_df.columns and "Divisions of Pakistan" in summary_df.columns:
    sel_divs = filtered_df["Division_Display"].dropna().unique().tolist()
    filtered_summary_df = summary_df[summary_df["Divisions of Pakistan"].isin(sel_divs)]

# =====================================================
# DASHBOARD SECTIONS
# =====================================================

# 1. Survey Summary Table
st.markdown("### Survey Summary")
final_df = utils.build_survey_summary_table(filtered_df)
if final_df is not None:
    st.dataframe(final_df.style.apply(lambda x: ["background-color: #f4f0ec; font-weight: bold; text-align:center" if x.name == "Total" else "text-align:center" for _ in x], axis=0), use_container_width=True)

# 2. Socio Economic Profile Cards
st.subheader("Socio Economic Profile (SEP)")
metrics = [
    ("Total Population", "Total Population", "sum", "number"),
    ("Land Area", "Land area (sq. km)", "sum", "number"),
    ("Housing Units", "Total Housing Units", "sum", "number"),
    ("GNI", "Total Annual Income / Gross National Income (GNI)", "sum", "number"),
    ("HH Size", "Average Household Size", "mean", "number"),
    ("Monthly Income", "Average Monthly Household Income", "mean", "number"),
    ("Divisions", "Divisions of Pakistan", "nunique", "count"),
    ("Districts", "No. of Districts", "sum", "count"),
    ("Tehsils", "No. of Tehsils", "sum", "count"),
    ("Union Councils", "No. of Union Council", "sum", "count"),
    ("Constituencies", "No. of Constituencies", "sum", "count"),
]

def format_val(val, vtype):
    if val is None: return "N/A"
    if vtype == "number":
        if val >= 1e9: return f"{val/1e9:.1f}B"
        if val >= 1e6: return f"{val/1e6:.1f}M"
        return f"{val:,.0f}" if val >= 1000 else f"{val:.2f}"
    return f"{int(val):,}"

for i in range(0, len(metrics), 6):
    cols = st.columns(6)
    for j, (lab, col, agg, vtype) in enumerate(metrics[i:i+6]):
        val = utils.get_summary_value(filtered_summary_df, col, agg) if agg != "nunique" else filtered_summary_df[col].nunique()
        with cols[j]:
            st.markdown(f'<div style="background-color:#f7f7f7; padding:10px; border-radius:6px; height:70px; display:flex; flex-direction:column; justify-content:center; margin-bottom:8px; border:1px solid #eee;"><div style="font-size:12px; color:#666;">{lab}</div><div style="font-size:15px; font-weight:600;">{format_val(val, vtype)}</div></div>', unsafe_allow_html=True)

# 3. Crosstab & Map
table_map = {
    "Province-wise Results": "zPR", "Division-wise Results": "Division_Display", "District-wise Results": "District",
    "Gender-wise Results": "d1_gender", "Age-wise Results": "d2_age", "Education-wise Results": "d3_education",
    "Religion-wise Results": "d6_religion", "Language-wise Results": "d5_language"
}
table_choice = st.selectbox("Choose table to display", list(table_map.keys()))
row_col = table_map[table_choice]
selected_table = utils.build_weighted_crosstab(filtered_df, row_col)
if selected_table is not None:
    st.dataframe(selected_table, use_container_width=True)

col_chart, col_map = st.columns([3, 2])
with col_chart:
    # 👈 Hovering removed and size reduced inside this function (see utils.py)
    chart_fig = utils.make_stacked_crosstab_chart(selected_table, table_choice)
    if chart_fig is not None: st.plotly_chart(chart_fig, use_container_width=True, key=f"chart_{table_choice}")

with col_map:
    is_div = "Division" in table_choice
    geo_col = "ADM2_EN" if is_div else "ADM1_EN"
    base_gdf = adm2_gdf if is_div else adm1_gdf
    pivot_num = utils.build_weighted_crosstab(filtered_df, row_col, as_string=False)
    if pivot_num is not None:
        top_opts = pivot_num.columns[:4].tolist()
        gdf = utils.build_map_dataframe(base_gdf, pivot_num, geo_col, "Division" if is_div else "Province")
        if gdf is not None:
            fig = px.choropleth(gdf, geojson=utils.get_geojson(gdf), locations=geo_col, featureidkey=f"properties.{geo_col}", 
                                color="Color_Category", color_discrete_map=styles.get_province_colors(), hover_name=geo_col, hover_data=top_opts)
            fig.update_traces(hovertemplate="<b>%{hovertext}</b><br><br>" + "<br>".join([f"{col}: %{{customdata[{i}]:.1f}}%" for i, col in enumerate(top_opts)]))
            fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", lataxis_range=[30, 47], lonaxis_range=[60, 78])
            fig.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"))
            st.plotly_chart(fig, use_container_width=True)

# 4. Charts Row
def mk_weighted_bar(col, title):
    if col not in filtered_df.columns: return
    d = filtered_df.groupby(col)["Weight"].sum().reset_index()
    d["Percent"] = (d["Weight"]/d["Weight"].sum()*100).round(1)
    fig = px.bar(d, x=col, y="Percent", text="Percent", title=title, color=col, color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(texttemplate='%{text:.1f}%', textposition="outside", hovertemplate="%{x}: %{y:.1f}%")
    fig.update_layout(height=360, hovermode="x unified", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)
with c1: mk_weighted_bar("Options", "Response Distribution")
with c2: mk_weighted_bar("zPR", "Province Breakdown")
c3, c4 = st.columns(2)
with c3: mk_weighted_bar("d1_gender", "Gender Split")
with c4: mk_weighted_bar("ur_n", "Urban vs Rural")

# =====================================================
# YEAR TREND
# =====================================================
st.markdown("### Year Trend")
pivot_pct = utils.get_year_weighted_table(filtered_df)
if pivot_pct is not None:
    plot_df = pivot_pct.reset_index().melt(id_vars="Year", var_name="Series", value_name="Percent")
    
    # 👉 FIX: Ensure all years are shown as categorical labels
    plot_df["Year"] = plot_df["Year"].astype(str)
    
    fig = px.line(plot_df, x="Year", y="Percent", color="Series", markers=True)
    fig.update_layout(hovermode="x unified", hoverlabel=dict(bgcolor="white"))
    fig.update_xaxes(type='category', categoryorder='category ascending')
    fig.update_traces(hovertemplate="%{fullData.name}: %{y:.1f}%")
    st.plotly_chart(fig, use_container_width=True)

    # Trend Table
    total_row = (filtered_df.groupby("Options")["Weight"].sum() / filtered_df["Weight"].sum() * 100).round(1).to_frame().T
    total_row.index = ["Total"]
    final_table = pd.concat([total_row, pivot_pct])
    def color_sc(val): return f"background-color: rgb({int(240 - (val * 1.5))}, {int(240 - (val * 1.5))}, 255); color: black" if not pd.isna(val) else ""
    st.dataframe(final_table.style.format("{:.1f}%").applymap(color_sc).apply(lambda r: ["background-color: #f8f8ff; font-weight: bold"] * len(r) if r.name == "Total" else [""] * len(r), axis=1), use_container_width=True)
