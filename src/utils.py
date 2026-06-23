"""
Utilitats transversals del projecte FGC OTMR Analyst.

Conté:
- ``_load_json``: helper unificat per carregar fitxers JSON del projecte
  (elimina la duplicació que tenien ``load_settings``, ``load_mappings``,
  ``load_stations`` i ``load_signals``).
- Funcions d'utilitat pública que abans eren codi mort a ``data_processing``
  (``normalize_distance``, ``segment_by_blocks``, ``get_sheet_names``).
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import pandas as pd  # type: ignore


def _project_root() -> str:
    """Directori arrel del projecte (pare de ``src/``)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(file_path: str, fallback: Any = None) -> Any:
    """
    Carrega un JSON relatiu a l'arrel del projecte.

    Si el fitxer no existeix o està malformat, retorna ``fallback``
    (sense llançar excepció), seguint el patró que ja usaven les
    funcions ``load_*`` originals.
    """
    if os.path.isabs(file_path):
        full_path = file_path
    else:
        full_path = os.path.join(_project_root(), file_path)
    if not os.path.exists(full_path):
        return fallback
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return fallback

from src.config import PATHS

def apply_universal_mapping(df: pd.DataFrame, train_type: str = "DEFAULT") -> pd.DataFrame:
    """
    Renombra les columnes del DataFrame basant-se en mappings.json.
    Així tot el sistema intern opera sobre noms estàndard (ex: VELOCIDAD).
    """
    mappings_data = load_json(PATHS["mappings"], fallback={})
    if not mappings_data:
        return df

    # Utilitzem UT 112 com a fallback si el tren no està definit
    mapping_dict = mappings_data.get(train_type, mappings_data.get("UT 112", {}))
    
    # Invertim: { "Nom_Excel": "Nom_Standard" }
    rename_dict = {v: k for k, v in mapping_dict.items()}
    
    return df.rename(columns=rename_dict)

# ---------------------------------------------------------------------------
# Funcions d'utilitat (abans codi mort a data_processing.py).
# Es mantenen aquí per si es volen fer servir des de la UI o els tests.
# ---------------------------------------------------------------------------

def normalize_distance(df: pd.DataFrame, km_col: str) -> pd.DataFrame:
    """
    Detecta si la distància està en KM o metres i la normalitza a metres.

    Afegeix una columna ``{km_col}_M`` amb el valor en metres.
    Heurística: si el màxim és < 2000 i el rang és < 150, s'assumeix KM.
    """
    if km_col not in df.columns:
        return df

    vals = pd.to_numeric(df[km_col], errors='coerce').fillna(0)
    if vals.max() < 2000 and (vals.max() - vals.min()) < 150:
        df[f"{km_col}_M"] = vals * 1000
    else:
        df[f"{km_col}_M"] = vals
    return df


def segment_by_blocks(df: pd.DataFrame, speed_col: str = 'Velocitat') -> list[pd.DataFrame]:
    """
    Divideix el viatge en blocs operacionals basats en parades.

    Tanca un bloc quan el tren porta més de 10 registres amb velocitat 0.
    Retorna una llista de DataFrames no buits.
    """
    if speed_col not in df.columns:
        return [df]

    df = df.copy()
    df[speed_col] = pd.to_numeric(df[speed_col], errors='coerce').fillna(0)

    blocks: list[pd.DataFrame] = []
    current_block: list[pd.Series] = []

    for _, row in df.iterrows():
        current_block.append(row)
        if row[speed_col] == 0 and len(current_block) > 10:
            blocks.append(pd.DataFrame(current_block))
            current_block = []

    if current_block:
        blocks.append(pd.DataFrame(current_block))

    return [b for b in blocks if not b.empty]


def get_sheet_names(uploaded_file: Any) -> list[str]:
    """Obté els noms de les fulles d'un fitxer Excel. Retorna [] si falla."""
    try:
        file_type = str(getattr(uploaded_file, "name", "")).split('.')[-1].lower()
    except Exception:
        return []
    if file_type not in ('xlsx', 'xls'):
        return []
    try:
        xl = pd.ExcelFile(uploaded_file)
        return xl.sheet_names
    except Exception:
        return []
