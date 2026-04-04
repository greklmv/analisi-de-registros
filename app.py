import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
from src.data_processing import (
    load_data, segment_by_blocks, calculate_kpis, get_suggested_mapping, 
    load_mappings, get_sheet_names, get_minute_summary, 
    get_all_stations_flat, get_event_based_summary, load_stations, get_closest_station
)  # type: ignore
from src.report_generator import generate_word_report  # type: ignore
import io
import time
import numpy as np
from datetime import datetime
import os
import base64

# --- CONFIGURACIÓ DE LA PÀGINA ---
st.set_page_config(
    page_title="FGC | Analista OTMR Pro v4.96",
    page_icon="🚆",
    layout="wide",
)

# --- CONFIGURACIÓ DE TEMA I ESTILS DINÀMICS ---
if 'theme_mode' not in st.session_state: st.session_state.theme_mode = "CLAR (Swiss)"

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# LOGO BASE64 (per al header)
logo_base64 = ""
if os.path.exists("assets/logo.png"):
    logo_base64 = get_base64_of_bin_file("assets/logo.png")

# --- DEFINICIÓ DE TEMES ---
THEMES = {
    "CLAR (Swiss)": {
        "primary": "#0052A3", "secondary": "#FF5722", "background": "#f8fafc", "surface": "#f8fafc",
        "surface_container": "#ffffff", "on_surface": "#0f172a", "on_surface_variant": "#475569",
        "plotly_template": "plotly_white", "shadow": "0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)",
        "card_bg": "#ffffff", "glass_blur": "0px", "border": "#e2e8f0"
    }
}

t = THEMES[st.session_state.theme_mode]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;800&display=swap');

    :root {{
        --primary: {t['primary']};
        --secondary: {t['secondary']};
        --background: {t['background']};
        --surface: {t['surface']};
        --surface-container: {t['surface_container']};
        --on-surface: {t['on_surface']};
        --on-surface-variant: {t['on_surface_variant']};
        --outline-variant: rgba(0, 210, 255, 0.15);
        --error: #ff716c;
    }}

    .main {{ background-color: var(--background) !important; color: var(--on-surface); font-family: 'Inter', sans-serif; }}
    [data-testid="stAppViewContainer"] {{ background-color: var(--background); }}
    [data-testid="stHeader"] {{ background: rgba(255, 255, 255, 0.8) !important; backdrop-filter: blur(8px); }}
    [data-testid="stSidebar"] {{ 
        background-color: #ffffff !important; 
        border-right: 1px solid #e2e8f0 !important; 
    }}
    
    /* Millora de llegibilitat específica per al Sidebar */
    [data-testid="stSidebar"] h3 {{
        color: var(--primary) !important;
        font-family: 'Manrope', sans-serif !important;
        font-size: 1.1rem !important;
        margin-top: 2rem !important;
    }}
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {{
        color: var(--on-surface) !important;
        font-family: 'Inter', sans-serif !important;
    }}
    /* Estilització d'expanders al sidebar per llegibilitat */
    [data-testid="stSidebar"] .st-emotion-cache-p4m61c {{ 
        color: var(--on-surface) !important;
        font-weight: 700 !important;
    }}

    /* Amagar el límit de 200MB i traduir el File Uploader al català */
    [data-testid="stFileUploader"] small {{ display: none !important; }}
    [data-testid="stFileUploaderDropzoneInstructions"] {{ display: none; }}
    [data-testid="stFileUploaderDropzoneInstructions"]::after {{ 
        content: "Arrossegueu el fitxer aquí";
        display: block; 
        font-size: 0.9rem;
        color: var(--on-surface);
        padding: 10px;
    }}

    /* Correcció definitiva de traducció del botó 'Browse files' al català */
    /* Només estilitzem el botó principal de la dropzone per evitar botons dobles */
    [data-testid="stFileUploaderDropzone"] button {{
        font-size: 0 !important;
        color: transparent !important;
        line-height: 0 !important;
        position: relative !important;
        background-color: var(--primary) !important;
        min-width: 180px !important;
        min-height: 45px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 10px !important;
        transition: all 0.3s ease !important;
    }}
    [data-testid="stFileUploaderDropzone"] button::after {{
        content: "ADJUNTA ARXIU";
        color: #000 !important;
        font-family: 'Manrope', sans-serif !important;
        font-weight: 800 !important;
        font-size: 0.85rem !important;
        line-height: normal !important;
        position: static !important;
        visibility: visible !important;
        letter-spacing: 0.05em;
    }}
    [data-testid="stFileUploader"] button:hover {{
        box-shadow: 0 0 20px var(--primary) !important;
        transform: scale(1.02) !important;
    }}

    [data-testid="stFileUploader"] {{
        background-color: rgba(255, 255, 255, 0.03) !important;
        border: 1px dashed var(--primary) !important;
        border-radius: 12px !important;
        padding: 5px !important;
    }}
    [data-testid="stFileUploader"] section {{
        background-color: transparent !important;
    }}
    [data-testid="stFileUploaderDropzone"] button {{
        background-color: var(--primary) !important;
        color: #000 !important;
    }}

    /* Estil per als Selectboxes */
    div[data-baseweb="select"] > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: var(--on-surface) !important;
        border-radius: 8px !important;
        border: 1px solid var(--outline-variant) !important;
    }}
    
    /* Estil per als Radio Buttons */
    [data-testid="stMarkdownContainer"] p {{ font-weight: 500; }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
        font-size: 0.9rem !important;
        color: var(--primary) !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}

    h1 {{ font-family: 'Manrope', sans-serif !important; font-weight: 800 !important; letter-spacing: -0.04em !important; color: var(--on-surface); font-size: 2.8rem !important; }}
    h2, h3, .stSubheader {{ font-family: 'Manrope', sans-serif !important; font-weight: 600 !important; color: var(--primary); text-transform: uppercase; }}

    .cockpit-card {{ 
        background: {t['card_bg']}; 
        backdrop-filter: blur({t['glass_blur']});
        padding: 1.5rem; 
        border-radius: 16px; 
        border: 1px solid {t['border']} !important; 
        box-shadow: {t['shadow']}; 
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); 
        margin-bottom: 1rem; 
        position: relative;
        overflow: hidden;
    }}
    .cockpit-card::before {{
        content: ""; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
        transition: 0.5s;
    }}
    .cockpit-card:hover::before {{ left: 100%; }}
    .cockpit-card:hover {{ transform: translateY(-5px) scale(1.01); border-color: var(--primary) !important; }}
    
    .kpi-label {{ font-family: 'Inter', sans-serif; font-weight: 700; font-size: 0.7rem; color: var(--on-surface-variant); text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 8px; }}
    .kpi-value {{ font-family: 'Manrope', sans-serif; font-size: 2.8rem; font-weight: 800; color: var(--on-surface); line-height: 1; letter-spacing: -0.02em; }}
    .kpi-unit {{ font-size: 0.8rem; font-weight: 600; color: var(--primary); margin-left: 8px; opacity: 0.8; }}
    
    .glass-panel {{ 
        background: {t['card_bg']}; 
        backdrop-filter: blur(40px); 
        border-radius: 32px; 
        padding: 4rem; 
        border: 1px solid {t['border']}; 
        box-shadow: {t['shadow']};
    }}

    .stButton>button {{ 
        background: linear-gradient(135deg, var(--primary), {"#00a2ff" if t['primary'] == "#00d2ff" else "#003b79"}) !important; 
        color: {"#002c38" if t['primary'] == "#00d2ff" else "#ffffff"} !important; 
        border-radius: 12px !important; border: none !important; 
        font-family: 'Manrope', sans-serif !important; font-weight: 800 !important; 
        text-transform: uppercase !important; padding: 0.8rem 2.5rem !important; 
        transition: all 0.3s ease !important; 
        letter-spacing: 0.1em !important;
        box-shadow: 0 4px 15px rgba(0, 210, 255, 0.2) !important;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 210, 255, 0.4) !important;
    }}

    /* Botons del sidebar més compactes */
    [data-testid="stSidebar"] .stButton>button {{
        padding: 0.4rem 1rem !important;
        font-size: 0.7rem !important;
        border-radius: 8px !important;
        letter-spacing: 0.05em !important;
    }}
    [data-testid="stSidebar"] .stButton>button:hover {{
        transform: translateY(-1px);
    }}

    .status-badge {{ 
        display: inline-flex; align-items: center; gap: 12px; 
        background: rgba(0, 210, 255, 0.08); padding: 10px 22px; 
        border-radius: 40px; font-size: 0.7rem; font-weight: 800; color: var(--primary);
        border: 1px solid rgba(0, 210, 255, 0.2);
        letter-spacing: 0.1em;
    }}
    .pulse-dot {{ width: 8px; height: 8px; background-color: var(--primary); border-radius: 50%; box-shadow: 0 0 15px var(--primary); animation: pulse 2s infinite; }}
    @keyframes pulse {{ 0% {{ transform: scale(0.9); opacity: 0.4; box-shadow: 0 0 0 0 rgba(0, 210, 255, 0.7); }} 70% {{ transform: scale(1.1); opacity: 1; box-shadow: 0 0 0 10px rgba(0, 210, 255, 0); }} 100% {{ transform: scale(0.9); opacity: 0.4; box-shadow: 0 0 0 0 rgba(0, 210, 255, 0); }} }}

    [data-testid="stSidebar"] img {{ filter: none; transition: all 0.5s ease; }}
    
    /* Animació de càrrega per a transicions */
    .stProgress > div > div > div > div {{ background-image: linear-gradient(90deg, var(--primary), var(--secondary)) !important; }}


    .top-schematic {{
        background: #ffffff !important;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        overflow-x: auto;
        width: 100%;
        display: block;
    }}
    .schematic-label {{ font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 600; fill: #64748b; }}
    .schematic-label-main {{ font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 800; fill: #1e293b; }}
    .schematic-node {{ fill: #ffffff; stroke: #94a3b8; stroke-width: 1.5; cursor: pointer; transition: all 0.2s; }}
    .schematic-node:hover {{ stroke: var(--primary); stroke-width: 3; fill: #f1f5f9; }}
    .schematic-node-pos {{ fill: var(--primary); stroke: #003b79; filter: drop-shadow(0 0 4px rgba(0,82,163,0.4)); cursor: pointer; }}
    .schematic-node-origin {{ fill: var(--secondary); stroke: #d84315; filter: drop-shadow(0 0 4px rgba(255,87,34,0.4)); cursor: pointer; }}
    .schematic-line {{ stroke: #cbd5e1; stroke-width: 2.5; fill: none; stroke-linecap: round; }}
    
    #MainMenu {{visibility: hidden;}} header {{visibility: hidden;}} footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)


def render_network_schematic(origin_id=None, pos_id=None):
    """Renderitza el mapa de vies tècnic (estil FGC Cockpit)"""
    import json
    # Utilitzem les funcions importades globalment
    network = load_stations()
    if not network: return

    # Paràmetres de dibuix
    W, H = 1500, 260
    X_START = 80
    Y_MAIN = 130
    SPACING = 55
    NODE_W, NODE_H = 10, 22
    
    svg = f"""
    <svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="background:#ffffff; border-radius:12px;">
        <style>
            .schematic-line {{ stroke: #cbd5e1; stroke-width: 2.5; fill: none; stroke-linecap: round; }}
            .schematic-node {{ fill: #ffffff; stroke: #94a3b8; stroke-width: 1.5; cursor: pointer; transition: all 0.2s; }}
            .schematic-node:hover {{ stroke: #0052A3; stroke-width: 3; fill: #f8fafc; }}
            .schematic-node-pos {{ fill: #0052A3; stroke: #003b79; filter: drop-shadow(0 0 4px rgba(0,82,163,0.4)); cursor: pointer; animation: pulse-blue 2s infinite; }}
            @keyframes pulse-blue {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} 100% {{ opacity: 1; }} }}
            .schematic-node-origin {{ fill: #FF5722; stroke: #d84315; filter: drop-shadow(0 0 4px rgba(255,87,34,0.4)); cursor: pointer; }}
            .schematic-label {{ font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 600; fill: #64748b; pointer-events: none; }}
            .schematic-label-main {{ font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 800; fill: #1e293b; pointer-events: none; }}
            .legend-text {{ font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 700; fill: #64748b; }}
            .reset-btn {{ fill: #f1f5f9; stroke: #cbd5e1; transition: all 0.2s; }}
            .reset-btn:hover {{ fill: #fee2e2; stroke: #ef4444; }}
            a {{ text-decoration: none; }}
        </style>
        
        <!-- Legend & Actions -->
        <g transform="translate(20, 20)">
            <rect x="0" y="0" width="10" height="10" rx="2" fill="#FF5722" />
            <text x="15" y="9" class="legend-text">ORIGEN SELECCIONAT</text>
            <rect x="150" y="0" width="10" height="10" rx="2" fill="#0052A3" />
            <text x="165" y="9" class="legend-text">POSICIÓ ACTUAL (DATA)</text>
            
            <a href="/?station_origin=RESET" target="_self">
                <rect x="330" y="-5" width="100" height="20" rx="10" class="reset-btn" />
                <text x="380" y="9" text-anchor="middle" class="legend-text" style="fill:#ef4444;">❌ RESET FILTRE</text>
            </a>
        </g>
    """
    
    def get_node_class(sid):
        if sid == pos_id: return "schematic-node-pos"
        if sid == origin_id: return "schematic-node-origin"
        return "schematic-node"

    # --- 1. TRONC COMÚ (PC -> SC) ---
    trunk = network.get("Tronc-Comu-PC-SC", {}).get("stations", [])
    x_pos = {}
    
    # Dibuixar línia principal
    svg += f'<line x1="{X_START}" y1="{Y_MAIN}" x2="{X_START + (len(trunk)+1)*SPACING}" y2="{Y_MAIN}" class="schematic-line" />'
    
    for i, station_item in enumerate(trunk):
        curr_x = X_START + i * SPACING
        x_pos[station_item['id']] = curr_x
        node_class = get_node_class(station_item['id'])
        
        # El node PC és més ample
        w = NODE_W * 2 if station_item['id'] == "PC" else NODE_W
        pk_abs = station_item.get('pk_abs', station_item['pk'])
        svg += f'<a href="/?station_origin={station_item["id"]}" target="_self" title="Seleccionar {station_item["name"]} (PK {pk_abs:.3f})">'
        svg += f'<rect x="{curr_x - w/2}" y="{Y_MAIN - NODE_H/2}" width="{w}" height="{NODE_H}" rx="3" class="{node_class}" />'
        svg += f'<text x="{curr_x}" y="{Y_MAIN + NODE_H + 15}" text-anchor="middle" class="schematic-label-main">{station_item["id"]}</text>'
        svg += '</a>'

    x_sc = x_pos.get("SC", X_START + (len(trunk)-1)*SPACING)
    
    # --- 2. RAMAL L7 (Surt de GR cap avall) ---
    x_gr = x_pos.get("GR", X_START + 2*SPACING)
    l7 = network.get("Ramal-L7", {}).get("stations", [])
    svg += f'<path d="M {x_gr} {Y_MAIN} L {x_gr+20} {Y_MAIN+60} L {x_gr + 20 + len(l7)*SPACING} {Y_MAIN+60}" class="schematic-line" />'
    for i, station_item in enumerate(l7):
        curr_x = x_gr + 40 + i * SPACING
        node_class = get_node_class(station_item['id'])
        pk_abs = station_item.get('pk_abs', station_item['pk'])
        svg += f'<a href="/?station_origin={station_item["id"]}" target="_self" title="Seleccionar {station_item["name"]} (PK {pk_abs:.3f})">'
        svg += f'<rect x="{curr_x - NODE_W/2}" y="{Y_MAIN + 60 - NODE_H/2}" width="{NODE_W}" height="{NODE_H}" rx="2" class="{node_class}" />'
        svg += f'<text x="{curr_x}" y="{Y_MAIN + 60 + NODE_H + 12}" text-anchor="middle" class="schematic-label">{station_item["id"]}</text>'
        svg += '</a>'

    # --- 3. RAMAL L12 (Surt de SR cap amunt) ---
    x_sr = x_pos.get("SR", X_START + 7*SPACING)
    l12 = network.get("Ramal-L12", {}).get("stations", [])
    svg += f'<path d="M {x_sr} {Y_MAIN} L {x_sr+20} {Y_MAIN-60} L {x_sr + 40 + SPACING} {Y_MAIN-60}" class="schematic-line" />'
    # Node RE
    curr_x_re = x_sr + 40
    node_class = get_node_class(l12[0]['id'])
    pk_abs = l12[0].get('pk_abs', l12[0]['pk'])
    svg += f'<a href="/?station_origin={l12[0]["id"]}" target="_self" title="Seleccionar {l12[0]["name"]} (PK {pk_abs:.3f})">'
    svg += f'<rect x="{curr_x_re - NODE_W/2}" y="{Y_MAIN - 60 - NODE_H/2}" width="{NODE_W}" height="{NODE_H}" rx="2" class="{node_class}" />'
    svg += f'<text x="{curr_x_re}" y="{Y_MAIN - 60 - NODE_H - 5}" text-anchor="middle" class="schematic-label">{l12[0]["id"]}</text>'
    svg += '</a>'
    # Text Dip.RE blue
    svg += f'<text x="{curr_x_re + 40}" y="{Y_MAIN - 60 - NODE_H - 10}" class="schematic-label" style="fill:#0052A3; font-weight:bold;">Dip.RE</text>'
    svg += f'<rect x="{curr_x_re + 35}" y="{Y_MAIN - 60 - NODE_H/2}" width="20" height="15" rx="3" fill="#ffffff" stroke="#cbd5e1" />'

    # --- 4. BIFURCACIÓ FINAL (SC -> S1/S2) ---
    # S1 (Terrassa) cap amunt
    s1 = network.get("Ramal-S1-Terrassa", {}).get("stations", [])
    svg += f'<path d="M {x_sc} {Y_MAIN} L {x_sc+30} {Y_MAIN-60} L {x_sc + 40 + len(s1)*SPACING} {Y_MAIN-60}" class="schematic-line" />'
    for i, station_item in enumerate(s1):
        curr_x = x_sc + 50 + i * SPACING
        node_class = get_node_class(station_item['id'])
        
        # Cas especial COR a Rubí
        if station_item['id'] == "RB":
            svg += f'<text x="{curr_x}" y="{Y_MAIN - 60 - NODE_H - 22}" text-anchor="middle" class="schematic-label" style="fill:#0052A3; font-weight:bold;">COR</text>'
            svg += f'<rect x="{curr_x - 10}" y="{Y_MAIN - 60 - NODE_H - 15}" width="20" height="12" rx="2" fill="#ffffff" stroke="#cbd5e1" />'
            
        pk_abs = station_item.get('pk_abs', station_item['pk'])
        svg += f'<a href="/?station_origin={station_item["id"]}" target="_self" title="Seleccionar {station_item["name"]} (PK {pk_abs:.3f})">'
        svg += f'<rect x="{curr_x - NODE_W/2}" y="{Y_MAIN - 60 - NODE_H/2}" width="{NODE_W}" height="{NODE_H}" rx="2" class="{node_class}" />'
        svg += f'<text x="{curr_x}" y="{Y_MAIN - 60 - NODE_H - 5}" text-anchor="middle" class="schematic-label">{station_item["id"]}</text>'
        svg += '</a>'
    svg += f'<text x="{x_sc + 60 + len(s1)*SPACING}" y="{Y_MAIN - 75}" class="schematic-label" style="fill:#0052A3; font-size:12px; font-weight:bold;">Can Roca</text>'

    # S2 (Sabadell) cap avall
    s2 = network.get("Ramal-S2-Sabadell", {}).get("stations", [])
    svg += f'<path d="M {x_sc} {Y_MAIN} L {x_sc+30} {Y_MAIN+60} L {x_sc + 40 + len(s2)*SPACING} {Y_MAIN+60}" class="schematic-line" />'
    for i, station_item in enumerate(s2):
        curr_x = x_sc + 50 + i * SPACING
        node_class = get_node_class(station_item['id'])
        pk_abs = station_item.get('pk_abs', station_item['pk'])
        svg += f'<a href="/?station_origin={station_item["id"]}" target="_self" title="Seleccionar {station_item["name"]} (PK {pk_abs:.3f})">'
        svg += f'<rect x="{curr_x - NODE_W/2}" y="{Y_MAIN + 60 - NODE_H/2}" width="{NODE_W}" height="{NODE_H}" rx="2" class="{node_class}" />'
        svg += f'<text x="{curr_x}" y="{Y_MAIN + 60 + NODE_H + 12}" text-anchor="middle" class="schematic-label">{station_item["id"]}</text>'
        svg += '</a>'
    svg += f'<text x="{x_sc + 60 + (len(s2)-1)*SPACING}" y="{Y_MAIN + 45}" class="schematic-label" style="fill:#0052A3; font-size:12px; font-weight:bold;">Ca N\'O</text>'

    svg += '</svg>'
    return svg

def main():
    # --- SYNC CLICS MAPA ---
    if "station_origin" in st.query_params:
        target_id = st.query_params["station_origin"]
        if target_id == "RESET":
            st.session_state.selected_st_ui = "Cap (Ús PK Absolut)"
        else:
            all_st = get_all_stations_flat()
            found = next((s for s in all_st if s["id"] == target_id), None)
            if found:
                st.session_state.selected_st_ui = found["display_name"]
        
        st.query_params.clear()
        st.rerun()

    # --- ESTAT DE L'APLICACIÓ ---
    if 'selected_vars' not in st.session_state: st.session_state.selected_vars = []
    if 'current_unit' not in st.session_state: st.session_state.current_unit = "UT 113-114"
    if 'processed_data' not in st.session_state: st.session_state.processed_data = None
    if 'last_loaded_key' not in st.session_state: st.session_state.last_loaded_key = None

    # --- HEADER ---
    st.markdown('<div style="padding-top: 1rem;"></div>', unsafe_allow_html=True)
    header_container = st.container()
    with header_container:
        h_col1, h_col2 = st.columns([0.75, 0.25])
        with h_col1:
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 20px;">
                    <img src="data:image/png;base64,{logo_base64}" width="100" style="border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); border: 2px solid #ffffff;">
                    <div>
                        <h1 style="margin: 0; padding: 0; line-height: 1.1;">ANALISTA OTMR <span style="color: {t['primary']}; opacity: 0.8;">PRO</span></h1>
                        <p style="margin: 0; color: {t['on_surface_variant']}; font-weight: 600; font-size: 0.8rem; letter-spacing: 0.1em; text-transform: uppercase;">
                            Ferrocarrils de la Generalitat de Catalunya • Xarxa de Telemetria
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with h_col2:
            st.markdown(f"""
                <div style="text-align: right; padding-top: 0.8rem;">
                    <div class="status-badge">
                        <div class="pulse-dot"></div> TELEMETRIA ACTIVA
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="margin-top: 1.5rem; margin-bottom: 2.5rem; border-bottom: 2px solid var(--outline-variant); opacity: 0.3;"></div>', unsafe_allow_html=True)

    # 0. Preparació de dades de context (Estacions i Filtre de Línia)
    all_st_flat = get_all_stations_flat()
    st_names = [s["display_name"] for s in all_st_flat]
    options_st = ["Cap (Ús PK Absolut)"] + st_names

    # Mapa de Seccions de Línia per a filtratge de dades (Garanteix que S1 no mostri estacions de S2)
    LINE_SECTIONS = {
        "S1 (Terrassa)": ["Tronc-Comu-PC-SC", "Ramal-S1-Terrassa"],
        "S2 (Sabadell)": ["Tronc-Comu-PC-SC", "Ramal-S2-Sabadell"],
        "L6 (Sarrià)": ["Tronc-Comu-PC-SC"],
        "L7 (Tibidabo)": ["Tronc-Comu-PC-SC", "Ramal-L7"],
        "L12 (R.Elisenda)": ["Tronc-Comu-PC-SC", "Ramal-L12"],
        "Totes": None
    }

    # --- CONFIGURACIÓ DE CONTEXT (DROPDOWNS) ---
    st.markdown("### 🗺️ Context de l'Anàlisi")
    ctx_c1, ctx_c2, ctx_c3 = st.columns([1, 1, 1.2])
    with ctx_c1:
        line_options = list(LINE_SECTIONS.keys())
        st.selectbox("🛤️ Línia d'Anàlisi:", options=line_options, key="active_line")
    
    with ctx_c2:
        direction_options = ["Ascendent", "Descendent"]
        sel_dir = st.selectbox("↕️ Sentit de la marxa:", options=direction_options, key="active_direction")
        is_ascendant = "Ascendent" in sel_dir
    
    current_line_filter = LINE_SECTIONS.get(st.session_state.get("active_line", "Totes"))
    
    with ctx_c3:
        # Sincronització de l'estat per evitar el bug de desselecció
        if "selected_st_ui" not in st.session_state or st.session_state.selected_st_ui not in options_st:
            st.session_state.selected_st_ui = "Cap (Ús PK Absolut)"
            
        sel_st_name = st.selectbox(
            "📍 Estació d'Origen (Calibratge PK):", 
            options=options_st,
            key="selected_st_ui"
        )

    # Càlcul del PK de referència base per al mapa i anàlisi
    selected_starting_pk = None
    origin_st_id = None
    if sel_st_name != "Cap (Ús PK Absolut)":
        sel_st_obj = next((s for s in all_st_flat if s["display_name"] == sel_st_name), None)
        if sel_st_obj:
            selected_starting_pk = float(sel_st_obj.get("pk_abs", sel_st_obj.get("pk", 0)))
            st.session_state.origin_st_info = sel_st_obj
            origin_st_id = sel_st_obj["id"]
    else:
        st.session_state.origin_st_info = None

    # --- MAPA TÈCNIC INTERACTIU (SEMPRE VISIBLE) ---
    current_st_id = None
    
    # Obtenir ID de posició actual si hi ha dades per mostrar on és el tren al mapa
    if st.session_state.get("processed_data") is not None:
        try:
            df_pos = st.session_state.processed_data
            km_col = st.session_state.get("km_col")
            if km_col and km_col in df_pos.columns:
                last_pk = df_pos[km_col].iloc[-1]
                s_data = load_stations()
                closest_str = get_closest_station(last_pk, s_data, line_filter=current_line_filter)
                if "(" in closest_str:
                    current_st_id = closest_str.split("(")[-1].split(")")[0]
        except: pass

    svg_code = render_network_schematic(origin_id=origin_st_id, pos_id=current_st_id)
    if svg_code:
        svg_code_clean = "".join([line.strip() for line in svg_code.split("\n")])
        st.markdown(f'<div class="top-schematic">{svg_code_clean}</div>', unsafe_allow_html=True)

    st.markdown('<div style="margin-bottom: 2rem;"></div>', unsafe_allow_html=True)

    # --- SIDEBAR ---
    st.sidebar.image("assets/logo.png", use_container_width=True)
    
    st.sidebar.markdown("---")

    st.sidebar.markdown("### 📁 Control de Registres")
    uploaded_file = st.sidebar.file_uploader("", type=["xlsx", "xls", "csv", "pdf"], label_visibility="collapsed")
    unit_model = st.sidebar.selectbox("Model d'Unitat de Tren:", options=["UT 113-114", "UT 112", "UT 115"], index=1 if st.session_state.current_unit == "UT 112" else 0)
    st.session_state.current_unit = unit_model
    
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    demo_mode = st.sidebar.toggle("Mode Demo (Simulació)", value=False)
    
    st.sidebar.markdown("### 🎯 Anàlisi Ràpid")
    
    def apply_rapid_vars(analysis_type):
        df = st.session_state.get("processed_data")
        if df is None:
            st.sidebar.warning("⚠️ Carrega dades abans.")
            return

        cols = df.columns.tolist()
        selected = []
        
        if analysis_type in ["estacio", "senyal"]:
            # Distància, Velocitat, Manipulador en FU, Bolet + ATP/ATO (Crític per context)
            for c in cols:
                cn = c.upper()
                # 1. Velocitat
                if any(k in cn for k in ["VELOCITAT", "VELOCIDAD", "AAA", "SPEED"]): 
                    selected.append(c)
                # 2. Distància
                if any(k in cn for k in ["DISTÀNCIA", "DISTANCIA", "KM", "PK", "DIST_"]): 
                    selected.append(c)
                # 3. Manipulador en FU (Fre d'Urgència)
                if any(k in cn for k in ["MANFU", "MANIPULADOR EN FU", "FRE D'URGÈNCIA", "FU MAN", "FRE_URG"]):
                    selected.append(c)
                # 4. Bolet (Seta / Polsador d'Urgència / Freno de Emergencia)
                if any(k in cn for k in ["BOLET", "SETA", "N-FE", "POLSADOR D'URGÈNCIA", "FREN_EMERG", "EMERGENCIA"]):
                    selected.append(c)
                # 5. Mode de Conducció (Nou requeriment per context d'ultrapassament)
                if any(k in cn for k in ["ATP", "ATO", "MODE", "MODO"]):
                    selected.append(c)
        
        elif analysis_type == "conduccio":
            # Mode ATP, Mode ATO
            for c in cols:
                cn = c.upper()
                if any(k in cn for k in ["ATP", "ATO", "MODE", "MODO"]):
                    selected.append(c)
        
        # Eliminar duplicats mantenint l'ordre
        st.session_state.selected_vars = list(dict.fromkeys(selected))
        st.rerun()

    if st.sidebar.button("🚉 Ultrapassament d'Estació", use_container_width=True):
        st.toast("🔍 Seleccionant variables d'estació...")
        apply_rapid_vars("estacio")
        
    if st.sidebar.button("🛑 Ultrapassament de Senyal", use_container_width=True):
        st.toast("⚠️ Seleccionant variables de senyal...")
        apply_rapid_vars("senyal")
        
    if st.sidebar.button("🎮 Mode de Conducció", use_container_width=True):
        st.toast("📑 Seleccionant variables de conducció...")
        apply_rapid_vars("conduccio")
    
    # Identificador únic per al fitxer (o mode demo)
    current_key = "DEMO" if demo_mode else (uploaded_file.name if uploaded_file else None)

    # Lògica de recuperació si el fitxer ha desaparegut del widget però el tenim en memòria (per reload de mapa)
    if current_key is None and st.session_state.get("processed_data") is not None:
        current_key = st.session_state.get("last_loaded_key")

    # --- LÒGICA DE PERSISTÈNCIA MAPA ---
    # Si tornem d'un clic de mapa (refresh complet del navegador), recuperem l'estat anterior
    if st.session_state.get("just_clicked_map", False) and current_key is None and st.session_state.get("processed_data") is not None:
        current_key = st.session_state.last_loaded_key
        st.session_state.just_clicked_map = False
    elif "just_clicked_map" in st.session_state:
        st.session_state.just_clicked_map = False # Reset seguretat

    # --- LÒGICA DE DESTRUCCIÓ/CONSTRUCCIÓ ---
    # Si el fitxer ha canviat realment, invalidem dades prèvies
    if current_key != st.session_state.last_loaded_key:
        st.session_state.processed_data = None
        st.session_state.last_loaded_key = current_key

    if current_key:
        if uploaded_file is None and not demo_mode and st.session_state.processed_data is not None:
            st.sidebar.info(f"✅ **MEMÒRIA ACTIVA:**\n{current_key}")
            st.sidebar.markdown("<small><i>(Pots canviar el fitxer adjuntant-ne un de nou)</i></small>", unsafe_allow_html=True)
            
        try:
            # Carregar dades NOMÉS si no estan ja al session_state
            if st.session_state.processed_data is None:
                with st.spinner("📦 Recuperant telemetria del xassís..."):
                    if demo_mode:
                        df = load_data("MOCK_FGC")
                    else:
                        sheet_name = 0
                        if uploaded_file.name.endswith(('.xlsx', '.xls')):
                            sheets = get_sheet_names(uploaded_file)
                            if len(sheets) > 1:
                                sheet_name = st.sidebar.selectbox("📋 Selecciona la Fulla de càlcul:", sheets)
                        df = load_data(uploaded_file, sheet_name=sheet_name)
                    st.session_state.processed_data = df
            
            df = st.session_state.processed_data
            all_cols = df.columns.tolist()
            
            # --- AUTO-DETECCIÓ PERSISTENT DE VARIABLES CRÍTIQUES ---
            if 'speed_col' not in st.session_state or st.session_state.speed_col not in all_cols:
                for col in all_cols:
                    if any(k in str(col).upper() for k in ['VELOCIDAD', 'SPEED', 'V_UT', 'VEL_', 'V_', 'KM/H', 'AAA']): 
                        st.session_state.speed_col = col; break
                else: st.session_state.speed_col = all_cols[min(1, len(all_cols)-1)]

            if 'km_col' not in st.session_state or st.session_state.km_col not in all_cols:
                for col in all_cols:
                    if any(k in str(col).upper() for k in ['DISTANCIA', 'KM', 'X_UT', 'DIST_']): 
                        st.session_state.km_col = col; break
                else: st.session_state.km_col = all_cols[min(2, len(all_cols)-1)]

            if 'time_col' not in st.session_state or st.session_state.time_col not in all_cols:
                for col in all_cols:
                    if any(k in str(col).upper() for k in ['HORA', 'TIME', 'SYSTEMTIME', 'FECHA', 'FECHA-HORA']): 
                        st.session_state.time_col = col; break
                else: st.session_state.time_col = all_cols[0]

            speed_col = st.session_state.speed_col
            km_col = st.session_state.km_col
            time_col = st.session_state.time_col

            # --- INTERVAL D'ANÀLISI I FILTRATGE ---
            st.markdown("### ⏲️ Interval d'Anàlisi")
            try:
                
                # Neteja de caràcters per a la Sèrie 112 (DD/MM/YY - HH:MM:SS)
                raw_t = df[time_col].astype(str).str.replace(' - ', ' ', regex=False)
                temp_ts = pd.to_datetime(raw_t, dayfirst=True, errors='coerce')
                
                min_t = temp_ts.min().time() if not temp_ts.isnull().all() else datetime.min.time()
                max_t = temp_ts.max().time() if not temp_ts.isnull().all() else datetime.max.time()
                
                f1, f2 = st.columns(2)
                start_time = f1.time_input("Inici d'anàlisi:", value=min_t)
                end_time = f2.time_input("Final d'anàlisi:", value=max_t)
                
                mask = (temp_ts.dt.time >= start_time) & (temp_ts.dt.time <= end_time)
                analysis_df = df.loc[mask].reset_index(drop=True)
            except Exception as e:
                st.warning(f"⚠️ Error en el format horari o estacions: {e}. Mostrant dades completes.")
                analysis_df = df
                selected_starting_pk = None

            # --- CÀLCUL DE KPIS (SEMPRE ACTIUS) ---
            if not analysis_df.empty:
                analysis_df[speed_col] = pd.to_numeric(analysis_df[speed_col], errors='coerce').fillna(0)
                analysis_df[km_col] = pd.to_numeric(analysis_df[km_col], errors='coerce').fillna(0)
                
                val_speed = f"{analysis_df[speed_col].max():.1f}"
                dist_raw = float(analysis_df[km_col].max() - analysis_df[km_col].min())
                val_dist_m = f"{abs(dist_raw) * 1000 if abs(dist_raw) < 150 else abs(dist_raw):,.0f}"
                first_ts = str(analysis_df[time_col].iloc[0])
                val_time = first_ts.split(" ")[-1][:8] if " " in first_ts else first_ts[:8]
            else:
                val_speed, val_dist_m, val_time = "0.0", "0", "--:--"

            st.subheader("🛰️ Monitoratge de KPIs")
            k_cols = st.columns(4) # Augmentem a 4 columnes per al Mode de Conducció
            with k_cols[0]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">🚀 Velocitat Màxima</div><div class="kpi-value">{val_speed}<span class="kpi-unit">KM/H</span></div></div>', unsafe_allow_html=True)
            with k_cols[1]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">📏 Distància Total</div><div class="kpi-value">{val_dist_m}<span class="kpi-unit">METRES</span></div></div>', unsafe_allow_html=True)
            with k_cols[2]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">📅 Timestamp Inici</div><div class="kpi-value">{val_time}<span class="kpi-unit">REF</span></div></div>', unsafe_allow_html=True)
            
            # --- KPI DE MODE DE CONDUCCIÓ ---
            conduction_mode = "Desconegut"
            atp_col = next((c for c in all_cols if "ATP" in str(c).upper()), None)
            ato_col = next((c for c in all_cols if "ATO" in str(c).upper()), None)
            if not analysis_df.empty and atp_col and ato_col:
                is_atp = (analysis_df[atp_col] == 1).sum()
                is_ato = (analysis_df[ato_col] == 1).sum()
                if is_atp > is_ato: conduction_mode = "⚙️ ATP"
                elif is_ato > is_atp: conduction_mode = "🤖 ATO"
            
            with k_cols[3]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">🕹️ Mode Predominant</div><div class="kpi-value">{conduction_mode}</div></div>', unsafe_allow_html=True)
            
            # --- MAPA TÈCNIC DE VIES ---
            current_st_id = None
            origin_st_id = None
            
            # 1. Obtenir ID d'origen des del selector
            current_sel = st.session_state.get("selected_st_ui", "Cap")
            if "(" in current_sel:
                origin_st_id = current_sel.split("(")[-1].split(")")[0]

            # 2. Obtenir ID de posició actual des de la telemetria
            if not analysis_df.empty:
                last_pk = analysis_df[km_col].iloc[-1]
                s_data = load_stations()
                closest_str = get_closest_station(last_pk, s_data, line_filter=current_line_filter)
                if "(" in closest_str:
                    current_st_id = closest_str.split("(")[-1].split(")")[0]
            
            # 3. Lògica per a variables automàtiques
            suggested_mapping = get_suggested_mapping(all_cols, unit_model=st.session_state.current_unit)
            if suggested_mapping and not st.session_state.selected_vars:
                with st.expander(f"✨ Protocol {st.session_state.current_unit} Detectat", expanded=True):
                    if st.button("🪄 Automatitzar Mapeig Suggerit"):
                        st.session_state.selected_vars = list(suggested_mapping.keys())
                        st.rerun()

            mappings = load_mappings()
            unit_vars = mappings.get(st.session_state.current_unit, {})
            all_options = list(unit_vars.keys()) + [c for c in all_cols if c not in unit_vars]
            
            def variable_formatter(opt):
                if opt in unit_vars: return f"{opt}: {unit_vars[opt]}"
                return opt

            # Inicialització i selecció de variables
            selected_vars = st.multiselect(
                "Variables actives (Telemetria):", 
                options=all_options, 
                key="selected_vars", 
                format_func=variable_formatter
            )

            # --- GRÀFIC TELEMÈTRIC COMPLEX ---
            st.subheader("📊 Cockpit d'Anàlisi de Senyals")
            
            from plotly.subplots import make_subplots
            
            # Decidim si necessitem subplots (Velocitat + Seleccionades)
            n_rows = 1 if not selected_vars else 2
            row_heights = [0.7, 0.3] if n_rows == 2 else [1.0]
            
            fig = make_subplots(
                rows=n_rows, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08,
                row_heights=row_heights,
                subplot_titles=("🚀 PERFIL DE VELOCITAT (KM/H)", "📡 SENYALS I ESTATS DE TREBALL") if n_rows > 1 else None
            )
            
            # 1. Velocitat Principal
            fill_c = "rgba(0, 210, 255, 0.15)" if st.session_state.theme_mode == "FOSC (Cockpit)" else "rgba(0, 82, 163, 0.15)"
            fig.add_trace(
                go.Scatter(
                    x=analysis_df[time_col], 
                    y=analysis_df[speed_col], 
                    line={'color': t['primary'], 'width': 3.5, 'shape': 'spline'}, 
                    fill='tozeroy', 
                    fillcolor=fill_c, 
                    name="Velocitat (KM/H)"
                ), row=1, col=1
            )
            
            # 2. Senyals addicionals (si n'hi ha)
            colors_extra = ["#feb300", "#ff716c", "#00ff88", "#ff00ff", "#00ffff"]
            for i, extra_v in enumerate(selected_vars):
                if extra_v not in [speed_col, km_col, time_col] and extra_v in analysis_df.columns:
                    target_row = 2 if n_rows > 1 else 1
                    color = colors_extra[i % len(colors_extra)]
                    
                    fig.add_trace(
                        go.Scatter(
                            x=analysis_df[time_col], 
                            y=analysis_df[extra_v], 
                            name=str(extra_v).split(':')[-1].strip(), 
                            line={'width': 2, 'color': color}, 
                            opacity=0.9
                        ), row=target_row, col=1
                    )
                    
                    # --- RES SALTAT D'ESDEVENIMENTS (Canvi 0 -> 1) ---
                    try:
                        # Convertim a numèric de forma segura
                        vals = pd.to_numeric(analysis_df[extra_v], errors='coerce').fillna(0)
                        
                        # Lògica especial per a ATP/ATO (Canvi de mode)
                        is_conduction_var = any(k in str(extra_v).upper() for k in ["ATP", "ATO"])
                        
                        # Detectem transició de 0 a 1
                        trans_idx = analysis_df[(vals.shift(1) == 0) & (vals == 1)].index
                        
                        for idx in trans_idx:
                            t_val = analysis_df.loc[idx, time_col]
                            label = f" ⚡ {str(extra_v).split(':')[-1].strip()}"
                            
                            # Si és canvi de mode, detectem l'anterior si podem
                            if is_conduction_var:
                                other_v = ato_col if "ATP" in str(extra_v).upper() else atp_col
                                if other_v and other_v in analysis_df.columns:
                                    prev_idx = analysis_df.index.get_loc(idx) - 1 if analysis_df.index.get_loc(idx) > 0 else 0
                                    other_prev_val = pd.to_numeric(analysis_df.iloc[prev_idx][other_v], errors='coerce')
                                    if other_prev_val == 1:
                                        label = f" 🕹️ CANVI DE MODE -> {str(extra_v).split(':')[-1].strip()}"
                            
                            # Línia Vertical
                            fig.add_vline(
                                x=t_val, 
                                line_width=2, 
                                line_dash="dash", 
                                line_color=color,
                                opacity=0.8,
                                annotation_text=f"{label} ({t_val})",
                                annotation_position="top right",
                                annotation_font_size=12,
                                annotation_font_color="#ffffff",
                                annotation_bgcolor=color,
                                annotation_bordercolor=color,
                                annotation_borderwidth=1,
                                row="all", col=1
                            )
                            # Marcador puntual al subplot de senyals
                            fig.add_trace(
                                go.Scatter(
                                    x=[t_val], 
                                    y=[1],
                                    mode="markers+text",
                                    marker=dict(size=12, color=color, symbol="diamond", line=dict(width=2, color="white")),
                                    showlegend=False,
                                    hoverinfo="skip"
                                ), row=target_row, col=1
                            )
                    except Exception as e:
                        # print(f"Error highlighting {extra_v}: {e}")
                        pass

            grid_c = 'rgba(255,255,255,0.08)' if t['plotly_template'] == 'plotly_dark' else 'rgba(0,0,0,0.08)'
            fig.update_layout(
                template=t['plotly_template'], 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                margin={'l': 0, 'r': 0, 't': 40, 'b': 0}, 
                height=600 if n_rows > 1 else 450, 
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(gridcolor=grid_c, zeroline=False, showline=True, linewidth=1, linecolor=grid_c)
            fig.update_yaxes(gridcolor=grid_c, zeroline=False, showline=True, linewidth=1, linecolor=grid_c)
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # --- RESUM EXECUTIU (TAULA) ---
            st.subheader("📋 Resum Executiu de l'Operació")
            tab_op, tab_min = st.tabs(["🚆 Resum Operatiu (Esdeveniments)", "📊 Log per Minut (Detall)"])
            
            with tab_op:
                with st.spinner("Analitzant parades i sortides..."):
                    op_events = get_event_based_summary(
                        analysis_df, 
                        time_col=str(time_col), 
                        speed_col=str(speed_col), 
                        km_col=str(km_col),
                        starting_pk=selected_starting_pk,
                        line_filter=current_line_filter,
                        is_ascendant=is_ascendant
                    )
                    
                    if op_events:
                        op_df = pd.DataFrame(op_events)
                        st.dataframe(
                            op_df.rename(columns={"time": "⌚ Hora", "event": "📝 Esdeveniment", "details": "ℹ️ Detalls"}),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No s'han detectat esdeveniments operatius significatius (aturades/sortides).")

            with tab_min:
                with st.spinner("Calculant segments..."):
                    minute_summary = get_minute_summary(
                        analysis_df, 
                        time_col=str(time_col), 
                        speed_col=str(speed_col), 
                        km_col=str(km_col),
                        extra_cols=st.session_state.get("selected_vars", []),
                        starting_pk=selected_starting_pk,
                        line_filter=current_line_filter,
                        is_ascendant=is_ascendant
                    )
                    
                    if minute_summary:
                        summary_df = pd.DataFrame(minute_summary)
                        ui_cols = {
                            "start_time": "⌚ Hora",
                            "location": "📍 Ubicació (Estació)",
                            "ut_indicator": "📟 Odòmetre (m)",
                            "distance": "📏 Dist. Segment",
                            "max_speed": "🚀 V. Max",
                            "avg_speed": "📈 V. Mig",
                            "anomalies": "⚠️ Alertes"
                        }
                        summary_df = summary_df.rename(columns=ui_cols)
                        st.dataframe(
                            summary_df, 
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "⚠️ Alertes": st.column_config.TextColumn(width="large")
                            }
                        )
                    else:
                        st.info("No s'han pogut segmentar prou dades per al log minutat.")

            # --- GENERACIÓ D'INFORME ---
            st.markdown("---")
            notes = st.text_area("Observacions del Tècnic:", placeholder="Afegeix els detalls de l'anàlisi aquí...")
            if st.button("🔧 GENERAR INFORME OFICIAL"):
                with st.spinner("Compilant informe..."):
                    plt.figure(figsize=(10, 4), dpi=100)
                    plt.style.use('dark_background' if t['plotly_template'] == 'plotly_dark' else 'default')
                    
                    # Garantim dades netes per Matplotlib
                    rep_x = pd.to_datetime(analysis_df[time_col], errors='coerce').dt.strftime('%H:%M:%S').fillna('--:--')
                    rep_y = pd.to_numeric(analysis_df[speed_col], errors='coerce').fillna(0).tolist()
                    
                    plt.plot(rep_x, rep_y, color=t['primary'], linewidth=2, label="Velocitat")
                    plt.title(f"Telemetria Serie FGC {st.session_state.current_unit}")
                    plt.grid(True, alpha=0.1)
                    
                    # --- HIGHLIGHTS EN MATPLOTLIB ---
                    colors_extra = ["#feb300", "#ff716c", "#00ff88", "#ff00ff", "#00ffff"]
                    for i, extra_v in enumerate(selected_vars):
                        if extra_v not in [speed_col, km_col, time_col] and extra_v in analysis_df.columns:
                            color = colors_extra[i % len(colors_extra)]
                            vals = pd.to_numeric(analysis_df[extra_v], errors='coerce').fillna(0)
                            trans_idx = analysis_df[(vals.shift(1) == 0) & (vals == 1)].index
                            for idx in trans_idx:
                                t_str = rep_x.loc[idx]
                                plt.axvline(x=t_str, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
                                plt.text(t_str, max(rep_y)*0.9, f" {str(extra_v).split(':')[-1].strip()}", 
                                         color=color, fontsize=8, verticalalignment='bottom')
                    
                    # Limitem la densitat de labels per a l'informe si hi ha moltes dades
                    if len(rep_x) > 10:
                        indices = np.linspace(0, len(rep_x)-1, 10).astype(int)
                        plt.xticks(indices, [rep_x.iloc[i] for i in indices], rotation=45)
                    else:
                        plt.xticks(rotation=45)
                    
                    chart_buf = io.BytesIO()
                    plt.savefig(chart_buf, format='png', bbox_inches='tight')
                    plt.close()
                    
                    # Re-càlcul del resum executiu (Events + Log per Minut)
                    op_events = get_event_based_summary(
                        analysis_df, 
                        time_col=str(time_col), 
                        speed_col=str(speed_col), 
                        km_col=str(km_col),
                        starting_pk=selected_starting_pk,
                        line_filter=current_line_filter,
                        is_ascendant=is_ascendant
                    )
                    
                    minute_summary = get_minute_summary(
                        analysis_df, 
                        time_col=str(time_col), 
                        speed_col=str(speed_col), 
                        km_col=str(km_col),
                        extra_cols=st.session_state.get("selected_vars", []),
                        starting_pk=selected_starting_pk,
                        line_filter=current_line_filter,
                        is_ascendant=is_ascendant
                    )
                    
                    doc_buf = generate_word_report(
                        analysis_df, 
                        minute_summary, 
                        {"motiu": f"Anàlisi {st.session_state.current_unit}"}, 
                        chart_img=chart_buf.getvalue(), 
                        notes=notes,
                        op_events=op_events
                    )
                    st.download_button("📥 DESCARREGAR INFORME", data=doc_buf, file_name=f"Informe_FGC_{current_key}.docx")

        except Exception as e:
            st.error(f"⚠️ Error Crític: {e}")
            st.exception(e)
    else:
        st.markdown('<br><div class="glass-panel" style="text-align: center; border-color: var(--primary);"><h2>SISTEMA EN ESPERA</h2><p style="color: var(--primary); font-weight: 700; letter-spacing: 0.2em;">>>> CARREGUEU TELEMETRIA PER INICIAR EL COCKPIT <<<</p></div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
