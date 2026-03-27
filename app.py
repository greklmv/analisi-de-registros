import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
from src.data_processing import load_data, segment_by_blocks, calculate_kpis, get_suggested_mapping, load_mappings  # type: ignore
from src.report_generator import generate_word_report  # type: ignore
import io
import time
from datetime import datetime

# --- CONFIGURACIÓ DE LA PÀGINA ---
st.set_page_config(
    page_title="FGC | Analista OTMR Pro v4.2",
    page_icon="🚆",
    layout="wide",
)

# --- ESTILS PREMIUM (PROFESSIONAL WORKSPACE - LIGHT MODE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;800&display=swap');

    :root {
        --primary: #0052A3;
        --primary-container: #d6e3ff;
        --surface: #F7F8F9;
        --surface-container-low: #FFFFFF;
        --surface-container: #FFFFFF;
        --surface-container-high: #f0f2f5;
        --surface-container-highest: #e0e5eb;
        --on-surface: #191c1e;
        --on-surface-variant: #43474e;
        --outline-variant: rgba(0, 82, 163, 0.1);
        --error: #ba1a1a;
    }

    .main { background-color: var(--surface) !important; color: var(--on-surface); font-family: 'Inter', sans-serif; }
    [data-testid="stAppViewContainer"] { background-color: var(--surface); }
    [data-testid="stSidebar"] { background-color: var(--surface-container-low); border-right: 1px solid var(--surface-container-highest) !important; }

    h1 { font-family: 'Manrope', sans-serif !important; font-weight: 800 !important; letter-spacing: -0.03em !important; color: var(--on-surface); font-size: 2.5rem !important; }
    h2, h3, .stSubheader { font-family: 'Manrope', sans-serif !important; font-weight: 600 !important; letter-spacing: -0.01em !important; color: var(--primary); }

    .cockpit-card { background-color: var(--surface-container); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--surface-container-highest) !important; box-shadow: 0 2px 8px rgba(0,0,0,0.04); transition: all 0.2s ease; margin-bottom: 1rem; }
    .cockpit-card:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
    .kpi-label { font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.7rem; color: var(--on-surface-variant); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.25rem; }
    .kpi-value { font-family: 'Manrope', sans-serif; font-size: 2.25rem; font-weight: 800; color: var(--primary); line-height: 1; }
    .kpi-unit { font-size: 0.85rem; font-weight: 500; color: var(--on-surface-variant); margin-left: 4px; }
    .glass-panel { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); border-radius: 12px; padding: 2.5rem; border: 1px solid var(--surface-container-highest); box-shadow: 0 10px 30px rgba(0,0,0,0.05); }

    .stButton>button { background: var(--primary) !important; color: #FFFFFF !important; border-radius: 6px !important; border: none !important; font-family: 'Inter', sans-serif !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; padding: 0.6rem 1.2rem !important; transition: all 0.3s ease !important; }
    .status-badge { display: inline-flex; align-items: center; gap: 8px; background-color: var(--primary-container); padding: 6px 14px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; color: var(--primary); }
    .pulse-dot { width: 8px; height: 8px; background-color: var(--primary); border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { transform: scale(0.95); opacity: 0.5; } 50% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(0.95); opacity: 0.5; } }

    /* Custom styles for tables */
    .stDataFrame { border-radius: 8px; border: 1px solid var(--surface-container-highest) !important; }
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def main():
    if 'selected_vars' not in st.session_state: st.session_state.selected_vars = []
    if 'current_unit' not in st.session_state: st.session_state.current_unit = "UT 113-114"

    # --- HEADER ---
    st.markdown('<div style="padding-top: 1.5rem;"></div>', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([0.7, 0.3])
    with h_col1:
        st.markdown("# ANALISTA OTMR")
        st.markdown('<p class="stCaption" style="color: var(--primary); font-weight: 600;">ORCHESTRATION SYSTEM v4.2 | PROTOCOL AVANÇAT</p>', unsafe_allow_html=True)
    with h_col2:
        st.markdown(f'<div style="text-align: right; padding-top: 1rem;"><div class="status-badge"><div class="pulse-dot"></div> EN_LÍNIA</div></div>', unsafe_allow_html=True)

    st.markdown('<div style="margin-bottom: 2rem; border-bottom: 1px solid var(--surface-container-highest);"></div>', unsafe_allow_html=True)

    # --- SIDEBAR ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/4/4b/FGC_original_logo.svg", width=120)
    st.sidebar.markdown("### 📁 Control de Registres")
    uploaded_file = st.sidebar.file_uploader("", type=["xlsx", "xls", "csv", "pdf"], label_visibility="collapsed")
    unit_model = st.sidebar.selectbox("Model d'Unitat de Tren:", options=["UT 113-114", "UT 112", "UT 115"], index=1 if st.session_state.current_unit == "UT 112" else 0)
    st.session_state.current_unit = unit_model
    demo_mode = st.sidebar.toggle("Mode Demo (Simulació)", value=False)
    
    final_file = uploaded_file if not (demo_mode and not uploaded_file) else "MOCK_FGC"

    if final_file:
        try:
            df = load_data(final_file)
            all_cols = df.columns.tolist()
            
            # --- SECTION 1: VARIABLE CORE ---
            st.subheader("🎯 Configuració de Senyals i Protocol")
            
            suggested_mapping = get_suggested_mapping(all_cols, unit_model=st.session_state.current_unit)
            if suggested_mapping:
                with st.expander(f"✨ Protocol {st.session_state.current_unit} Detectat de forma automática", expanded=True):
                    if st.button("🪄 Automatitzar Mapeig i Diccionari"):
                        st.session_state.selected_vars = list(suggested_mapping.keys())
                        st.rerun()

            # --- DROPDOWN CON TODAS LAS VARIABLES DEL MANUAL ---
            mappings = load_mappings()
            unit_vars = mappings.get(st.session_state.current_unit, {})
            
            # Unimos las del manual con las detectadas en el archivo
            all_options = list(unit_vars.keys()) + [c for c in all_cols if c not in unit_vars]
            
            def variable_formatter(opt):
                if opt in unit_vars:
                    return f"{opt}: {unit_vars[opt]}"
                return opt

            valid_defaults = [v for v in st.session_state.selected_vars if v in all_options] or all_cols[:8]
            selected_vars = st.multiselect("Variables actives al bus de dades:", options=all_options, default=valid_defaults, format_func=variable_formatter)

            if selected_vars:
                # Nos aseguramos de acceder solo a columnas que realmente existen en el archivo
                valid_selected = [v for v in selected_vars if v in df.columns]
                
                if not valid_selected:
                    st.warning("Cap de les variables seleccionades s'ha trobat en el fitxer. Utilitzant mapeig suggerit...")
                    valid_selected = all_cols[:8]
                
                filtered_df = df[valid_selected].copy()
                
                # Intelligent Column Mapping
                def_speed, def_km, def_time = 0, 0, 0
                for i, col in enumerate(selected_vars):
                    c_up = str(col).upper()
                    if 'VELOCIDAD' in c_up or 'SPEED' in c_up: def_speed = i
                    if 'DISTANCIA' in c_up or 'KM' in c_up: def_km = i
                    if 'HORA' in c_up or 'FECHA' in c_up or 'TIME' in c_up: def_time = i

                r1, r2, r3 = st.columns(3)
                with r1: speed_col = st.selectbox("Velocitat:", selected_vars, index=def_speed)
                with r2: km_col = st.selectbox("Distància:", selected_vars, index=def_km)
                with r3: time_col = st.selectbox("Timestamp:", selected_vars, index=def_time)

                # --- FILTRE TEMPORAL ---
                st.markdown("### ⏲️ Selecció d'Interval d'Anàlisi")
                try:
                    # Intentar convertir timestamps a datetime para obtener límites
                    sample_time = pd.to_datetime(filtered_df[time_col].iloc[0], errors='coerce')
                    min_time = datetime.strptime("00:00:00", "%H:%M:%S").time()
                    max_time = datetime.strptime("23:59:59", "%H:%M:%S").time()
                    
                    f1, f2, f3 = st.columns(3)
                    
                    if 'start_t_val' not in st.session_state: st.session_state.start_t_val = min_time
                    if 'end_t_val' not in st.session_state: st.session_state.end_t_val = max_time
                    
                    with f1: sel_date = st.date_input("Dia del Registre:", sample_time.date() if pd.notnull(sample_time) else datetime.now().date(), format="DD-MM-YYYY")
                    with f2: start_time = st.time_input("Inici d'anàlisi:", value=st.session_state.start_t_val, key="start_t_input")
                    with f3: end_time = st.time_input("Final d'anàlisi:", value=st.session_state.end_t_val, key="end_t_input")
                    
                    if st.button("🔄 Restablir Interval (Buidar Horari)"):
                        st.session_state.start_t_input = min_time
                        st.session_state.end_t_input = max_time
                        st.rerun()
                    
                    # Filtrado (usando una serie temporal temporal sin sobrescribir la original)
                    temp_time_series = pd.to_datetime(filtered_df[time_col], errors='coerce')
                    mask = (temp_time_series.dt.time >= start_time) & (temp_time_series.dt.time <= end_time)
                    filtered_df = filtered_df.loc[mask].reset_index(drop=True)
                except Exception as e:
                    st.warning("No s'ha pogut aplicar el filtre temporal automàtic. Verifica el format de la columna d'hora.")

                # --- SANITIZATION ---
                filtered_df[speed_col] = pd.to_numeric(filtered_df[speed_col], errors='coerce').fillna(0)
                filtered_df[km_col] = pd.to_numeric(filtered_df[km_col], errors='coerce').fillna(0)
                
                # --- CALCULATION ---
                blocks = segment_by_blocks(filtered_df, speed_col=str(speed_col))
                all_kpis = [calculate_kpis(b, km_col=str(km_col), speed_col=str(speed_col), time_col=str(time_col)) for b in blocks]
                all_kpis = [k for k in all_kpis if k is not None]

                # --- MARCADORES KPI (FILTRADOS) ---
                k_cols = st.columns(3)
                total_anomalies = sum(k.get('anomalies', 0) for k in all_kpis)
                
                if not filtered_df.empty:
                    val_speed = f"{filtered_df[speed_col].max():.1f}"
                    # Detectamos si la columna de distancia está en metros (m) para convertir a KM
                    desc = variable_formatter(km_col).lower()
                    km_col_low = str(km_col).lower()
                    
                    dist_raw = float(filtered_df[km_col].max() - filtered_df[km_col].min())
                    
                    # Heurística agresiva: Si detectamos metros en la descripción, el nombre, 
                    # o si el valor es sospechosamente alto para un trayecto de FGC (> 100 km)
                    is_meters = "(m)" in desc or "dist" in km_col_low or dist_raw > 150
                    
                    if is_meters:
                        final_dist_val = dist_raw / 1000
                    else:
                        final_dist_val = dist_raw
                        
                    val_dist = f"{final_dist_val:.2f}"
                    # Debug en modo expander si se desea revisar
                    with st.expander("🔍 Detalls del càlcul de Distància", expanded=False):
                        st.write(f"Columna: {km_col}")
                        st.write(f"Valor Brut (max-min): {dist_raw}")
                        st.write(f"Detecció de Metres: {'SÍ' if is_meters else 'NO'}")
                        st.write(f"Motiu Detecció: {'Descr (m)' if '(m)' in desc else 'Nom (dist)' if 'dist' in km_col_low else 'Magnitud (>150)' if dist_raw > 150 else 'Cap'}")
                else:
                    val_speed = "0.0"
                    val_dist = "0.00"
                
                with k_cols[0]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">Màxima</div><div class="kpi-value">{val_speed}<span class="kpi-unit">KM/H</span></div></div>', unsafe_allow_html=True)
                with k_cols[1]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">Distància</div><div class="kpi-value">{val_dist}<span class="kpi-unit">KM</span></div></div>', unsafe_allow_html=True)
                with k_cols[2]: st.markdown(f'<div class="cockpit-card"><div class="kpi-label">Anomalies</div><div class="kpi-value" style="color: {"var(--error)" if total_anomalies > 0 else "var(--primary)"};">{total_anomalies}<span class="kpi-unit">ALERTA</span></div></div>', unsafe_allow_html=True)

                # --- TELEMETRY CHART ---
                st.subheader("📈 Telemetria Estesa i Anàlisi de Seguretat")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=filtered_df[time_col], y=filtered_df[speed_col], name="Velocitat", line={'color': '#0052A3', 'width': 3}, fill='tozeroy', fillcolor='rgba(0, 82, 163, 0.05)'))
                
                # Add anomaly markers
                anom_df = filtered_df[filtered_df[speed_col].diff().fillna(0) < -5]
                if not anom_df.empty:
                    fig.add_trace(go.Scatter(x=anom_df[time_col], y=anom_df[speed_col], mode='markers', name='Frenada Brusca', marker={'color': 'red', 'size': 10, 'symbol': 'x'}))

                fig.update_layout(template="plotly_white", margin={'l': 0, 'r': 0, 't': 40, 'b': 0}, height=450, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

                # --- REPORT NOTES ---
                st.markdown("---")
                st.subheader("🗞️ Generació d'Informe i Diagnòstic")
                notes = st.text_area("Observacions i Diagnòstic del Tècnic:", placeholder="Escriu aquí el resum de l'anàlisi per inyectar al Word...")

                if st.button("🔧 PROCESSAR I GENERAR INFORME OFICIAL"):
                    with st.spinner("Compilant informe amb gràfics..."):
                        # Prepare chart image for Word (using matplotlib for simplicity)
                        plt.figure(figsize=(10, 4), dpi=100)
                        plt.plot(filtered_df[time_col], filtered_df[speed_col], color='#0052A3', linewidth=2)
                        plt.title(f"Telemetria Serie FGC {st.session_state.current_unit}")
                        plt.xlabel("Temps")
                        plt.ylabel("km/h")
                        plt.grid(True, alpha=0.3)
                        
                        chart_buf = io.BytesIO()
                        plt.savefig(chart_buf, format='png', bbox_inches='tight')
                        plt.close()
                        
                        doc_buffer = generate_word_report(filtered_df, all_kpis, {"motiu": "Anàlisi OTMR v4.2"}, chart_img=chart_buf.getvalue(), notes=notes)
                        
                        st.download_button(label="📥 DESCARREGAR INFORME COMPLET", data=doc_buffer, file_name=f"FGC_OTMR_FINAL_REPORT.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        except Exception as e:
            st.error(f"⚠️ Error Crític: {e}")
            st.exception(e)
    else:
        st.markdown('<br><div class="glass-panel" style="text-align: center;"><h2>ESPERANT TELEMETRIA</h2><p>PROTOCOL ACTIU. Carregueu un fitxer original per iniciar l\'anàlisi.</p></div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
