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

# --- TEMA I ESTILS ---
if 'theme_mode' not in st.session_state: st.session_state.theme_mode = "CLAR (Swiss)"

def get_base64_of_bin_file(bin_file):
    if not os.path.exists(bin_file): return ""
    with open(bin_file, 'rb') as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64_of_bin_file("assets/logo.png")

t = {
    "primary": "#0052A3", "secondary": "#FF5722", "background": "#f8fafc", "border": "#e2e8f0",
    "on_surface": "#0f172a", "on_surface_variant": "#475569", "card_bg": "#ffffff", "shadow": "0 1px 3px rgba(0,0,0,0.1)"
}

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Manrope:wght@600;800&display=swap');
    :root {{ --primary: {t['primary']}; --secondary: {t['secondary']}; --background: {t['background']}; --on-surface: {t['on_surface']}; }}
    .main {{ background-color: {t['background']} !important; font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {t['background']} !important; }}
    h1 {{ font-family: 'Manrope', sans-serif; font-weight: 800; color: var(--on-surface); font-size: 2.2rem !important; margin-bottom: 0px; }}
    .cockpit-card {{ background: {t['card_bg']}; padding: 1.2rem; border-radius: 12px; border: 1px solid {t['border']}; box-shadow: {t['shadow']}; margin-bottom: 1rem; }}
    .kpi-label {{ font-size: 0.65rem; font-weight: 800; color: {t['on_surface_variant']}; text-transform: uppercase; letter-spacing: 0.1em; }}
    .kpi-value {{ font-family: 'Manrope', sans-serif; font-size: 2.2rem; font-weight: 800; color: var(--on-surface); line-height: 1.1; }}
    .kpi-unit {{ font-size: 0.75rem; color: var(--primary); font-weight: 700; margin-left: 4px; }}
    .status-badge {{ display: inline-flex; align-items: center; gap: 8px; background: rgba(0, 82, 163, 0.05); padding: 8px 16px; border-radius: 20px; font-size: 0.65rem; font-weight: 800; color: var(--primary); border: 1px solid rgba(0, 82, 163, 0.1); }}
    .pulse-dot {{ width: 8px; height: 8px; background: var(--primary); border-radius: 50%; opacity: 0.6; animation: pulse-blue 1.5s infinite; }}
    @keyframes pulse-blue {{ 0% {{ transform: scale(0.9); opacity: 0.4; }} 70% {{ transform: scale(1.1); opacity: 1; }} 100% {{ transform: scale(0.9); opacity: 0.4; }} }}
    .top-schematic {{ background: #ffffff; padding: 2rem 1.5rem; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 2rem; overflow: hidden; display: flex; justify-content: center; }}
</style>
""", unsafe_allow_html=True)

def render_network_schematic(origin_id=None, pos_id=None, signals_data=None):
    from src.data_processing import load_stations
    network = load_stations()
    if not network: return ""
    # Mantenim SPACING alt per omplir el quadre, però millorem marges de noms
    X_START, Y_MAIN, SPACING, NODE_CH = 40, 150, 62, 22
    LABEL_OFFSET = 32 # Distància del nom al node
    
    trunk = network.get("Tronc-Comu-PC-SC", {}).get("stations", [])
    x_sc = X_START + (len(trunk)-1)*SPACING
    
    s1 = network.get("Ramal-S1-Terrassa", {}).get("stations", [])
    x_last_s1 = x_sc + 60 + (len(s1)-1) * SPACING if s1 else x_sc
    
    s2 = network.get("Ramal-S2-Sabadell", {}).get("stations", [])
    x_last_s2 = x_sc + 60 + (len(s2)-1) * SPACING if s2 else x_sc
    
    W_SVG = max(x_last_s1, x_last_s2) + 60
    H_SVG = 380 # Augmentem H per donar aire als noms de dalt i baix
    
    svg = f'<svg width="100%" height="{H_SVG}" viewBox="0 0 {W_SVG} {H_SVG}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" style="background:#ffffff; border-radius:12px;">'
    svg += """<style>
        .schematic-line{stroke:#ccd6e0;stroke-width:2.5;fill:none;stroke-linecap:round;}
        .schematic-node{fill:#ffffff;stroke:#94a3b8;stroke-width:2;cursor:pointer;transition:all 0.2s;}
        .schematic-node:hover{stroke:#0052A3;stroke-width:5;fill:#f1f5f9;}
        .schematic-node-pos{fill:#0052A3;stroke:#003b79;filter:drop-shadow(0 0 5px rgba(0,82,163,0.3));}
        .schematic-node-origin{fill:#FF5722;stroke:#d84315;}
        .schematic-label{font-family:'Inter',sans-serif;font-size:11px;font-weight:800;fill:#334155;pointer-events:none;}
        .schematic-signal{stroke:#f59e0b;stroke-width:2;fill:none;transition:all 0.2s;}
        .schematic-signal:hover{stroke:#d97706;stroke-width:4;}
    </style>"""
    
    VIA_OFF = 5 
    NODE_H = 26
    x_coords = {}
    
    # Tronc Comú (Doble Via)
    svg += f'<line x1="{X_START}" y1="{Y_MAIN-VIA_OFF}" x2="{x_sc}" y2="{Y_MAIN-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
    svg += f'<line x1="{X_START}" y1="{Y_MAIN+VIA_OFF}" x2="{x_sc}" y2="{Y_MAIN+VIA_OFF}" class="schematic-line" />'
    
    for i, s in enumerate(trunk):
        x = X_START + i * SPACING
        x_coords[s['id']] = x
        cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
        svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{Y_MAIN-13}" width="12" height="{NODE_H}" rx="4" class="{cls}"/><text x="{x}" y="{Y_MAIN+LABEL_OFFSET+6}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'

    x_gr = x_coords.get("GR", X_START + 2*SPACING)
    l7_st = network.get("Ramal-L7", {}).get("stations", [])
    if l7_st:
        y_l7 = Y_MAIN + 65
        x_first_l7 = x_gr + SPACING
        x_last_l7 = x_first_l7 + (len(l7_st)-1) * SPACING
        svg += f'<path d="M {x_gr} {Y_MAIN-VIA_OFF} L {x_first_l7} {y_l7-VIA_OFF} L {x_last_l7} {y_l7-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
        svg += f'<path d="M {x_gr} {Y_MAIN+VIA_OFF} L {x_first_l7} {y_l7+VIA_OFF} L {x_last_l7} {y_l7+VIA_OFF}" class="schematic-line" />'
        for i, s in enumerate(l7_st):
            x = x_first_l7 + i * SPACING
            cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
            svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{y_l7-13}" width="12" height="{NODE_H}" rx="4" class="{cls}"/><text x="{x}" y="{y_l7+LABEL_OFFSET+6}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'

    x_sr = x_coords.get("SR", X_START + 7*SPACING)
    l12_st = network.get("Ramal-L12", {}).get("stations", [])
    if l12_st:
        y_l12 = Y_MAIN - 65
        x_first_l12 = x_sr + SPACING
        x_last_l12 = x_first_l12 + (len(l12_st)-1) * SPACING
        svg += f'<path d="M {x_sr} {Y_MAIN-VIA_OFF} L {x_first_l12} {y_l12-VIA_OFF} L {x_last_l12} {y_l12-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
        svg += f'<path d="M {x_sr} {Y_MAIN+VIA_OFF} L {x_first_l12} {y_l12+VIA_OFF} L {x_last_l12} {y_l12+VIA_OFF}" class="schematic-line" />'
        for i, s in enumerate(l12_st):
            x = x_first_l12 + i * SPACING
            cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
            svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{y_l12-13}" width="12" height="{NODE_H}" rx="4" class="{cls}"/><text x="{x}" y="{y_l12-LABEL_OFFSET}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'

    y_s1 = Y_MAIN - 90
    x_first_s1 = x_sc + SPACING
    x_last_s1 = x_first_s1 + (len(s1)-1) * SPACING
    svg += f'<path d="M {x_sc} {Y_MAIN-VIA_OFF} L {x_first_s1} {y_s1-VIA_OFF} L {x_last_s1} {y_s1-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
    svg += f'<path d="M {x_sc} {Y_MAIN+VIA_OFF} L {x_first_s1} {y_s1+VIA_OFF} L {x_last_s1} {y_s1+VIA_OFF}" class="schematic-line" />'
    for i, s in enumerate(s1):
        x = x_first_s1 + i * SPACING
        cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
        svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{y_s1-13}" width="12" height="{NODE_H}" rx="4" class="{cls}"/><text x="{x}" y="{y_s1-LABEL_OFFSET}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'
    
    y_s2 = Y_MAIN + 90
    x_first_s2 = x_sc + SPACING
    x_last_s2 = x_first_s2 + (len(s2)-1) * SPACING
    svg += f'<path d="M {x_sc} {Y_MAIN-VIA_OFF} L {x_first_s2} {y_s2-VIA_OFF} L {x_last_s2} {y_s2-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
    svg += f'<path d="M {x_sc} {Y_MAIN+VIA_OFF} L {x_first_s2} {y_s2+VIA_OFF} L {x_last_s2} {y_s2+VIA_OFF}" class="schematic-line" />'
    for i, s in enumerate(s2):
        x = x_first_s2 + i * SPACING
        cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
        svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{y_s2-13}" width="12" height="{NODE_H}" rx="4" class="{cls}"/><text x="{x}" y="{y_s2+LABEL_OFFSET+6}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'

    # --- Dibuixar Senyals si n'hi ha (Situades a la VIA 1 - via de baix) ---
    if signals_data:
        # Tronc Comú
        trunk_pks = [s['pk_abs'] for s in trunk]
        for sig in signals_data.get("Tronc-Comu", []):
            spk = float(sig["pk_abs"])
            if spk <= trunk_pks[-1]:
                for i in range(len(trunk)-1):
                    p1, p2 = trunk_pks[i], trunk_pks[i+1]
                    if p1 <= spk <= p2:
                        sx = x_coords[trunk[i]['id']] + (spk-p1)/(p2-p1)*(x_coords[trunk[i+1]['id']]-x_coords[trunk[i]['id']])
                        # Marca vertical sobre la VIA 1 (Y_MAIN + VIA_OFF)
                        svg += f'<g><title>Senyal {sig["id"]} [Via 1] (PK {spk:.3f})</title><line x1="{sx}" y1="{Y_MAIN+VIA_OFF-6}" x2="{sx}" y2="{Y_MAIN+VIA_OFF+6}" class="schematic-signal" /></g>'
                        break

        # S1 Branch
        s1_pks = [s['pk_abs'] for s in s1]
        if s1:
            for sig in signals_data.get("Ramal-S1", []):
                spk = float(sig["pk_abs"])
                if s1_pks[0] <= spk <= s1_pks[-1]:
                    for i in range(len(s1)-1):
                        p1, p2 = s1_pks[i], s1_pks[i+1]
                        if p1 <= spk <= p2:
                            sx = x_first_s1 + i*SPACING + (spk-p1)/(p2-p1)*SPACING
                            svg += f'<g><title>Senyal {sig["id"]} [Via 1] (PK {spk:.3f})</title><line x1="{sx}" y1="{y_s1+VIA_OFF-6}" x2="{sx}" y2="{y_s1+VIA_OFF+6}" class="schematic-signal" /></g>'
                            break

        # S2 Branch
        s2_pks = [s['pk_abs'] for s in s2]
        if s2:
            for sig in signals_data.get("Ramal-S2", []):
                spk = float(sig["pk_abs"])
                if s2_pks[0] <= spk <= s2_pks[-1]:
                    for i in range(len(s2)-1):
                        p1, p2 = s2_pks[i], s2_pks[i+1]
                        if p1 <= spk <= p2:
                            sx = x_first_s2 + i*SPACING + (spk-p1)/(p2-p1)*SPACING
                            svg += f'<g><title>Senyal {sig["id"]} [Via 1] (PK {spk:.3f})</title><line x1="{sx}" y1="{y_s2+VIA_OFF-6}" x2="{sx}" y2="{y_s2+VIA_OFF+6}" class="schematic-signal" /></g>'
                            break

        # L7 Branch
        l7_pks = [s['pk_abs'] for s in l7_st]
        if l7_st:
            for sig in signals_data.get("Ramal-L7", []):
                spk = float(sig["pk_abs"])
                if l7_pks[0] <= spk <= l7_pks[-1]:
                    for i in range(len(l7_st)-1):
                        p1, p2 = l7_pks[i], l7_pks[i+1]
                        if p1 <= spk <= p2:
                            sx = x_first_l7 + i*SPACING + (spk-p1)/(p2-p1)*SPACING
                            svg += f'<g><title>Senyal {sig["id"]} [Via 1] (PK {spk:.3f})</title><line x1="{sx}" y1="{y_l7+VIA_OFF-6}" x2="{sx}" y2="{y_l7+VIA_OFF+6}" class="schematic-signal" /></g>'
                            break

    svg += f'<g transform="translate(20, 15)">'
    svg += f'<rect x="0" y="0" width="10" height="10" rx="2" fill="#ccd6e0" style="opacity:0.6;"/><text x="14" y="9" style="font-family:Inter; font-size:10px; font-weight:800; fill:#64748b;">VIA 2 / DESC</text>'
    svg += f'<rect x="90" y="0" width="10" height="10" rx="2" fill="#ccd6e0"/><text x="104" y="9" style="font-family:Inter; font-size:10px; font-weight:800; fill:#1e293b;">VIA 1 / ASC</text>'
    svg += f'<line x1="180" y1="5" x2="190" y2="5" style="stroke:#f59e0b; stroke-width:3;"/><text x="195" y="9" style="font-family:Inter; font-size:10px; font-weight:800; fill:#1e293b;">SENYAL (VIA 1)</text>'
    svg += f'<rect x="290" y="0" width="10" height="10" rx="2" fill="#0052A3"/><text x="304" y="9" style="font-family:Inter; font-size:10px; font-weight:800; fill:#1e293b;">POSICIÓ ACTUAL</text>'
    svg += f'</g>'
    svg += '</svg>'
    return svg

def main():
    # 1. Gestió d'estat inicial
    if 'selected_vars' not in st.session_state: st.session_state.selected_vars = []
    if 'processed_data' not in st.session_state: st.session_state.processed_data = None
    if 'last_loaded_key' not in st.session_state: st.session_state.last_loaded_key = None
    if 'filtered_df' not in st.session_state: st.session_state.filtered_df = None
    if 'selected_st_ui' not in st.session_state: st.session_state.selected_st_ui = "Cap (Ús PK Absolut)"

    # 2. Interacció amb el Mapa (Query Params)
    if "station_origin" in st.query_params:
        target_id = st.query_params["station_origin"]
        all_st = get_all_stations_flat()
        found = next((s for s in all_st if s["id"] == target_id), None)
        if found and found["display_name"] != st.session_state.selected_st_ui:
            st.session_state.selected_st_ui = found["display_name"]
            st.query_params.clear()
            st.rerun()
        elif found:
            st.query_params.clear()

    with st.sidebar:
        st.markdown(f'<div style="text-align:center; margin-bottom:20px;"><img src="data:image/png;base64,{logo_base64}" width="100" style="border-radius:15px;"></div>', unsafe_allow_html=True)
        st.markdown("### 📁 Control Registres")
        uploaded_file = st.file_uploader("", type=["xlsx", "csv", "pdf"], label_visibility="collapsed")
        unit_model = st.selectbox("Tren Seleccionat:", ["UT 113-114", "UT 112", "UT 115"], key="current_unit")
        demo_mode = st.toggle("Activar Mode Demo", value=False)
        st.markdown("---")
        st.markdown("### 🎯 Anàlisi Ràpid")
        def apply_rapid_vars(analysis_type):
            df_curr = st.session_state.get("processed_data")
            if df_curr is None: return
            cols = df_curr.columns.tolist()
            selected = []
            if analysis_type == "estacio":
                for c in cols:
                    cn = str(c).upper()
                    if any(k in cn for k in ["VEL", "SPEED", "AAA"]): selected.append(c)
                    if any(k in cn for k in ["DIST", "KM", "PK"]): selected.append(c)
            elif analysis_type == "senyal":
                for c in cols:
                    cn = str(c).upper()
                    if any(k in cn for k in ["VEL", "SPEED"]): selected.append(c)
                    if any(k in cn for k in ["FU", "URG", "FE", "BOLET", "SETA"]): selected.append(c)
            elif analysis_type == "conduccio":
                for c in cols:
                    cn = str(c).upper()
                    if any(k in cn for k in ["ATP", "ATO", "MODE"]): selected.append(c)
            st.session_state.selected_vars = list(dict.fromkeys(selected))
            st.rerun()

        rb_c1, rb_c2 = st.columns(2)
        if rb_c1.button("🚉 Ultrap. Estació", use_container_width=True): apply_rapid_vars("estacio")
        if rb_c1.button("🕹️ Mode Conducció", use_container_width=True): apply_rapid_vars("conduccio")
        if rb_c2.button("🛑 Ultrap. Senyal", use_container_width=True): apply_rapid_vars("senyal")
        if rb_c2.button("🧹 Neteja Filtres", use_container_width=True): 
            st.session_state.selected_vars = []
            st.rerun()

        if st.session_state.processed_data is not None:
            st.markdown("---")
            st.markdown("### 🕒 Filtre Temporal")
            df_full = st.session_state.processed_data
            t_col_temp = next((c for c in df_full.columns if any(k in str(c).upper() for k in ['TIME', 'HORA'])), df_full.columns[0])
            raw_t_full = df_full[t_col_temp].astype(str).str.replace(' - ', ' ', regex=False)
            temp_ts_full = pd.to_datetime(raw_t_full, dayfirst=True, errors='coerce')
            times_full = temp_ts_full.dt.strftime('%H:%M:%S').tolist()
            
            t_start, t_end = st.select_slider(
                "Selecciona l'interval horari:",
                options=times_full,
                value=(times_full[0], times_full[-1]),
                key="time_filter_slider"
            )
            
            idx_s = times_full.index(t_start)
            idx_e = times_full.index(t_end)
            if idx_s > idx_e: idx_s, idx_e = idx_e, idx_s
            st.session_state.filtered_df = df_full.iloc[idx_s:idx_e+1]
        else:
            st.session_state.filtered_df = None

    st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:center;"><div><h1>ANALISTA OTMR <span style="color:#0052A3">PRO</span></h1><p style="margin:0; font-size:0.75rem; color:#64748b; font-weight:800;">DEPARTAMENT OPERATIU - FERROCARRILS DE LA GENERALITAT DE CATALUNYA</p></div><div class="status-badge"><div class="pulse-dot"></div> MONITORITZACIÓ ACTIVA</div></div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 🗺️ Context de l'Anàlisi")
    ctx_c1, ctx_c2, ctx_c3 = st.columns([1,1,1.2])
    with ctx_c1: st.selectbox("Tracks / Línia:", ["S1 (Terrassa)", "S2 (Sabadell)", "L6 (Sarrià)", "L7 (Tibidabo)", "L12 (RE)", "Totes"], key="active_line")
    with ctx_c2: st.selectbox("Sentit de la marxa:", ["Ascendent", "Descendent"], key="active_direction")
    
    st_options = ["Cap (Ús PK Absolut)"] + [s["display_name"] for s in get_all_stations_flat()]
    st_idx = st_options.index(st.session_state.selected_st_ui) if st.session_state.selected_st_ui in st_options else 0
    with ctx_c3: st.selectbox("📍 Origen (Calibratge PK):", st_options, index=st_idx, key="selectbox_st_ui", on_change=lambda: st.session_state.update(selected_st_ui=st.session_state.selectbox_st_ui))

    key_id = "DEMOFIX" if demo_mode else (uploaded_file.name if uploaded_file else None)
    if key_id and (st.session_state.processed_data is None or key_id != st.session_state.last_loaded_key):
        df = load_data(uploaded_file if not demo_mode else "MOCK_FGC")
        st.session_state.processed_data, st.session_state.last_loaded_key = df, key_id

    # Obtenir el DF adequat segons el filtre
    df = st.session_state.get("filtered_df")
    if df is None:
        df = st.session_state.get("processed_data")

    if df is not None:
        speed_col = next((c for c in df.columns if any(k in str(c).upper() for k in ['VEL', 'SPEED', 'AAA'])), df.columns[0] if len(df.columns) > 0 else None)
        km_col = next((c for c in df.columns if any(k in str(c).upper() for k in ['DIST', 'KM', 'PK'])), df.columns[1] if len(df.columns) > 1 else (df.columns[0] if len(df.columns) > 0 else None))
        time_col = next((c for c in df.columns if any(k in str(c).upper() for k in ['TIME', 'HORA'])), df.columns[2] if len(df.columns) > 2 else (df.columns[0] if len(df.columns) > 0 else None))
        ato_col = next((c for c in df.columns if "ATO" in str(c).upper()), None)

        if not speed_col or not km_col or not time_col:
            st.error("⚠️ El fitxer no conté les columnes mínimes requerides (Velocitat, PK/Distància, Temps).")
            st.stop()

        raw_t = df[time_col].astype(str).str.replace(' - ', ' ', regex=False)
        temp_ts = pd.to_datetime(raw_t, dayfirst=True, errors='coerce')
        times_l = temp_ts.dt.strftime('%H:%M:%S').tolist()
        
        st.markdown("### ⏲️ Cursor de Telemetria Sincronitzat")
        cursor_idx = st.select_slider("Gliseu pel registre operacional:", options=range(len(df)), value=len(df)-1, format_func=lambda x: times_l[x])
        point = df.iloc[cursor_idx]
        
        pk_abs = float(point[km_col])
        origin_id = None
        sel_st = st.session_state.selected_st_ui
        start_pk = None
        if sel_st != "Cap (Ús PK Absolut)":
            obj = next((s for s in get_all_stations_flat() if s["display_name"] == sel_st), None)
            if obj:
                origin_id, start_pk = obj["id"], float(obj.get("pk_abs", obj.get("pk", 0)))
                dist = float(point[km_col]) - float(df.iloc[0][km_col])
                pk_abs = start_pk + (dist if "Ascendent" in st.session_state.active_direction else -dist)

        closest = get_closest_station(pk_abs, load_stations())
        pos_id = closest.split("(")[-1].split(")")[0] if "(" in closest else None
        
        # Propera Senyal
        from src.data_processing import load_signals, get_closest_signal
        signals_data = load_signals()
        closest_sig, sig_dist = get_closest_signal(pk_abs, signals_data)
        next_sig_str = f"{closest_sig['id']} ({sig_dist*1000:.0f}m)" if closest_sig else "---"

        from src.svg_component import interactive_svg
        svg_code = render_network_schematic(origin_id, pos_id, signals_data)
        clicked_station = interactive_svg(svg_code=svg_code, height=420, key="svg_map")

        if clicked_station and clicked_station != "RESET":
            all_st = get_all_stations_flat()
            found = next((s for s in all_st if s["id"] == clicked_station), None)
            if found and found["display_name"] != st.session_state.selected_st_ui:
                st.session_state.selected_st_ui = found["display_name"]
                st.rerun()

        st.markdown(f'<p style="text-align:center; font-weight:800; color:#0052A3; margin-top:-20px; margin-bottom:25px;">📍 POSICIÓ ACTUAL: {closest}</p>', unsafe_allow_html=True)

        k_cols = st.columns(5)
        k_cols[0].markdown(f'<div class="cockpit-card"><div class="kpi-label">🚀 Velocitat</div><div class="kpi-value">{float(point[speed_col]):.1f}<span class="kpi-unit">KM/H</span></div></div>', unsafe_allow_html=True)
        k_cols[1].markdown(f'<div class="cockpit-card"><div class="kpi-label">📏 Posició PK</div><div class="kpi-value">{pk_abs:.3f}<span class="kpi-unit">KM</span></div></div>', unsafe_allow_html=True)
        
        dist_recorreguda = abs(float(point[km_col]) - float(df.iloc[0][km_col]))
        k_cols[2].markdown(f'<div class="cockpit-card"><div class="kpi-label">🛤️ Dist. Recorreguda</div><div class="kpi-value">{dist_recorreguda:.3f}<span class="kpi-unit">KM</span></div></div>', unsafe_allow_html=True)
        
        mode = "🤖 ATO" if (ato_col and point[ato_col]==1) else "⚙️ ATP"
        k_cols[3].markdown(f'<div class="cockpit-card"><div class="kpi-label">🕹️ Mode Actiu</div><div class="kpi-value" style="color:{"#10b981" if "ATO" in mode else "#0052A3"}">{mode}</div></div>', unsafe_allow_html=True)
        k_cols[4].markdown(f'<div class="cockpit-card"><div class="kpi-label">🚦 Propera Senyal</div><div class="kpi-value">{next_sig_str}</div></div>', unsafe_allow_html=True)

        st.multiselect("Senyals de Control:", df.columns.tolist(), key="selected_vars_ui", default=st.session_state.selected_vars)
        st.session_state.selected_vars = st.session_state.selected_vars_ui
        
        from plotly.subplots import make_subplots
        fig = make_subplots(rows=2 if st.session_state.selected_vars else 1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df[time_col], y=df[speed_col], name="Velocitat", line=dict(color="#0052A3", width=3), fill='tozeroy', fillcolor='rgba(0,82,163,0.1)'), row=1, col=1)
        fig.add_vline(x=point[time_col], line_width=2, line_dash="dash", line_color="#ef4444")
        
        if ato_col:
            changes = df[df[ato_col].diff().fillna(0) != 0]
            for _, r in changes.iterrows():
                m = "ATO" if r[ato_col]==1 else "ATP"
                fig.add_vline(x=r[time_col], line_width=1.2, line_dash="dot", line_color="#f59e0b")
                fig.add_annotation(x=r[time_col], y=90, text=f"Entrada {m}", showarrow=False, font=dict(size=9, color="#b45309"))

        # Afegir Senyals al Gràfic
        if signals_data:
            limit_pks = [df[km_col].min(), df[km_col].max()]
            for name, items in signals_data.items():
                for sig in items:
                    spk = float(sig["pk_abs"])
                    if min(limit_pks) <= spk <= max(limit_pks):
                        # Trobar punt de temps més proper al PK del senyal (aproximat)
                        closest_idx = (df[km_col] - spk).abs().idxmin()
                        sig_time = df.loc[closest_idx, time_col]
                        fig.add_vline(x=sig_time, line_width=1, line_dash="dash", line_color="#f59e0b", opacity=0.4)
                        fig.add_annotation(x=sig_time, y=10, text=f"{sig['id']}", showarrow=False, font=dict(size=8, color="#d97706"))

        for idx, v in enumerate(st.session_state.selected_vars):
            if v != speed_col: fig.add_trace(go.Scatter(x=df[time_col], y=df[v], name=str(v)), row=2, col=1)
        
        fig.update_layout(height=450, margin=dict(l=0,r=0,t=20,b=0), legend=dict(orientation="h", y=1.05, x=1))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📋 Resum Operatiu")
        tab1, tab2 = st.tabs(["🚆 Esdeveniments", "📊 Log Detallat"])
        with tab1:
            evs = get_event_based_summary(df, str(km_col), str(speed_col), str(time_col), starting_pk=start_pk, is_ascendant=("Ascendent" in st.session_state.active_direction))
            st.dataframe(pd.DataFrame(evs), use_container_width=True, hide_index=True)
        with tab2:
            log = get_minute_summary(df, str(time_col), str(speed_col), str(km_col), extra_cols=st.session_state.selected_vars, starting_pk=start_pk, is_ascendant=("Ascendent" in st.session_state.active_direction))
            st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True)

        st.markdown("---")
        notes = st.text_area("Observacions Tècniques:", placeholder="Afegiu detalls sobre qualsevol anomalia detectada...", height=100)
        if st.button("🔧 DESCARREGAR INFORME OFICIAL", use_container_width=True):
            with st.spinner("Generant Word..."):
                plt.figure(figsize=(10,4)); plt.plot(df[time_col], df[speed_col], color='#0052A3'); plt.grid(True, alpha=0.3)
                buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close()
                doc = generate_word_report(df, log, {"u":st.session_state.current_unit}, chart_img=buf.getvalue(), notes=notes, op_events=evs)
                st.download_button("📥 DESCARREGAR ARXIU", doc, f"Informe_FGC_{st.session_state.current_unit}.docx")
    else:
        st.markdown('<div style="text-align:center; padding:150px; opacity:0.4;"><h2>CARREGANT DADES...</h2><p>Pugeu un registre per començar l\'anàlisi operativa</p></div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
