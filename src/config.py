"""
Configuració centralitzada del projecte FGC OTMR Analyst.

Conté:
- ``VERSION``: versió única de l'aplicació (abans hi havia 3 versions
  diferents entre app.py, report_generator.py i la capçalera del Word).
- ``load_settings``: carrega els llindars operatius des de ``settings.json``
  amb fallback hardcoded.
- ``PALETTE``: tokens de color del tema Swiss/teal (abans duplicats a app.py).
- ``PATHS``: rutes estàndard als fitxers de configuració JSON i assets.
"""
from __future__ import annotations

import os
from typing import Any

from src.utils import load_json


# Versió única de l'aplicació. Mostrar-la a la UI, als informes i a la
# documentació. Abans hi havia "v4.96" (app.py), "v5.0" (report_generator.py)
# i "PRO v5.0" (peu del Word) — es unifiquen aquí.
VERSION = "5.1"


# Rutes estàndard dels fitxers del projecte (totes relatives a l'arrel).
PATHS = {
    "settings": "src/settings.json",
    "mappings": "src/mappings.json",
    "stations": "src/stations.json",
    "signals": "src/signals.json",
    "template_word": "plantilla informe registros.docx",
    "logo": "assets/logo.png",
}


# Paleta de colors (tema Swiss/teal). Abans estava hardcoded inline a app.py
# com a diccionari ``t``. Centralitzar-la aquí facilita el mode fosc (FASE 4.6).
PALETTE = {
    "primary": "#006666",
    "primary_container": "#8dedec",
    "secondary": "#006760",
    "background": "#e1fbff",
    "surface_low": "#cbf9ff",
    "surface_lowest": "#ffffff",
    "on_surface": "#003439",
    "on_surface_variant": "#29646a",
    "outline": "#7eb6be",
    "shadow": "0px 24px 48px rgba(0, 52, 57, 0.06)",
    "glass_bg": "rgba(225, 251, 255, 0.6)",
}


# Llindars per defecte si settings.json no existeix o està malformat.
DEFAULT_SETTINGS = {
    "OVERSPEED_THRESHOLD": 90.5,
    "BRUSQUE_BRAKING_THRESHOLD": -7.0,
    "STATION_STOP_DIST_M": 25.0,
    "MOVING_SPEED_THRESHOLD": 2.0,
    "MIN_STATION_STOP_TIME_S": 10.0,
}


def load_settings(train_type: str = "DEFAULT", file_path: str = PATHS["settings"]) -> dict[str, Any]:
    """Carrega els llindars operatius des de ``settings.json`` amb fallback."""
    data = load_json(file_path)
    if not isinstance(data, dict) or not data:
        return dict(DEFAULT_SETTINGS)
    
    # Suportem el format de perfils (diccionari de diccionaris)
    if train_type in data and isinstance(data[train_type], dict):
        return data[train_type]
    elif "DEFAULT" in data and isinstance(data["DEFAULT"], dict):
        return data["DEFAULT"]
        
    return data


# Lazy-load inicial per defecte
SETTINGS: dict[str, Any] = load_settings()


def reload_settings(train_type: str = "DEFAULT") -> dict[str, Any]:
    """
    Torna a carregar ``settings.json`` i actualitza ``SETTINGS`` in-place.
    """
    global SETTINGS
    SETTINGS = load_settings(train_type)
    return SETTINGS
