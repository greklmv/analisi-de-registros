import requests
import streamlit as st
from src.config import VERSION
import logging

GITHUB_REPO = "greklmv/analisi-de-registros"

@st.cache_data(ttl=3600)  # Caché de 1 hora para no saturar la API de GitHub ni ralentizar la app
def get_latest_release_info():
    """Consulta la API de GitHub para obtener la última versión lanzada."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        data = response.json()
        latest_version = data.get("tag_name", "").lstrip("v")
        download_url = data.get("html_url", "")
        return latest_version, download_url
    except Exception as e:
        logging.warning(f"No se pudo consultar la API de actualizaciones: {e}")
        return None, None

def parse_version(v_str):
    """Convierte un string de versión '5.1' o '5.1.2' en una tupla de enteros."""
    try:
        return tuple(map(int, v_str.split(".")))
    except ValueError:
        return (0,)

def check_for_updates():
    """Comprueba si hay actualizaciones y muestra un warning en Streamlit si procede."""
    latest_version, download_url = get_latest_release_info()
    
    if latest_version and download_url:
        try:
            if parse_version(latest_version) > parse_version(VERSION):
                st.warning(
                    f"🚀 **¡Nueva versión disponible (v{latest_version})!** "
                    f"Actualmente tienes la versión v{VERSION}. "
                    f"[Haz clic aquí para descargar la actualización]({download_url})",
                    icon="⬇️"
                )
        except Exception as e:
            logging.warning(f"Error parseando versión para actualizar: {e}")
