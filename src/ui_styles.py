import streamlit as st
import os
import base64
from src.config import PALETTE

def get_base64_of_bin_file(bin_file):
    if not os.path.exists(bin_file): return ""
    with open(bin_file, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def inject_styles():
    t = PALETTE
    
    st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;800&display=swap');
    
    :root {{
        --primary: {t['primary']};
        --primary-container: {t['primary_container']};
        --background: {t['background']};
        --on-surface: {t['on_surface']};
        --glass-bg: {t['glass_bg']};
    }}

    .stApp {{
        background: linear-gradient(135deg, {t['background']} 0%, #ffffff 100%) !important;
        font-family: 'Manrope', sans-serif;
    }}

    .main {{
        background: transparent !important;
    }}

    h1, h2, h3 {{
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
        color: {t['on_surface']};
        letter-spacing: -0.02em;
    }}

    h1 {{ font-size: 2.8rem !important; margin-bottom: 0px; }}

    /* Glassmorphism Cards */
    .cockpit-card {{
        background: {t['glass_bg']};
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        padding: 1.5rem;
        border-radius: 40px; /* Full rounding */
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: {t['shadow']};
        margin-bottom: 1.5rem;
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}

    .cockpit-card:hover {{
        transform: translateY(-4px);
        background: rgba(255, 255, 255, 0.8);
    }}

    .kpi-label {{
        font-size: 0.7rem;
        font-weight: 600;
        color: {t['on_surface_variant']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }}

    .kpi-value {{
        font-family: 'Manrope', sans-serif;
        font-size: 2.4rem;
        font-weight: 800;
        color: {t['on_surface']};
        line-height: 1.1;
    }}

    .kpi-unit {{
        font-size: 0.8rem;
        color: {t['primary']};
        font-weight: 600;
        margin-left: 6px;
    }}

    /* Buttons & Interactions */
    div.stButton > button {{
        background: linear-gradient(135deg, {t['primary']} 0%, {t['secondary']} 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 102, 102, 0.2) !important;
    }}

    div.stButton > button:hover {{
        transform: scale(1.02) !important;
        box-shadow: 0 6px 20px rgba(0, 102, 102, 0.3) !important;
    }}

    /* Small buttons for sidebar */
    section[data-testid="stSidebar"] div.stButton > button {{
        padding: 0.25rem 0.5rem !important;
        font-size: 0.65rem !important;
        min-height: 26px !important;
        border-radius: 8px !important;
        margin-bottom: 0px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        display: block !important;
        width: 100% !important;
    }}

    /* Global Roundedness */
    .stSelectbox, .stMultiSelect, .stSlider, .stTextInput, .stTextArea {{
        border-radius: 20px !important;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        background: {t['surface_low']};
        border-radius: 30px;
        padding: 5px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: 25px;
        padding: 10px 20px;
        font-weight: 600;
    }}

    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        background: {t['primary_container']};
        padding: 10px 20px;
        border-radius: 50px;
        font-size: 0.7rem;
        font-weight: 800;
        color: {t['primary']};
        box-shadow: {t['shadow']};
    }}

    .pulse-dot {{
        width: 10px;
        height: 10px;
        background: {t['primary']};
        border-radius: 50%;
        animation: pulse-teal 1.5s infinite;
    }}

    @keyframes pulse-teal {{
        0% {{ transform: scale(0.9); opacity: 0.4; box-shadow: 0 0 0 0 rgba(0, 102, 102, 0.4); }}
        70% {{ transform: scale(1.1); opacity: 1; box-shadow: 0 0 0 10px rgba(0, 102, 102, 0); }}
        100% {{ transform: scale(0.9); opacity: 0.4; box-shadow: 0 0 0 0 rgba(0, 102, 102, 0); }}
    }}

    /* Schematic Box */
    .top-schematic {{
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
        padding: 2.5rem 1.5rem;
        border-radius: 32px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        margin-bottom: 2.5rem;
        box-shadow: {t['shadow']};
    }}
</style>
    """, unsafe_allow_html=True)
    
    return get_base64_of_bin_file("assets/logo.png")
