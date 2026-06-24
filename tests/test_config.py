"""Tests de src/config.py: VERSION, PALETTE, SETTINGS, load_settings, reload_settings."""
from __future__ import annotations

from src import config


def test_version_es_string_no_buida():
    assert isinstance(config.VERSION, str)
    assert config.VERSION.strip() != ""


def test_palette_te_totes_les_claus_requerides():
    required = {
        "primary", "primary_container", "secondary", "background",
        "surface_low", "surface_lowest", "on_surface", "on_surface_variant",
        "outline", "shadow", "glass_bg",
    }
    assert required.issubset(config.PALETTE.keys())
    # Els colors hex han començar per '#'
    for key in ("primary", "secondary", "on_surface"):
        assert config.PALETTE[key].startswith("#"), f"{key} hauria de ser hex"


def test_paths_apunta_a_fitxers_relatius():
    for key in ("settings", "mappings", "stations", "signals"):
        assert isinstance(config.PATHS[key], str)
        assert config.PATHS[key].startswith("src/")


def test_settings_carrega_llindars_known():
    s = config.SETTINGS
    # Tots els llindars definits a DEFAULT_SETTINGS hi són presents.
    for k in config.DEFAULT_SETTINGS:
        assert k in s, f"Falta llindar {k} a SETTINGS"
    # Valors coneguts dels defaults
    assert s["OVERSPEED_THRESHOLD"] == 90.5
    assert s["BRUSQUE_BRAKING_THRESHOLD"] == -7.0


def test_load_settings_amb_path_inexistent_fa_fallback():
    s = config.load_settings("src/NO_EXISTEIX.json")
    assert s == config.DEFAULT_SETTINGS


def test_reload_settings_retorna_dict_igual_a_settings():
    s = config.reload_settings()
    assert isinstance(s, dict)
    # Després del reload, SETTINGS ha de ser coherent amb el retornat
    assert config.SETTINGS == s
