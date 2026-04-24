import streamlit as st
import pandas as pd
import geopandas as gpd
import re
import os
import plotly.express as px

@st.cache_resource
def load_and_prepare_maps(adm1_path, adm2_path):
    adm1 = gpd.read_file(adm1_path)
    adm2 = gpd.read_file(adm2_path)
    # Simplify geometry for performance while keeping boundaries accurate
    adm1["geometry"] = adm1["geometry"].simplify(0.01, preserve_topology=True)
    adm2["geometry"] = adm2["geometry"].simplify(0.01, preserve_topology=True)
    return adm1, adm2

@st.cache_data
def load_data(path):
    return pd.read_csv(path, encoding="utf-8-sig")

@st.cache_data
def load_summary(path):
    return pd.read_excel(path)

@st.cache_data
def preprocess_main_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    text_cols = [
        "zPR", "Division_Display", "District", "d1_gender", "d2_age",
        "d3_education", "d6_religion", "d5_language", "ur_n",
        "Options", "Year", "TVS"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df.loc[df[col].str.lower().isin(["nan", "none"]), col] = pd.NA
    if "Weight" in df.columns:
        df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    return df

@st.cache_data
def preprocess_summary_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "Divisions of Pakistan" in df.columns:
        df["Divisions of Pakistan"] = df["Divisions of Pakistan"].astype(str).str.strip()
        df.loc[df["Divisions of Pakistan"].str.lower().isin(["nan", "none"]), "Divisions of Pakistan"] = pd.NA
    return df

@st.cache_data
def detect_icm_title(df: pd.DataFrame) -> str:
    possible_cols = [col for col in df.columns if "ICM" in str(col).upper()]
    icm_col = possible_cols[0] if possible_cols else df.columns[-1]
    icm_series = df[icm_col].dropna().astype(str)
    raw_icm = icm_series.iloc[0] if not icm_series.empty else ""
    match = re.search(r"ICM[_\s]?Q?\d+", raw_icm, re.IGNORECASE)
    if match:
        return match.group(0).upper().replace("_", " ")
    return raw_icm

def get_summary_value(dataframe, column_name, agg="sum"):
    if column_name not in dataframe.columns:
        return None
    numeric_series = pd.to_numeric(dataframe[column_name], errors="coerce").dropna()
    if numeric_series.empty:
        return None
    if agg == "sum":
        return numeric_series.sum()
    elif agg == "mean":
        return numeric_series.mean()
    return None

@st.cache_data
def build_survey_summary_table(filtered_df: pd.DataFrame):
    if not all(col in filtered_df.columns for col in ["Options", "Weight"]):
        return None
    temp = filtered_df.dropna(subset=["Options", "Weight"]).copy()
    if temp.empty: return None
    temp["Options"] = temp["Options"].astype(str).str.strip()
    counts = temp["Options"].value_counts()
    total_count = counts.sum()
    counts_df = counts.to_frame().T
    counts_df.index = ["Count"]
    grouped = temp.groupby("Options", observed=False)["Weight"].sum()
    weighted_pct = (grouped / grouped.sum() * 100).round(1)
    weighted_df = weighted_pct.to_frame().T
    weighted_df.index = ["Weighted %"]
    final_df = pd.concat([counts_df, weighted_df], axis=0).fillna(0)
    final_df["Total"] = [total_count, 100]
    cols = list(final_df.columns)
    dk_cols = [c for c in cols if ("DK" in str(c) or "NR" in str(c)) and c != "Total"]
    normal_cols = [c for c in cols if c not in dk_cols and c != "Total"]
    final_df = final_df[normal_cols + dk_cols + ["Total"]]
    
    final_df.loc["Count"] = pd.to_numeric(final_df.loc["Count"], errors="coerce").fillna(0).round(0).apply(lambda x: f"{int(x):,}")
    final_df.loc["Weighted %"] = pd.to_numeric(final_df.loc["Weighted %"], errors="coerce").fillna(0).round(1).apply(
        lambda x: f"{int(x)}%" if float(x) == 100 else f"{float(x):.1f}%"
    )
    return final_df

@st.cache_data
def build_weighted_crosstab(dataframe: pd.DataFrame, row_col: str, col_col="Options", weight_col="Weight", as_string=True):
    required_cols = [row_col, col_col, weight_col]
    if not all(col in dataframe.columns for col in required_cols): return None
    temp_df = dataframe.dropna(subset=required_cols).copy()
    if temp_df.empty: return None
    grouped = temp_df.groupby([row_col, col_col], observed=False)[weight_col].sum().reset_index()
    pivot = grouped.pivot(index=row_col, columns=col_col, values=weight_col).fillna(0)
    pivot_pct = (pivot.div(pivot.sum(axis=1), axis=0) * 100).round(1)
    cols = list(pivot_pct.columns)
    dk_cols = [c for c in cols if "DK" in str(c) or "NR" in str(c)]
    normal_cols = [c for c in cols if c not in dk_cols]
    pivot_pct = pivot_pct[normal_cols + dk_cols]
    if as_string:
        return pivot_pct.astype(str) + "%"
    return pivot_pct

@st.cache_data
def get_year_weighted_table(filtered_df: pd.DataFrame):
    if not all(col in filtered_df.columns for col in ["Year", "Options", "Weight"]): return None
    temp_df = filtered_df.dropna(subset=["Year", "Options", "Weight"]).copy()
    if temp_df.empty: return None
    grouped = temp_df.groupby(["Year", "Options"], observed=False)["Weight"].sum().reset_index()
    pivot = grouped.pivot(index="Year", columns="Options", values="Weight").fillna(0)
    pivot_pct = (pivot.div(pivot.sum(axis=1), axis=0) * 100).round(1)
    
    cols = list(pivot_pct.columns)
    dk_cols = [c for c in cols if "DK" in str(c) or "NR" in str(c)]
    normal_cols = [c for c in cols if c not in dk_cols]
    pivot_pct = pivot_pct[normal_cols + dk_cols]
    
    return pivot_pct

def make_stacked_crosstab_chart(table_df, title):
    if table_df is None or table_df.empty: return None
    df_numeric = table_df.replace('%', '', regex=True).astype(float).reset_index()
    x_col = df_numeric.columns[0]
    plot_df = df_numeric.melt(id_vars=x_col, var_name="Options", value_name="Percent")
    
    fig = px.bar(plot_df, x=x_col, y="Percent", color="Options", barmode="stack",
                 color_discrete_sequence=px.colors.qualitative.Bold, title=title)
    fig.update_traces(
        texttemplate="%{y:.0f}%", 
        textposition="inside", 
        insidetextanchor="middle",
        hoverinfo='none',      # 👈 Remove hovering
        hovertemplate=None     # 👈 Remove hovering
    )
    fig.update_layout(
        hovermode=False,       # 👈 Disable hover mode
        height=450,            # 👈 Reduced height to match map
        margin=dict(l=20, r=20, t=40, b=10), # 👈 Reduced bottom margin
        xaxis_title="", 
        yaxis_title="Weighted %", 
        legend_title=""
    )
    return fig

@st.cache_data
def build_map_dataframe(_base_gdf: gpd.GeoDataFrame, pivot_numeric: pd.DataFrame, geo_col: str, map_level: str):
    if pivot_numeric is None or pivot_numeric.empty: return None
    gdf = _base_gdf.copy()
    gdf[geo_col] = gdf[geo_col].astype(str).str.strip()
    pivot_numeric = pivot_numeric.copy()
    pivot_numeric.index = pivot_numeric.index.astype(str).str.strip()
    name_fix = {"KP": "Khyber Pakhtunkhwa", "KPK": "Khyber Pakhtunkhwa", "Baluchistan": "Balochistan"}
    pivot_numeric.index = pivot_numeric.index.map(lambda x: name_fix.get(x, x))
    merged = gdf.merge(pivot_numeric, left_on=geo_col, right_index=True, how="left").fillna(0)
    if map_level == "Province":
        merged["Province_Name"] = merged[geo_col]
        active_regions = pivot_numeric.index.tolist()
    else:
        merged["Province_Name"] = merged["ADM1_EN"]
        active_regions = pivot_numeric.index.tolist()
    merged["is_active"] = merged[geo_col].isin(active_regions)
    merged["Color_Category"] = merged.apply(lambda row: row["Province_Name"] if row["is_active"] else "Not in Survey", axis=1)
    return merged

def get_geojson(gdf):
    return gdf.__geo_interface__
