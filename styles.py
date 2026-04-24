import streamlit as st

def apply_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Nastaliq+Urdu&display=swap');
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] > div { padding-top: 10px !important; }
    div[data-testid="stSidebar"] .stMultiSelect { margin-bottom: 5px !important; }
    
    /* Global font */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Custom card styling */
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-value { font-size: 20px; font-weight: 600; color: #1a73e8; }
    .metric-label { font-size: 12px; color: #5f6368; text-transform: uppercase; letter-spacing: 0.5px; }
    </style>
    """, unsafe_allow_html=True)

def render_header(title, english_q, urdu_q):
    st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <h1 style="font-weight: 700; color: #1a73e8; margin-bottom: 5px;">{title}</h1>
        <div style="font-size: 18px; color: #3c4043; margin-bottom: 10px; line-height: 1.4;">{english_q}</div>
        <div style="font-family: 'Noto Nastaliq Urdu', serif; direction: rtl; text-align: right; font-size: 20px; color: #202124; line-height: 1.8;">{urdu_q}</div>
    </div>
    <hr style="border: 0; height: 1px; background: #e0e0e0; margin-bottom: 25px;">
    """, unsafe_allow_html=True)

def render_summary_card(label, value):
    st.markdown(f"""
    <div style="background-color:#f7f7f7; padding:10px; border-radius:6px; height:75px; 
                display:flex; flex-direction:column; justify-content:center; margin-bottom:8px; border: 1px solid #eee;">
        <div style="font-size:11px; color:#666; text-transform: uppercase;">{label}</div>
        <div style="font-size:16px; font-weight:600; color: #333;">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def get_province_colors():
    return {
        "Punjab": "#1f77b4",
        "Sindh": "#2ca02c",
        "Khyber Pakhtunkhwa": "#ff7f0e",
        "Balochistan": "#d62728",
        "Islamabad": "#9467bd",
        "Not in Survey": "#d3d3d3"
    }
