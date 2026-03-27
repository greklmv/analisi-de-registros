import pandas as pd  # type: ignore
import pdfplumber  # type: ignore
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
    
    # Normalización inicial de columnas
    df.columns = [str(c).strip() for c in df.columns]
    return df

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
    """Extract tables from PDF using pdfplumber."""
    with pdfplumber.open(uploaded_file) as pdf:
        all_tables = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table: continue
                df_cols = [str(c) if c is not None else f"Column_{i}" for i, c in enumerate(table[0])]
                df = pd.DataFrame(table[1:], columns=df_cols)
                all_tables.append(df)
        
        if not all_tables:
            raise ValueError("No s'han trobat taules al PDF.")
        
        return pd.concat(all_tables, ignore_index=True)

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

def calculate_kpis(df, km_col='KM', speed_col='Velocitat', time_col='Hora'):
    """Calculate KPIs with real time diffs and anomaly detection."""
    try:
        cols = df.columns
        if km_col not in cols or speed_col not in cols:
            return None
        
        # 1. Normalización de KM (si son metros -> KM)
        raw_start_km = float(df[km_col].iloc[0])
        raw_end_km = float(df[km_col].iloc[-1])
        
        # 2. Diferencial de Tiempo Real
        if time_col in cols:
            start_t = pd.to_datetime(df[time_col].iloc[0], errors='coerce')
            end_t = pd.to_datetime(df[time_col].iloc[-1], errors='coerce')
            if pd.notnull(start_t) and pd.notnull(end_t):
                duration_td = (end_t - start_t).total_seconds()
            else:
                duration_td = float(len(df))
        else:
            duration_td = float(len(df))

        # 3. Detección de Anomalías (Deceleración brusca)
        v_diff = df[speed_col].diff().fillna(0)
        anomalies = int(v_diff[v_diff < -5].count())

        kpis = {
            "start_time": df[time_col].iloc[0] if time_col in cols else "N/A",
            "start_km": f"{raw_start_km:.3f}",
            "end_km": f"{raw_end_km:.3f}",
            "distance": f"{(raw_end_km - raw_start_km):.3f}",
            "max_speed": f"{df[speed_col].max():.1f}",
            "avg_speed": f"{df[speed_col].mean():.1f}",
            "duration": f"{duration_td:.0f}",
            "anomalies": anomalies
        }
        
        # Add Catalan keys
        kpis.update({
            "Hora d'inici": kpis["start_time"],
            "KM Inicial": kpis["start_km"],
            "KM Final": kpis["end_km"],
            "Distància Acumulada": kpis["distance"],
            "Velocitat Màxima": kpis["max_speed"],
            "Velocitat Mitjana": kpis["avg_speed"],
            "Anomalies Detectades": kpis["anomalies"]
        })
        
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
    
    return pd.DataFrame({
        'Hora': times,
        'VELOCIDAD': velocity,
        'KM': km,
        'PRESION_TDP': pressure,
        'MATRICULA_UT': ['UT 114.22'] * rows
    })
