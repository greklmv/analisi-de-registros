"""
Mòdul faceter (facade) del projecte FGC OTMR Analyst.

Històricament contenia tota la lògica del projecte. Ara delega en:
- :mod:`src.config` — configuració, versió, paleta de colors.
- :mod:`src.geo`    — estacions, senyals, PK.
- :mod:`src.analytics` — KPIs, anomalies, esdeveniments, resum IA.

Les funcions es re-exporten aquí per compatibilitat cap enrere amb
``app.py`` i altres mòduls que encara fan ``from src.data_processing import …``.
"""
from __future__ import annotations

import pandas as pd  # type: ignore
import pdfplumber  # type: ignore
import io
import json
import os
import numpy as np  # type: ignore
import streamlit as st  # type: ignore
from datetime import datetime, timedelta

from src.utils import load_json
from src.config import SETTINGS  # noqa: F401  (re-exportat per compat amb app.py)


# ---------------------------------------------------------------------------
# Compat cap enrere: SETTINGS
# ---------------------------------------------------------------------------
def load_settings(train_type: str = "DEFAULT", file_path: str = "src/settings.json"):
    """Carrega els llindars operatius. Delega a :mod:`src.config`."""
    from src.config import load_settings as _load
    return _load(train_type=train_type, file_path=file_path)


# ---------------------------------------------------------------------------
# Utilitats de caché Streamlit
# ---------------------------------------------------------------------------
def maybe_cache_data(**kwargs):
    """Utilitat per evitar avisos de 'ScriptRunContext' quan s'executa fora de Streamlit."""
    try:
        import streamlit as st
        if st.runtime.exists():
            return st.cache_data(**kwargs)
    except (ImportError, AttributeError):
        pass
    return lambda f: f


def load_mappings(file_path="src/mappings.json"):
    """Load variable mappings from an external JSON file."""
    return load_json(file_path, fallback={}) or {}


# ---------------------------------------------------------------------------
# Re-exportacions: geo (estacions, senyals, PK)
# ---------------------------------------------------------------------------
from src.geo import (  # noqa: E402,F401
    load_stations, get_closest_station, get_all_stations_flat,
    load_signals, get_closest_signal, find_nearest_signal_id,
    calculate_pk_at_index,
)


# ---------------------------------------------------------------------------
# Càrrega de dades (Excel, CSV, PDF, mock)
# ---------------------------------------------------------------------------
def clean_telemetry_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Neteja els nombres de columnes de possibles rutes absolutes de fitxers de telemetria (.tel)."""
    new_cols = []
    for col in df.columns:
        col_str = str(col)
        for ext in ['.tel\\', '.tel/', '.csv\\', '.csv/', '.xlsx\\', '.xlsx/']:
            if ext in col_str:
                parts = col_str.split(ext)
                col_str = parts[-1]
                break
        else:
            if '\\' in col_str:
                parts = col_str.split('\\')
                if parts[-1].strip():
                    col_str = parts[-1]
        new_cols.append(col_str)
    df.columns = new_cols
    return df


@maybe_cache_data()
def load_data(uploaded_file, sheet_name=0, train_type="DEFAULT"):
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

    # Netejar columnes de possibles rutes absolutes de telemetria
    df = clean_telemetry_column_names(df)

    # 1. Aplicar Capa de Normalización (Universal Mapper)
    from src.utils import apply_universal_mapping
    df = apply_universal_mapping(df, train_type=train_type)

    # 1.b Adaptar variables Active-Low para UT 115
    if train_type == "UT 115":
        for signal in ["FU_SISTEMA", "BOLET"]:
            if signal in df.columns:
                df[signal] = pd.to_numeric(df[signal], errors='coerce')
                # 0 se convierte en 1 (Activo), 1 se convierte en 0 (Inactivo)
                df[signal] = 1 - df[signal]


    # Normalització inicial de PK si existeix
    km_potential = next((c for c in df.columns if any(k in str(c).upper() for k in ['DISTANCIA', 'KM', 'X_UT', 'DIST_'])), None)
    if km_potential:
        # Coaccionar a numeric; reemplazar textos inválidos con NaN
        df[km_potential] = pd.to_numeric(df[km_potential], errors='coerce')
        # Limpiar filas donde la distancia sea inválida
        df = df.dropna(subset=[km_potential])

    # Buscar columna de velocitat per normalitzar-la també
    speed_col = next((c for c in df.columns if any(k in str(c).upper() for k in ['VEL', 'SPEED', 'V_'])), None)
    if speed_col:
        df[speed_col] = pd.to_numeric(df[speed_col], errors='coerce')
        df = df.dropna(subset=[speed_col])
        
    # Si desprès de netejar queda buit
    if df.empty:
        raise ValueError("L'arxiu no conté dades vàlides o les columnes essencials tenen formats incorrectes.")

    # Normalització inicial de columnes
    df.columns = [str(c).strip() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Mapping de columnes
# ---------------------------------------------------------------------------
def get_suggested_mapping(columns, unit_model="UT 113-114"):
    """Retorna un mapeig suggerit amb normalització avanzada y cerca de subcadenes."""
    mappings = load_mappings()
    base_mapping = dict(mappings.get(unit_model, {}))

    def normalize(s):
        return str(s).strip().upper().replace('‑', '-').replace('_', '').replace(' ', '').replace('(KM/H)', '').replace('(M)', '')

    normalized_base = {normalize(k): v for k, v in base_mapping.items()}

    final_mapping: dict = {}
    for col in columns:
        col_norm = normalize(col)
        for k_norm, v in normalized_base.items():
            if k_norm in col_norm or col_norm in k_norm:
                final_mapping[col] = f"{col}: {v}"
                break
    return final_mapping


# ---------------------------------------------------------------------------
# Extracció de PDF
# ---------------------------------------------------------------------------
@maybe_cache_data()
def extract_from_pdf(uploaded_file):
    """Extract tables or fixed-width text from PDF using pdfplumber."""
    import re
    with pdfplumber.open(uploaded_file) as pdf:
        all_dfs = []
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    if not table: continue
                    df_cols = [str(c).replace('\n', ' ').strip() if c is not None else f"Column_{i}" for i, c in enumerate(table[0])]
                    df_tmp = pd.DataFrame(table[1:], columns=df_cols)
                    all_dfs.append(df_tmp)

            text = page.extract_text()
            if text:
                pattern = r"(\d{2}/\d{2}/\d{2} - \d{2}:\d{2}:\d{2})\s+(\d+)\s+([\d\.]+)"
                matches = re.findall(pattern, text)
                if matches:
                    df_txt = pd.DataFrame(matches, columns=['Fecha - Hora', 'Distancia', 'AAA'])
                    all_dfs.append(df_txt)

        if not all_dfs:
            raise ValueError("No s'han trobat dades vàlides al PDF.")

        final_df = pd.concat(all_dfs, ignore_index=True)

        time_potential = next((c for c in final_df.columns if any(k in str(c).upper() for k in ['HORA', 'FECHA', 'TIME'])), None)
        if time_potential:
            mask = final_df[time_potential].astype(str).str.contains(r'\d{2}/\d{2}/\d{2}', na=False)
            final_df = final_df[mask].reset_index(drop=True)

        final_df = final_df.dropna(axis=1, how='all')
        return final_df


# ---------------------------------------------------------------------------
# Re-exportacions: analytics (KPIs, anomalies, events, IA context)
# ---------------------------------------------------------------------------
from src.analytics import (  # noqa: E402,F401
    get_minute_summary, detect_anomalies, get_event_based_summary,
    calculate_kpis, get_ai_context,
)


# ---------------------------------------------------------------------------
# Dades de prova (mock)
# ---------------------------------------------------------------------------
def generate_mock_fgc_data():
    """Genera dades sintètiques pel desenvolupament de l'aplicació."""
    rows = 500
    start_time = datetime.now()
    times = [(start_time + timedelta(seconds=i)).strftime("%H:%M:%S") for i in range(rows)]

    velocity = np.concatenate([
        np.linspace(0, 85, 100),
        [85 + np.random.normal(0, 1)] * 300,
        np.linspace(85, 0, 100)
    ])
    velocity = np.clip(velocity, 0, 95)

    km = np.cumsum(velocity / 3600) + 24.500

    pressure = np.full(rows, 5.0)
    pressure[400:] = 3.2

    fu = np.zeros(rows)
    fu[410:430] = 1

    bolet = np.zeros(rows)

    mode_atp = np.ones(rows)
    mode_ato = np.zeros(rows)
    mode_ato[100:400] = 1

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
