import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
from src.data_processing import load_data, segment_by_blocks, calculate_kpis, get_suggested_mapping, load_mappings, get_sheet_names  # type: ignore
from src.report_generator import generate_word_report  # type: ignore
import io
import time
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓ DE LA PÀGINA ---
st.set_page_config(
    page_title="FGC | Analista OTMR Pro v4.2",
    page_icon="🚆",
    layout="wide",
)

# --- CONFIGURACIÓ DE TEMA I ESTILS DINÀMICS ---
if 'theme_mode' not in st.session_state: st.session_state.theme_mode = "FOSC (Cockpit)"

# --- DEFINICIÓ DE TEMES ---
THEMES = {
    "FOSC (Cockpit)": {
        "primary": "#00d2ff", "secondary": "#feb300", "background": "#0c0e10", "surface": "#0c0e10",
        "surface_container": "#171a1c", "on_surface": "#f1f0f3", "on_surface_variant": "#aaabad",
        "plotly_template": "plotly_dark", "shadow": "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
        "card_bg": "rgba(35, 38, 41, 0.45)", "glass_blur": "16px", "border": "rgba(255, 255, 255, 0.08)"
    },
    "CLAR (Swiss)": {
        "primary": "#0052A3", "secondary": "#FF5722", "background": "#f7f9fd", "surface": "#f7f9fd",
        "surface_container": "#ffffff", "on_surface": "#191c1f", "on_surface_variant": "#424751",
        "plotly_template": "plotly_white", "shadow": "0 2px 12px rgba(0,0,0,0.05)",
        "card_bg": "#ffffff", "glass_blur": "0px", "border": "rgba(0, 82, 163, 0.1)"
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
    [data-testid="stHeader"] {{ background: rgba(12, 14, 16, 0.1) !important; backdrop-filter: blur(12px); }}
    [data-testid="stSidebar"] {{ 
        background-color: {"#0c0e10" if st.session_state.theme_mode == "FOSC (Cockpit)" else "#ffffff"} !important; 
        border-right: 1px solid var(--outline-variant) !important; 
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
        background-color: {t['card_bg']}; 
        backdrop-filter: blur({t['glass_blur']});
        padding: 1.5rem; 
        border-radius: 12px; 
        border: 1px solid {t['border']} !important; 
        box-shadow: {t['shadow']}; 
        transition: all 0.3s ease; 
        margin-bottom: 1rem; 
    }}
    .cockpit-card:hover {{ transform: translateY(-4px); border-color: var(--primary) !important; }}
    
    .kpi-label {{ font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.75rem; color: var(--on-surface-variant); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.5rem; }}
    .kpi-value {{ font-family: 'Manrope', sans-serif; font-size: 2.5rem; font-weight: 800; color: var(--on-surface); line-height: 1; }}
    .kpi-unit {{ font-size: 0.9rem; font-weight: 500; color: var(--primary); margin-left: 6px; }}
    
    .glass-panel {{ 
        background: {t['card_bg']}; 
        backdrop-filter: blur(40px); 
        border-radius: 24px; 
        padding: 3rem; 
        border: 1px solid {t['border']}; 
    }}

    .stButton>button {{ 
        background: linear-gradient(135deg, var(--primary), {"#00a2ff" if t['primary'] == "#00d2ff" else "#003b79"}) !important; 
        color: {"#002c38" if t['primary'] == "#00d2ff" else "#ffffff"} !important; 
        border-radius: 10px !important; border: none !important; 
        font-family: 'Manrope', sans-serif !important; font-weight: 800 !important; 
        text-transform: uppercase !important; padding: 0.8rem 1.8rem !important; 
        transition: all 0.3s ease !important; 
    }}

    .status-badge {{ 
        display: inline-flex; align-items: center; gap: 10px; 
        background-color: rgba(0, 210, 255, 0.1); padding: 8px 18px; 
        border-radius: 30px; font-size: 0.75rem; font-weight: 800; color: var(--primary);
    }}
    .pulse-dot {{ width: 10px; height: 10px; background-color: var(--primary); border-radius: 50%; box-shadow: 0 0 15px var(--primary); animation: pulse 2s infinite; }}
    @keyframes pulse {{ 0% {{ transform: scale(0.9); opacity: 0.4; }} 50% {{ transform: scale(1.2); opacity: 1; }} 100% {{ transform: scale(0.9); opacity: 0.4; }} }}

    [data-testid="stSidebar"] img {{ filter: {"brightness(0) invert(1)" if st.session_state.theme_mode == "FOSC (Cockpit)" else "none"}; }}

    #MainMenu {{visibility: hidden;}} header {{visibility: hidden;}} footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

def main():
    if 'selected_vars' not in st.session_state: st.session_state.selected_vars = []
    if 'current_unit' not in st.session_state: st.session_state.current_unit = "UT 113-114"
    if 'processed_data' not in st.session_state: st.session_state.processed_data = None
    if 'last_loaded_key' not in st.session_state: st.session_state.last_loaded_key = None

    # --- HEADER ---
    st.markdown('<div style="padding-top: 1.5rem;"></div>', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([0.7, 0.3])
    with h_col1:
        st.markdown(f"# 🚆 Analista registres")
    with h_col2:
        st.markdown(f'<div style="text-align: right; padding-top: 1rem;"><div class="status-badge"><div class="pulse-dot"></div> EN_LÍNIA</div></div>', unsafe_allow_html=True)

    st.markdown('<div style="margin-bottom: 2rem; border-bottom: 1px solid var(--outline-variant);"></div>', unsafe_allow_html=True)

    # --- SIDEBAR ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/4/4b/FGC_original_logo.svg", width=120)
    
    st.sidebar.markdown("### 🎨 Aparença")
    new_theme = st.sidebar.radio("Esquema de colors:", options=list(THEMES.keys()), index=0 if st.session_state.theme_mode == "FOSC (Cockpit)" else 1, horizontal=True)
    if new_theme != st.session_state.theme_mode:
        st.session_state.theme_mode = new_theme
        st.rerun()

    st.sidebar.markdown("### 📁 Control de Registres")
    uploaded_file = st.sidebar.file_uploader("", type=["xlsx", "xls", "csv", "pdf"], label_visibility="collapsed")
    unit_model = st.sidebar.selectbox("Model d'Unitat de Tren:", options=["UT 113-114", "UT 112", "UT 115"], index=1 if st.session_state.current_unit == "UT 112" else 0)
    st.session_state.current_unit = unit_model
    
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    demo_mode = st.sidebar.toggle("Mode Demo (Simulació)", value=False)
    
    # Identificador únic per al fitxer (o mode demo)
    current_key = "DEMO" if demo_mode else (uploaded_file.name if uploaded_file else None)

    # --- LÒGICA DE PERSISTÈNCIA ---
    # Si el fitxer ha canviat, invalidem dades prèvies
    if current_key != st.session_state.last_loaded_key:
        st.session_state.processed_data = None
        st.session_state.last_loaded_key = current_key

    if current_key:
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
            
            # --- AUTO-DETECCIÓ PERSISTENT DE VARIABLES CRÍTIQUES (INDIE DEL MULTISELECT) ---
            if 'speed_col' not in st.session_state or st.session_state.speed_col not in all_cols:
                for col in all_cols:
                    if any(k in str(col).upper() for k in ['VELOCIDAD', 'SPEED', 'V_UT']): 
                        st.session_state.speed_col = col; break
                else: st.session_state.speed_col = all_cols[min(1, len(all_cols)-1)]

            if 'km_col' not in st.session_state or st.session_state.km_col not in all_cols:
                for col in all_cols:
                    if any(k in str(col).upper() for k in ['DISTANCIA', 'KM', 'X_UT']): 
                        st.session_state.km_col = col; break
                else: st.session_state.km_col = all_cols[min(2, len(all_cols)-1)]

            if 'time_col' not in st.session_state or st.session_state.time_col not in all_cols:
                for col in all_cols:
                    if any(k in str(col).upper() for k in ['HORA', 'TIME', 'SYSTEMTIME']): 
                        st.session_state.time_col = col; break
                else: st.session_state.time_col = all_cols[0]

            speed_col = st.session_state.speed_col
            km_col = st.session_state.km_col
            time_col = st.session_state.time_col

            # --- INTERVAL D'ANÀLISI ---
            st.markdown("### ⏲️ Interval d'Anàlisi")
            try:
                temp_time_series = pd.to_datetime(df[time_col], errors='coerce')
                min_t = temp_time_series.min().time() if not temp_time_series.isnull().all() else datetime.min.time()
                max_t = temp_time_series.max().time() if not temp_time_series.isnull().all() else datetime.max.time()
                
                f1, f2 = st.columns(2)
                start_time = f1.time_input("Inici d'anàlisi:", value=min_t)
                end_time = f2.time_input("Final d'anàlisi:", value=max_t)
                
                mask = (temp_time_series.dt.time >= start_time) & (temp_time_series.dt.time <= end_time)
                analysis_df = df.loc[mask].reset_index(drop=True)
            except Exception:
                st.warning("⚠️ No s'ha pogut filtrar per temps. Mostrant dades completes.")
                analysis_df = df

            # --- CÀLCUL I MOSTRA DE KPIS (BASATS EN EL FILTRE ACTUAL) ---
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
            k_cols = st.columns(3)
            with k_cols[0]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">🚀 Velocitat Màxima</div><div class="kpi-value">{val_speed}<span class="kpi-unit">KM/H</span></div></div>', unsafe_allow_html=True)
            with k_cols[1]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">📏 Distància Total</div><div class="kpi-value">{val_dist_m}<span class="kpi-unit">METRES</span></div></div>', unsafe_allow_html=True)
            with k_cols[2]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">📅 Timestamp Inici</div><div class="kpi-value">{val_time}<span class="kpi-unit">REF</span></div></div>', unsafe_allow_html=True)
            
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

            # Inicialització del multiselect si no té valors
            if 'selected_vars' not in st.session_state or not st.session_state.selected_vars:
                st.session_state.selected_vars = all_cols[:8]

            # Ús de 'key' directe per evitar el bug del doble clic
            selected_vars = st.multiselect(
                "Variables actives (Telemetria):", 
                options=all_options, 
                key="selected_vars", 
                format_func=variable_formatter
            )

            # --- INTERVAL D'ANÀLISI ---
            st.markdown("### ⏲️ Interval d'Anàlisi")
            try:
                temp_time_series = pd.to_datetime(df[time_col], errors='coerce')
                min_t = temp_time_series.min().time() if not temp_time_series.isnull().all() else datetime.min.time()
                max_t = temp_time_series.max().time() if not temp_time_series.isnull().all() else datetime.max.time()
                
                f1, f2 = st.columns(2)
                start_time = f1.time_input("Inici d'anàlisi:", value=min_t)
                end_time = f2.time_input("Final d'anàlisi:", value=max_t)
                
                mask = (temp_time_series.dt.time >= start_time) & (temp_time_series.dt.time <= end_time)
                analysis_df = df.loc[mask].reset_index(drop=True)
            except Exception:
                st.warning("⚠️ No s'ha pogut filtrar per temps. Mostrant dades completes.")
                analysis_df = df

            # Re-càlcul de valors per als KPIs (ara basats en l'interval filtrat)
            if not analysis_df.empty:
                # Assegurem conversió numèrica per evitar TypeError amb strings
                analysis_df[speed_col] = pd.to_numeric(analysis_df[speed_col], errors='coerce').fillna(0)
                analysis_df[km_col] = pd.to_numeric(analysis_df[km_col], errors='coerce').fillna(0)
                
                val_speed = f"{analysis_df[speed_col].max():.1f}"
                dist_raw = float(analysis_df[km_col].max() - analysis_df[km_col].min())
                val_dist_m = f"{abs(dist_raw) * 1000 if abs(dist_raw) < 150 else abs(dist_raw):,.0f}"
                first_ts = str(analysis_df[time_col].iloc[0])
                val_time = first_ts.split(" ")[-1][:8] if " " in first_ts else first_ts[:8]
            else:
                val_speed, val_dist_m, val_time = "0.0", "0", "--:--"

            # --- RE-RENDER KPIS (DALT) ---
            # Nota: Streamlit no permet moure components cap amunt fàcilment sense 'placeholder' 
            # però com que ja s'han printat al principi de la secció del fitxer, aquí només ens assegurem
            # que tinguin les dades del filtratge si cal. Per mantenir simplicitat i complir "sempre actius":
            # Hem Mogut el càlcul a l'inici del bloc del fitxer (a dalt).

            # --- GRÀFIC TELEMÈTRIC ---
            st.subheader("📊 Telemetria en Temps Real")
            fig = go.Figure()
            fill_c = "rgba(0, 210, 255, 0.12)" if st.session_state.theme_mode == "FOSC (Cockpit)" else "rgba(0, 82, 163, 0.12)"
            fig.add_trace(go.Scatter(x=analysis_df[time_col], y=analysis_df[speed_col], line={'color': t['primary'], 'width': 3}, fill='tozeroy', fillcolor=fill_c, name="Velocitat"))
            
            # Afegeix altres variables seleccionades al gràfic si n'hi ha
            for extra_v in selected_vars:
                if extra_v not in [speed_col, km_col, time_col] and extra_v in analysis_df.columns:
                    fig.add_trace(go.Scatter(x=analysis_df[time_col], y=analysis_df[extra_v], name=extra_v, line={'width': 1.5}, opacity=0.7))

            grid_c = 'rgba(255,255,255,0.05)' if t['plotly_template'] == 'plotly_dark' else 'rgba(0,0,0,0.05)'
            fig.update_layout(template=t['plotly_template'], paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin={'l': 0, 'r': 0, 't': 40, 'b': 0}, height=450, hovermode="x unified", xaxis={"gridcolor": grid_c, "zeroline": False}, yaxis={"gridcolor": grid_c, "zeroline": False})
            st.plotly_chart(fig, use_container_width=True)

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
                    
                    plt.plot(rep_x, rep_y, color=t['primary'], linewidth=2)
                    plt.title(f"Telemetria Serie FGC {st.session_state.current_unit}")
                    plt.grid(True, alpha=0.1)
                    
                    # Limitem la densitat de labels per a l'informe si hi ha moltes dades
                    if len(rep_x) > 10:
                        indices = np.linspace(0, len(rep_x)-1, 10).astype(int)
                        plt.xticks(indices, [rep_x.iloc[i] for i in indices], rotation=45)
                    else:
                        plt.xticks(rotation=45)
                    
                    chart_buf = io.BytesIO()
                    plt.savefig(chart_buf, format='png', bbox_inches='tight')
                    plt.close()
                    
                    blocks = segment_by_blocks(analysis_df, speed_col=str(speed_col))
                    all_kpis = [calculate_kpis(b, km_col=str(km_col), speed_col=str(speed_col), time_col=str(time_col)) for b in blocks]
                    
                    doc_buf = generate_word_report(analysis_df, all_kpis, {"motiu": f"Anàlisi {st.session_state.current_unit}"}, chart_img=chart_buf.getvalue(), notes=notes)
                    st.download_button("📥 DESCARREGAR INFORME", data=doc_buf, file_name=f"Informe_FGC_{current_key}.docx")

        except Exception as e:
            st.error(f"⚠️ Error Crític: {e}")
            st.exception(e)
    else:
        st.markdown('<br><div class="glass-panel" style="text-align: center; border-color: var(--primary);"><h2>SISTEMA EN ESPERA</h2><p style="color: var(--primary); font-weight: 700; letter-spacing: 0.2em;">>>> CARREGUEU TELEMETRIA PER INICIAR EL COCKPIT <<<</p></div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
