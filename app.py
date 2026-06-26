import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
from datetime import datetime
import os
import base64
import io
from src.openrouter_client import analyze_with_ai, OpenRouterError
from src.ai_memory import load_memory, add_lesson, clear_memory
from src.data_processing import (
    load_data, calculate_kpis, get_suggested_mapping,
    load_mappings, get_minute_summary,
    get_all_stations_flat, get_event_based_summary, load_stations, get_closest_station,
    get_ai_context
)
from src.report_generator import generate_word_report
from src.config import VERSION, PALETTE
from src.update_checker import check_for_updates

# --- CONFIGURACIÓ DE LA PÀGINA ---
st.set_page_config(
    page_title=f"FGC | Analista OTMR Pro v{VERSION}",
    page_icon="🚆",
    layout="wide",
)

check_for_updates()

# --- TEMA I ESTILS ---
if 'theme_mode' not in st.session_state: st.session_state.theme_mode = "CLAR (Swiss)"

from src.ui_styles import inject_styles
from src.ui_components import render_network_schematic

logo_base64 = inject_styles()

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
        
        # Recargar los settings (límites físicos) con el perfil correcto
        from src.config import reload_settings
        reload_settings(unit_model)
        
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
        if rb_c1.button("🚉 Estacions", use_container_width=True): apply_rapid_vars("estacio")
        if rb_c1.button("🕹️ ATP/ATO", use_container_width=True): apply_rapid_vars("conduccio")
        if rb_c2.button("🛑 Senyals", use_container_width=True): apply_rapid_vars("senyal")
        if rb_c2.button("🧹 Neteja", use_container_width=True): 
            st.session_state.selected_vars = []
            st.rerun()

        if st.session_state.processed_data is not None:
            st.markdown("---")
            st.markdown("### 🕒 Filtre Temporal")
            df_full = st.session_state.processed_data
            t_col_temp = next((c for c in df_full.columns if any(k in str(c).upper() for k in ['TIME', 'HORA'])), df_full.columns[0])
            n_opts = len(df_full)
            if n_opts > 1:
                idx_s, idx_e = st.slider(
                    "Selecciona Rang Temporal:",
                    min_value=0,
                    max_value=n_opts - 1,
                    value=(0, n_opts - 1),
                    format="Punt %d",
                    key="time_range_slider"
                )
                time_s = df_full[t_col_temp].iloc[idx_s]
                time_e = df_full[t_col_temp].iloc[idx_e]
                st.caption(f"De: **{time_s}** a **{time_e}**")
                st.session_state.filtered_df = df_full.iloc[idx_s:idx_e+1]
            else:
                st.session_state.filtered_df = df_full
        else:
            st.session_state.filtered_df = None

    t = PALETTE
    st.markdown(f'''<div style="display:flex; justify-content:space-between; align-items:center;"><div><h1>ANALISTA OTMR <span style="color:{t["primary"]}">PRO</span></h1><p style="margin:0; font-size:0.8rem; color:{t["on_surface_variant"]}; font-weight:600; letter-spacing: 0.05em;">DEPARTAMENT OPERATIU - FERROCARRILS DE LA GENERALITAT DE CATALUNYA</p></div><div class="status-badge"><div class="pulse-dot"></div> MONITORITZACIÓ ACTIVA</div></div>''', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 🗺️ Context de l'Anàlisi")
    ctx_c1, ctx_c2, ctx_c3 = st.columns([1,1,1.2])
    with ctx_c1: st.selectbox("Tracks / Línia:", ["S1 (Terrassa)", "S2 (Sabadell)", "L6 (Sarrià)", "L7 (Tibidabo)", "L12 (RE)", "Totes"], key="active_line")
    with ctx_c2:
        if 'processed_data' in st.session_state and st.session_state.processed_data is not None:
            df_temp = st.session_state.processed_data
            km_col_temp = next((c for c in df_temp.columns if any(k in str(c).upper() for k in ['DIST', 'KM', 'PK'])), df_temp.columns[1] if len(df_temp.columns) > 1 else None)
            if km_col_temp:
                try:
                    start_km = float(df_temp[km_col_temp].iloc[0])
                    end_km = float(df_temp[km_col_temp].iloc[-1])
                    st.session_state.active_direction = "Ascendent" if end_km >= start_km else "Descendent"
                except (IndexError, KeyError, ValueError, TypeError):
                    st.session_state.active_direction = "Ascendent"
            else:
                st.session_state.active_direction = "Ascendent"
            st.info(f"🧭 Sentit: {st.session_state.active_direction}")
        else:
            st.selectbox("Sentit de la marxa:", ["Ascendent", "Descendent"], key="active_direction", disabled=True)
    
    st_options = ["Cap (Ús PK Absolut)"] + [s["display_name"] for s in get_all_stations_flat()]
    st_idx = st_options.index(st.session_state.selected_st_ui) if st.session_state.selected_st_ui in st_options else 0
    with ctx_c3: st.selectbox("📍 Origen (Calibratge PK):", st_options, index=st_idx, key="selectbox_st_ui", on_change=lambda: st.session_state.update(selected_st_ui=st.session_state.selectbox_st_ui))

    base_key = "DEMOFIX" if demo_mode else (uploaded_file.name if uploaded_file else None)
    key_id = f"{base_key}_{unit_model}" if base_key else None
    
    if key_id and (st.session_state.processed_data is None or key_id != st.session_state.last_loaded_key):
        df = load_data(uploaded_file if not demo_mode else "MOCK_FGC", train_type=unit_model)
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
        track = "Via1" if "Ascendent" in st.session_state.active_direction else "Via2"
        closest_sig, sig_dist = get_closest_signal(pk_abs, signals_data, track=track)
        next_sig_str = f"{closest_sig['id']} ({(sig_dist or 0)*1000:.0f}m)" if closest_sig else "---"

        from src.svg_component import interactive_svg
        svg_code = render_network_schematic(origin_id, pos_id, signals_data)
        clicked_station = interactive_svg(svg_code=svg_code, height=420, key="svg_map")

        if clicked_station and clicked_station != "RESET":
            all_st = get_all_stations_flat()
            found = next((s for s in all_st if s["id"] == clicked_station), None)
            if found and found["display_name"] != st.session_state.selected_st_ui:
                st.session_state.selected_st_ui = found["display_name"]
                st.rerun()

        st.markdown(f'<p style="text-align:center; font-weight:700; color:{t["primary"]}; margin-top:-20px; margin-bottom:25px; letter-spacing:0.02em;">📍 POSICIÓ ACTUAL: {closest}</p>', unsafe_allow_html=True)

        k_cols = st.columns(5)
        k_cols[0].markdown(f'<div class="cockpit-card"><div class="kpi-label">🚀 Velocitat</div><div class="kpi-value">{float(point[speed_col]):.1f}<span class="kpi-unit">KM/H</span></div></div>', unsafe_allow_html=True)
        k_cols[1].markdown(f'<div class="cockpit-card"><div class="kpi-label">📏 Posició PK</div><div class="kpi-value">{pk_abs:.3f}<span class="kpi-unit">KM</span></div></div>', unsafe_allow_html=True)
        
        dist_recorreguda = abs(float(point[km_col]) - float(df.iloc[0][km_col]))
        k_cols[2].markdown(f'<div class="cockpit-card"><div class="kpi-label">🛤️ Dist. Recorreguda</div><div class="kpi-value">{dist_recorreguda:.3f}<span class="kpi-unit">KM</span></div></div>', unsafe_allow_html=True)
        
        mode = "🤖 ATO" if (ato_col and point[ato_col]==1) else "⚙️ ATP"
        k_cols[3].markdown(f'<div class="cockpit-card"><div class="kpi-label">🕹️ Mode Actiu</div><div class="kpi-value" style="color:{"#10b981" if "ATO" in mode else t["primary"]}">{mode}</div></div>', unsafe_allow_html=True)
        k_cols[4].markdown(f'<div class="cockpit-card"><div class="kpi-label">🚦 Propera Senyal</div><div class="kpi-value">{next_sig_str}</div></div>', unsafe_allow_html=True)

        st.multiselect("Senyals de Control:", df.columns.tolist(), key="selected_vars_ui", default=st.session_state.selected_vars)
        st.session_state.selected_vars = st.session_state.selected_vars_ui
        
        from plotly.subplots import make_subplots
        fig = make_subplots(rows=2 if st.session_state.selected_vars else 1, shared_xaxes=True)
        
        # DOWNSAMPLING
        plot_df = df
        if len(plot_df) > 3000:
            step = len(plot_df) // 1500
            plot_df = plot_df.iloc[::step]
            
        fig.add_trace(go.Scatter(x=plot_df[time_col], y=plot_df[speed_col], name="Velocitat", line=dict(color=t["primary"], width=3), fill='tozeroy', fillcolor='rgba(141,237,236,0.1)'), row=1, col=1)
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
            track_key = "Via1" if "Ascendent" in st.session_state.active_direction else "Via2"
            active_signals = signals_data.get(track_key, signals_data)
            
            # Funció per iterar en qualsevol estructura (per seguretat)
            def plot_signals_recursive(data):
                if isinstance(data, list):
                    for sig in data:
                        if "pk_abs" not in sig: continue
                        spk = float(sig["pk_abs"])
                        if min(limit_pks) <= spk <= max(limit_pks):
                            closest_idx = (df[km_col] - spk).abs().idxmin()
                            sig_time = df.loc[closest_idx, time_col]
                            fig.add_vline(x=sig_time, line_width=1, line_dash="dash", line_color="#f59e0b", opacity=0.4)
                            fig.add_annotation(x=sig_time, y=10, text=f"{sig['id']}", showarrow=False, font=dict(size=8, color="#d97706"))
                elif isinstance(data, dict):
                    for v in data.values():
                        plot_signals_recursive(v)

            plot_signals_recursive(active_signals)

        for idx, v in enumerate(st.session_state.selected_vars):
            if v != speed_col: fig.add_trace(go.Scatter(x=plot_df[time_col], y=plot_df[v], name=str(v)), row=2, col=1)
        
        # Generar KPIs i Esdeveniments (pujat aquí per poder pintar anomalies al gràfic)
        kpis = calculate_kpis(df, str(km_col), str(speed_col), str(time_col))
        evs = get_event_based_summary(df, str(km_col), str(speed_col), str(time_col), starting_pk=(start_pk if start_pk is not None else 0), is_ascendant=("Ascendent" in st.session_state.active_direction))

        # Dibuixar Eventos Sombreados (Anomalías)
        try:
            for ev in evs:
                if ev.get("is_anomaly"):
                    # ev['time'] is 'HH:MM:SS'. We combine it with the date of the first record
                    base_date = pd.to_datetime(df[time_col].iloc[0]).strftime('%Y-%m-%d')
                    ev_time = pd.to_datetime(f"{base_date} {ev['time']}")
                    fig.add_vrect(
                        x0=ev_time - pd.Timedelta(seconds=10), 
                        x1=ev_time + pd.Timedelta(seconds=10),
                        fillcolor="red", opacity=0.15, layer="below", line_width=0,
                        annotation_text=ev["event"], annotation_position="top left",
                        annotation_font_size=10, annotation_font_color="red"
                    )
        except Exception as e:
            pass # Si falla el parseo de tiempo, no rompemos el gráfico
            
        fig.update_layout(height=450, margin=dict(l=0,r=0,t=20,b=0), legend=dict(orientation="h", y=1.05, x=1))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📋 Resum Operatiu")
        tab1, tab2, tab3 = st.tabs(["🚆 Esdeveniments", "📊 Log Detallat", "🤖 Assistent IA"])
        
        with tab1:
            st.dataframe(pd.DataFrame(evs), use_container_width=True, hide_index=True)
            
        with tab2:
            log = get_minute_summary(df, str(time_col), str(speed_col), str(km_col), extra_cols=st.session_state.selected_vars, starting_pk=(start_pk if start_pk is not None else 0), is_ascendant=("Ascendent" in st.session_state.active_direction))
            st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True)

        with tab3:
            st.markdown("#### 🧠 Intel·ligència Artificial Operativa")
            ai_ctx = get_ai_context(df, kpis, evs)
            memory = load_memory()
            
            if st.button("🪄 GENERAR DIAGNÒSTIC AUTOMÀTIC", use_container_width=True):
                with st.spinner("L'IA està analitzant el registre..."):
                    try:
                        diag = analyze_with_ai(ai_ctx, "Fes un diagnòstic detallat d'aquest viatge. Busca anomalies, sobrevelocitats o comportaments que requereixin atenció.", memory=memory)
                        st.session_state.ai_last_diag = diag
                        # Intentem omplir les observacions si estan buides
                        if not st.session_state.get('notes_text'):
                            st.session_state.notes_text = diag
                    except OpenRouterError as e:
                        st.error(f"⚠️ No s'ha pogut generar el diagnòstic IA: {e}")
            
            if 'ai_last_diag' in st.session_state:
                st.info(st.session_state.ai_last_diag)
                
                # Feedback per APRENENTATGE
                st.markdown("---")
                st.markdown("##### 👩‍🏫 Correcció d'Experts (Aprenentatge)")
                with st.expander("Vols millorar el coneixement de l'IA per a futurs anàlisis?"):
                    lesson = st.text_area("Si l'IA ha comès un error o vols que recordi una regla operativa per a aquest tram/unitat, escriu-la aquí:", placeholder="Exemple: 'Al PK 25.4 és normal un FU si hi ha proves de shunting'...")
                    if st.button("💾 Guarda Lliçó a la Memòria"):
                        if lesson:
                            add_lesson(lesson)
                            st.success("Lliçó guardada. L'IA la tindrà en compte en el pròxim anàlisi!")
                        else:
                            st.warning("Escriu alguna cosa per guardar.")
            else:
                st.write("Clica el botó superior per iniciar l'anàlisi intel·ligent.")

        st.markdown("---")
        # Ús de session_state per a les observacions per permetre auto-completat de l'IA
        if 'notes_text' not in st.session_state: st.session_state.notes_text = ""
        notes = st.text_area("Observacions Tècniques:", value=st.session_state.notes_text, placeholder="Afegiu detalls sobre qualsevol anomalia detectada...", height=150, key="notes_area")
        st.session_state.notes_text = notes # Sincronitzem

        if st.button("🔧 DESCARREGAR INFORME OFICIAL", use_container_width=True):
            with st.spinner("Generant Word..."):
                plt.figure(figsize=(10,4)); plt.plot(df[time_col], df[speed_col], color=t["primary"]); plt.grid(True, alpha=0.3)
                buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close()
                ai_conclusions = st.session_state.get('ai_last_diag')
                doc = generate_word_report(df, log, {"u":st.session_state.current_unit}, chart_img=buf.getvalue(), notes=notes, op_events=evs, ai_conclusions=ai_conclusions)
                st.download_button(
                    "📥 DESCARREGAR ARXIU", 
                    data=doc, 
                    file_name=f"Informe_FGC_{st.session_state.current_unit}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    else:
        st.markdown('<div style="text-align:center; padding:150px; opacity:0.4;"><h2>CARREGANT DADES...</h2><p>Pugeu un registre per començar l\'anàlisi operativa</p></div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
