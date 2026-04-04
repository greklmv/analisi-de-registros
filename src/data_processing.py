import pandas as pd  # type: ignore
import pdfplumber  # type: ignore  # type: ignore
import io
import json
import os
import numpy as np  # type: ignore
import streamlit as st  # type: ignore
from datetime import datetime, timedelta

def load_mappings(file_path="src/mappings.json"):
    """Load variable mappings from an external JSON file."""
    # Handle absolute path if within project
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base_dir, file_path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

@st.cache_data
def load_data(uploaded_file, sheet_name=0):
    """Suporta Excel, CSV, PDF o genera dades d'exemple amb caché."""
    if uploaded_file == "MOCK_FGC":
        return generate_mock_fgc_data()
        
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    if file_type in ['xlsx', 'xls']:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
    elif file_type == 'csv':
        df = pd.read_csv(uploaded_file)
    elif file_type == 'pdf':
        df = extract_from_pdf(uploaded_file)
    else:
        raise ValueError("Format de fitxer no compatible. Usa Excel o PDF.")
    
    # Normalització inicial de PK si existeix
    km_potential = next((c for c in df.columns if any(k in str(c).upper() for k in ['DISTANCIA', 'KM', 'X_UT', 'DIST_'])), None)
    if km_potential:
        df[km_potential] = pd.to_numeric(df[km_potential], errors='coerce').fillna(0)
    
    # Normalització inicial de columnes
    df.columns = [str(c).strip() for c in df.columns]
    return df

def load_stations(file_path="src/stations.json"):
    """Load train stations from an external JSON file and resolve absolute PKs."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base_dir, file_path)
    if not os.path.exists(full_path):
        return {}
        
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Resolució de PKs absoluta
        # 1. Crear mapa ràpid d'ID d'estació -> PK per a lookups d'origen
        id_to_pk = {}
        for section in data.values():
            for st in section.get("stations", []):
                # Inicialment només guardem els que no tenen origen o són de la secció principal
                if "origin" not in section:
                    id_to_pk[st["id"]] = st["pk"]

        # 2. Resoldre estacions amb origen (recursivament si calgués, però aquí usem 2 passades)
        resolved_data = {}
        for sec_id, section in data.items():
            stations = section.get("stations", []).copy()
            origin_id = section.get("origin")
            
            offset = 0.0
            if origin_id in id_to_pk:
                offset = id_to_pk[origin_id]
            
            for st in stations:
                st["pk_abs"] = st["pk"] + offset
                # Guardem a la memòria per a possibles sub-branques
                id_to_pk[st["id"]] = st["pk_abs"]
            
            resolved_data[sec_id] = section
        return resolved_data
    except Exception:
        return {}

def get_closest_station(pk, stations_data, line_filter=None):
    """Identifica l'estació més propera per a un PK determinat amb precisió técnica, opcionalment filtrant per línia."""
    if not stations_data:
        return "Tram Obert"
    
    best_station = None
    min_dist = float('inf')
    
    # Busquem l'estació amb el PK més proper
    for sec_id, line_info in stations_data.items():
        # Si hi ha filtre i aquesta secció no és part de la línia activa, la ignorem
        if line_filter and sec_id not in line_filter:
            continue
            
        for st in line_info.get("stations", []):
            st_pk = float(st.get("pk_abs", st.get("pk", 0)))
            dist = pk - st_pk # Diferència real (positiva si hem passat l'estació)
            abs_dist = abs(dist)
            
            if abs_dist < min_dist:
                min_dist = abs_dist
                best_station = {
                    "id": st.get("id", "---"),
                    "name": st.get("name", "---"),
                    "pk": st_pk,
                    "diff": dist
                }
    
    if not best_station:
        return "Tram Obert"
    
    dist_m = best_station["diff"] * 1000
    abs_dist_m = abs(dist_m)
    
    if abs_dist_m < 25: # Umbral de parada en andana (25m)
        return f"Aturat a {best_station['name']} ({best_station['id']})"
    elif dist_m > 0:
        return f"Rebassat {best_station['name']} (+{abs_dist_m:.0f} m)"
    else:
        return f"Arribant a {best_station['name']} (-{abs_dist_m:.0f} m)"

def get_all_stations_flat():
    """Retorna una llista plana de totes les estacions per al selector de la UI."""
    data = load_stations()
    flat_list = []
    for section in data.values():
        for st in section.get("stations", []):
            st["display_name"] = f"{st['name']} ({st['id']}) - PK {st.get('pk_abs', st['pk']):.3f}"
            flat_list.append(st)
    # Sort by PK abs
    return sorted(flat_list, key=lambda x: x.get("pk_abs", 0))

def get_sheet_names(uploaded_file):
    """Obté els noms de les fulles d'un fitxer Excel."""
    file_type = uploaded_file.name.split('.')[-1].lower()
    if file_type in ['xlsx', 'xls']:
        try:
            xl = pd.ExcelFile(uploaded_file)
            return xl.sheet_names
        except Exception:
            return []
    return []

def get_suggested_mapping(columns, unit_model="UT 113-114"):
    """Retorna un mapeig suggerit amb normalització avanzada y cerca de subcadenes."""
    mappings = load_mappings()
    base_mapping = dict(mappings.get(unit_model, {}))
    
    def normalize(s):
        # Remove common units and separators
        return str(s).strip().upper().replace('‑', '-').replace('_', '').replace(' ', '').replace('(KM/H)', '').replace('(M)', '')

    normalized_base = {normalize(k): v for k, v in base_mapping.items()}
    
    final_mapping: dict = {}
    for col in columns:
        col_norm = normalize(col)
        # Búsqueda por subcadena: si el nombre corto está dentro del nombre de la columna real
        for k_norm, v in normalized_base.items():
            if k_norm in col_norm or col_norm in k_norm:
                final_mapping[col] = f"{col}: {v}"
                break
    return final_mapping

@st.cache_data
def extract_from_pdf(uploaded_file):
    """Extract tables or fixed-width text from PDF using pdfplumber."""
    import re
    with pdfplumber.open(uploaded_file) as pdf:
        all_dfs = []
        for page in pdf.pages:
            # 1. Intentar extraure taula (Sèries 113/114 amb línies)
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    if not table: continue
                    df_cols = [str(c).replace('\n', ' ').strip() if c is not None else f"Column_{i}" for i, c in enumerate(table[0])]
                    df_tmp = pd.DataFrame(table[1:], columns=df_cols)
                    all_dfs.append(df_tmp)
            
            # 2. Intentar parseig de text (Sèrie 112 / Fixed-width)
            text = page.extract_text()
            if text:
                # Patró: DD/MM/YY - HH:MM:SS (Data) Distància (Dígits) Valor (Dígits.Decimal)
                pattern = r"(\d{2}/\d{2}/\d{2} - \d{2}:\d{2}:\d{2})\s+(\d+)\s+([\d\.]+)"
                matches = re.findall(pattern, text)
                if matches:
                    df_txt = pd.DataFrame(matches, columns=['Fecha - Hora', 'Distancia', 'AAA'])
                    all_dfs.append(df_txt)
        
        if not all_dfs:
            raise ValueError("No s'han trobat dades vàlides al PDF.")
        
        final_df = pd.concat(all_dfs, ignore_index=True)
        
        # NETEJA CRÍTICA: Eliminar files de "Llengenda" o capçaleres intermèdies
        # Detectem la columna de temps (la més probable) i filtrem les files que no tinguin format de data
        time_potential = next((c for c in final_df.columns if any(k in str(c).upper() for k in ['HORA', 'FECHA', 'TIME'])), None)
        if time_potential:
            # Manté només les files on el temps realment sembla una data
            mask = final_df[time_potential].astype(str).str.contains(r'\d{2}/\d{2}/\d{2}', na=False)
            final_df = final_df[mask].reset_index(drop=True)
            
        # Eliminar columnes completament buides (com les de les llegendes descartades)
        final_df = final_df.dropna(axis=1, how='all')
            
        return final_df

def normalize_distance(df, km_col):
    """Detecta si la distancia está en KM o Metros y normaliza a Metros."""
    if km_col not in df.columns:
        return df
    
    vals = pd.to_numeric(df[km_col], errors='coerce').fillna(0)
    # Heurística: Si el máximo es < 1000 y el delta es pequeño, probablemente sean KM
    # Si el valor promedio es > 5000, probablemente sean metros (odómetro)
    if vals.max() < 2000 and (vals.max() - vals.min()) < 150:
        df[f"{km_col}_M"] = vals * 1000
    else:
        df[f"{km_col}_M"] = vals
    return df

def segment_by_blocks(df, speed_col='Velocitat'):
    """Split the trip into operational blocks based on stops."""
    if speed_col not in df.columns:
        return [df]
    
    df[speed_col] = pd.to_numeric(df[speed_col], errors='coerce').fillna(0)
    
    blocks = []
    current_block = []
    
    # Algoritmo de segmentación mejorado
    for _, row in df.iterrows():
        current_block.append(row)
        # Si el tren está parado por más de 5 registros, cerramos bloque
        if row[speed_col] == 0:  # type: ignore
            # Miramos atrás (si ya hay suficientes datos)
            if len(current_block) > 10:
                blocks.append(pd.DataFrame(current_block))  # type: ignore
                current_block = []
            
    if current_block:
        blocks.append(pd.DataFrame(current_block))
        
    return [b for b in blocks if not b.empty]

def get_minute_summary(df, time_col='Hora', speed_col='Velocitat', km_col='KM', extra_cols=None, starting_pk=None, line_filter=None, is_ascendant=True):
    """Agrupa les dades en blocs per minut amb seguiment de PK absoluta basat en estació d'origen i sentit de marxa."""
    if df.empty: return []
    if extra_cols is None: extra_cols = []
    
    # Pre-càlcul del valor inicial d'odòmetre per a increments relatius
    try:
        initial_odometer = float(df[km_col].iloc[0])
    except:
        initial_odometer = 0.0

    df_temp = df.copy()
    df_temp[speed_col] = pd.to_numeric(df_temp[speed_col], errors='coerce').fillna(0)
    df_temp[km_col] = pd.to_numeric(df_temp[km_col], errors='coerce').fillna(0)
    
    df_temp[time_col] = pd.to_datetime(df_temp[time_col], errors='coerce')
    df_temp = df_temp.set_index(time_col)
    
    resampled = df_temp.resample('1min')
    
    summary = []
    total_acc_dist: float = 0.0
    last_states = {}
    stations_data = load_stations()
    
    for timestamp, block in resampled:
        if block is None or block.empty: continue
        
        max_v = block[speed_col].max()
        avg_v = block[speed_col].mean()
        
        ut_raw = float(block[km_col].iloc[0])
        ut_val = f"{ut_raw * 1000 if ut_raw < 150 else ut_raw:,.1f}"
        
        # Detecció de la ubicació (estació) amb el nou sistema PK i sentit (Ascendent/Descendent)
        if starting_pk is not None:
            # PK = PK Origen +/- (Distància Acumulada / 1000) depenent del sentit
            dist_km = (total_acc_dist / 1000)
            current_pk = (starting_pk + dist_km) if is_ascendant else (starting_pk - dist_km)
        else:
            current_pk = ut_raw if ut_raw < 150 else ut_raw / 1000
            
        loc_name = get_closest_station(current_pk, stations_data, line_filter=line_filter)
        
        # Distància d'aquest minut (delta real entre registres per evitar salts de l'odòmetre)
        delta_km = abs(block[km_col].max() - block[km_col].min())
        delta_m = delta_km * 1000 if delta_km < 150 else delta_km
        
        # Alertes telemètriques...
        alerts = []
        if max_v > 90: alerts.append(f"🔴 EXCÉS VELOCITAT ({max_v:.1f} km/h)")
        
        # ... resta d'alertes ... (mantenir la lògica original de canvis d'estat)
        
        v_diff = block[speed_col].diff().fillna(0)
        # Deceleració mitjana en m/s² (aprox)
        decel = (v_diff / 3.6).mean() 
        if any(v_diff < -7): alerts.append("⚠️ FRENADA BRUSCA")
        
        # DE-DUPLICATED: Roll-back detection now happens at minute summary level
        
        # DETECCIÓ DE CANVIS D'ESTAT (0 <-> 1) en variables seleccionades
        extra_data = {}
        for col in extra_cols:
            if col in [speed_col, km_col, str(time_col)]: continue
            
            col_series = block[col]
            # Filtre de seguretat: Només detectem canvis en variables DIGITALS (0 o 1)
            unique_vals = set(col_series.dropna().unique())
            is_digital = unique_vals.issubset({0, 1, 0.0, 1.0, '0', '1', 0.0})
            if not is_digital: continue
            
            # Busquem l'estat inicial real (el primer no-NaN)
            current_state = last_states.get(col)
            if pd.isna(current_state):
                first_valid = col_series.dropna()
                current_state = first_valid.iloc[0] if not first_valid.empty else np.nan
            
            changes_in_block = []
            for val in col_series:
                if pd.isna(val) or pd.isna(current_state) or val == current_state:
                    if pd.isna(current_state) and not pd.isna(val):
                        current_state = val # Establir línia base si veníem de NaN
                    continue
                
                # Només si tenim un valor real i és diferent de l'anterior
                emoji = "⬆️" if str(val) == "1" else "⬇️"
                changes_in_block.append(f"CANVI {col}: {current_state} {emoji} {val}")
                current_state = val
            
            # Guardem l'últim estat per al següent minut
            last_states[col] = current_state
            
            if changes_in_block:
                # Si hi ha hagut canvis, els afegim a les alertes del minut
                alerts.extend(changes_in_block)

            # Igualment guardem el valor mitjà/mode per a la visualització
            try:
                if pd.api.types.is_numeric_dtype(col_series):
                    extra_data[f"var_{col}"] = f"{col_series.mean():.1f}"
                else:
                    extra_data[f"var_{col}"] = str(col_series.mode().iloc[0]) if not col_series.mode().empty else "---"
            except Exception:
                extra_data[f"var_{col}"] = "---"

        # Detecció de ROLL-BACK a nivell de fila per a les dades del minut
        km_diff = block[km_col].diff().fillna(0)
        has_rb = any((km_diff < -0.001) & (block[speed_col] > 1))
        if has_rb:
            alerts.append("🔄 ROLL-BACK")

        row = {
            "start_time": pd.to_datetime(timestamp).strftime('%H:%M'),
            "location": loc_name,
            "ut_indicator": ut_val, 
            "distance": f"{total_acc_dist:,.1f} m", 
            "max_speed": f"{max_v:.1f}",
            "avg_speed": f"{avg_v:.1f}",
            "anomalies": ", ".join(alerts) if alerts else "",
            "speed_history": block[speed_col].tolist(),
            "has_rollback": has_rb,
            "count": len(block)
        }
        row.update(extra_data)
        summary.append(row)
        total_acc_dist = float(total_acc_dist) + float(delta_m)  # type: ignore
        
    return summary

def get_event_based_summary(df, km_col, speed_col, time_col, starting_pk=0, line_filter=None, is_ascendant=True):
    """
    Genera un resum d'esdeveniments operatius: Sortides i Estacionaments.
    Ideal per al resum executiu net.
    """
    if df.empty: return []
    
    # Carreguem dades estacions
    stations_data = load_stations()
    
    # 1. Definir estats: 0 = Parat, 1 = Moviment
    df_state = df.copy()
    df_state['is_moving'] = (df_state[speed_col] > 2).astype(int) # Llindar de 2 km/h
    
    # 2. Agrupar estats contigus
    df_state['state_change'] = df_state['is_moving'].diff().fillna(0).abs()
    df_state['group'] = df_state['state_change'].cumsum()
    
    events = []
    groups = df_state.groupby('group')
    
    init_km = df_state[km_col].iloc[0]
    
    for i, (name, group) in enumerate(groups):
        if group.empty: continue
        
        is_moving = group['is_moving'].iloc[0] == 1
        start_time = pd.to_datetime(group[time_col].iloc[0]).strftime('%H:%M:%S')
        
        rel_m = (group[km_col].mean() - init_km) * 1000
        dist_km = (rel_m / 1000)
        current_pk = (starting_pk if starting_pk is not None else init_km) + (dist_km if is_ascendant else -dist_km)
        
        # Buscar estació més propera (filatrada per línia)
        st_info_str = get_closest_station(current_pk, stations_data, line_filter=line_filter)
        loc_name = st_info_str if st_info_str else "Tram Obert"
        
        try:
            t1 = pd.to_datetime(group[time_col].iloc[0])
            t2 = pd.to_datetime(group[time_col].iloc[-1])
            duration_sec = (t2 - t1).total_seconds()
        except: duration_sec = 0
            
        if not is_moving:
            if duration_sec > 10:
                events.append({
                    "time": start_time,
                    "event": f"🅿️ Estacionat a {loc_name}",
                    "details": f"Aturat durant {int(duration_sec)}s (PK {current_pk:.3f})",
                    "pk": current_pk
                })
        else:
            # Mode de Conducció Predominant
            mode_l = "ATP"
            atp_sub = next((c for c in group.columns if "ATP" in str(c).upper()), None)
            ato_sub = next((c for c in group.columns if "ATO" in str(c).upper()), None)
            if atp_sub and ato_sub:
                if (group[ato_sub] == 1).sum() > (group[atp_sub] == 1).sum(): mode_l = "ATO"

            if i > 0:
                events.append({
                    "time": start_time,
                    "event": f"🚀 Sortida ({mode_l}) de {loc_name}",
                    "details": f"Velocitat màx: {group[speed_col].max():.1f} km/h (PK {current_pk:.3f})",
                    "pk": current_pk,
                    "mode": mode_l
                })
            else:
                events.append({
                    "time": start_time,
                    "event": f"🚄 En circulació {mode_l} (inici)",
                    "details": f"Passant per {loc_name} (PK {current_pk:.3f})",
                    "pk": current_pk,
                    "mode": mode_l
                })

    return events

def calculate_kpis(df, km_col='KM', speed_col='Velocitat', time_col='Hora'):
    """Calculate KPIs with real time diffs and anomaly detection."""
    try:
        cols = df.columns
        if km_col not in cols or speed_col not in cols:
            return None
        
        # Conversió a numèric per seguretat
        df[speed_col] = pd.to_numeric(df[speed_col], errors='coerce').fillna(0)
        df[km_col] = pd.to_numeric(df[km_col], errors='coerce').fillna(0)
        
        raw_start_km = float(df[km_col].iloc[0])
        raw_end_km = float(df[km_col].iloc[-1])
        
        if time_col in cols:
            start_t = pd.to_datetime(df[time_col].iloc[0], errors='coerce')
            end_t = pd.to_datetime(df[time_col].iloc[-1], errors='coerce')
            duration_td = (end_t - start_t).total_seconds() if pd.notnull(start_t) and pd.notnull(end_t) else float(len(df))
        else:
            duration_td = float(len(df))

        # Detecció de tipus d'anomalia
        v_diff = df[speed_col].diff().fillna(0)
        has_brusque_braking = any(v_diff < -7)
        has_overspeed = any(df[speed_col] > 90)
        
        # Rollback check
        km_diff = df[km_col].diff().fillna(0)
        has_rollback = any((km_diff < -0.001) & (df[speed_col] > 1))
        
        alert_msg = []
        if has_overspeed: alert_msg.append("Excés Velocitat")
        if has_brusque_braking: alert_msg.append("Frenada Brusca")
        if has_rollback: alert_msg.append("Roll-back")

        kpis = {
            "start_time": df[time_col].iloc[0] if time_col in cols else "N/A",
            "start_km": f"{raw_start_km:.3f}",
            "end_km": f"{raw_end_km:.3f}",
            "distance": f"{abs(raw_end_km - raw_start_km):.3f}",
            "max_speed": f"{df[speed_col].max():.1f}",
            "avg_speed": f"{df[speed_col].mean():.1f}",
            "duration": f"{duration_td:.0f}",
            "anomalies": " | ".join(alert_msg) if alert_msg else "Cap",
            "has_rollback": has_rollback
        }
        return kpis
    except Exception as e:
        return {"Error": str(e)}

def generate_mock_fgc_data():
    """Genera dades sintètiques pel desenvolupament de l'aplicació."""
    rows = 500
    start_time = datetime.now()
    times = [ (start_time + timedelta(seconds=i)).strftime("%H:%M:%S") for i in range(rows)]
    
    # Generar un perfil de velocidad realista
    velocity = np.concatenate([
        np.linspace(0, 85, 100),
        [85 + np.random.normal(0, 1)] * 300,
        np.linspace(85, 0, 100)
    ])
    velocity = np.clip(velocity, 0, 95)
    
    km = np.cumsum(velocity / 3600) + 24.500
    
    pressure = np.full(rows, 5.0)
    pressure[400:] = 3.2
    
    # Noves variables per a l'anàlisi ràpid
    fu = np.zeros(rows)
    fu[410:430] = 1 # Simulem un FU puntual al final
    
    bolet = np.zeros(rows)
    # bolet[0] = 0
    
    mode_atp = np.ones(rows)
    mode_ato = np.zeros(rows)
    mode_ato[100:400] = 1 # Actiu a tram central
    
    return pd.DataFrame({
        'Hora': times,
        'VELOCIDAD': velocity,
        'KM': km,
        'PRESION_TDP': pressure,
        'Fre d\'Urgència': fu,
        'Bolet': bolet,
        'Mode ATP': mode_atp,
        'Mode ATO': mode_ato,
        'MATRICULA_UT': ['UT 114.22'] * rows
    })
