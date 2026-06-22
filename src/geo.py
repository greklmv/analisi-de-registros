"""
Capes geogràfiques del projecte FGC OTMR Analyst.

Conté tot el relacionat amb estacions, senyals i el càlcul de PK (Punt
Quilomètric). Aquestes funcions estan separades d'``analytics`` perquè
no depenen de les dades del registre, només dels fitxers estàtics
(``stations.json``, ``signals.json``) i de la configuració de llindars.

Llegiu ``src/config.py`` per ``SETTINGS`` i ``PATHS``.
"""
from __future__ import annotations

from typing import Any, Optional

from src.utils import load_json
from src.config import SETTINGS, PATHS


# ---------------------------------------------------------------------------
# ESTACIONS
# ---------------------------------------------------------------------------

def load_stations(file_path: str = PATHS["stations"]) -> dict[str, Any]:
    """
    Carrega les estacions des de ``stations.json`` i resol els PK absoluts.

    El fitxer pot definir seccions amb ``origin`` (l'ID d'una estació d'una
    altra secció) per a sub-branques. Aquí es calcula ``pk_abs`` = ``pk`` +
    ``pk_abs`` de l'estació origen. Si el fitxer no existeix o està malformat,
    retorna ``{}``.
    """
    data = load_json(file_path)
    if not data:
        return {}

    try:
        # 1. Mapa ràpid ID -> PK per a lookups d'origen (només seccions sense origin)
        id_to_pk: dict[str, float] = {}
        for section in data.values():
            for st in section.get("stations", []):
                if "origin" not in section:
                    id_to_pk[st["id"]] = st["pk"]

        # 2. Resoldre estacions amb origen (2 passades)
        resolved_data: dict[str, Any] = {}
        for sec_id, section in data.items():
            stations = section.get("stations", []).copy()
            origin_id = section.get("origin")

            offset = 0.0
            if origin_id in id_to_pk:
                offset = id_to_pk[origin_id]

            for st in stations:
                st["pk_abs"] = st["pk"] + offset
                id_to_pk[st["id"]] = st["pk_abs"]

            resolved_data[sec_id] = section
        return resolved_data
    except Exception:
        return {}


def get_closest_station(pk: float, stations_data: dict, line_filter: Any = None) -> str:
    """
    Identifica l'estació més propera per a un PK determinat.

    Retorna un missatge llegible per la UI:
    - ``"Aturat a {name} ({id})"`` si està dins de l'umbral de parada.
    - ``"Rebassat {name} (+{m} m)"`` si ha passat l'estació.
    - ``"Arribant a {name} (-{m} m)"`` si s'hi acosta.
    - ``"Tram Obert"`` si no hi ha dades o cap propera.

    Opcionalment filtra per línia (``line_filter`` = llista/col·lecció
    d'IDs de secció vàlids).
    """
    if not stations_data:
        return "Tram Obert"

    best_station: Optional[dict] = None
    min_dist = float("inf")

    for sec_id, line_info in stations_data.items():
        if line_filter and sec_id not in line_filter:
            continue
        for st in line_info.get("stations", []):
            st_pk = float(st.get("pk_abs", st.get("pk", 0)))
            dist = pk - st_pk  # positiva si hem passat l'estació
            abs_dist = abs(dist)
            if abs_dist < min_dist:
                min_dist = abs_dist
                best_station = {
                    "id": st.get("id", "---"),
                    "name": st.get("name", "---"),
                    "pk": st_pk,
                    "diff": dist,
                }

    if not best_station:
        return "Tram Obert"

    dist_m = best_station["diff"] * 1000
    abs_dist_m = abs(dist_m)

    if abs_dist_m < SETTINGS["STATION_STOP_DIST_M"]:
        return f"Aturat a {best_station['name']} ({best_station['id']})"
    if dist_m > 0:
        return f"Rebassat {best_station['name']} (+{abs_dist_m:.0f} m)"
    return f"Arribant a {best_station['name']} (-{abs_dist_m:.0f} m)"


def get_all_stations_flat() -> list[dict]:
    """Retorna una llista plana de totes les estacions per al selector de la UI."""
    data = load_stations()
    flat_list: list[dict] = []
    for section in data.values():
        for st in section.get("stations", []):
            st["display_name"] = f"{st['name']} ({st['id']}) - PK {st.get('pk_abs', st['pk']):.3f}"
            flat_list.append(st)
    return sorted(flat_list, key=lambda x: x.get("pk_abs", 0))


# ---------------------------------------------------------------------------
# SENYALS
# ---------------------------------------------------------------------------

def load_signals(file_path: str = PATHS["signals"]) -> dict[str, Any]:
    """Carrega les senyals de via des de ``signals.json``."""
    return load_json(file_path, fallback={}) or {}


def get_closest_signal(pk: float, signals_data: dict, line_filter: Any = None,
                       track: Optional[str] = None) -> tuple[Optional[dict], Optional[float]]:
    """
    Troba la senyal més propera per a un PK determinat.

    - ``track``: ``"Via1"`` o ``"Via2"`` per restringir la cerca (si existeix
      com a clau a ``signals_data``).
    - ``line_filter``: col·lecció d'IDs de grup vàlids per filtrar.

    Retorna ``(senyal, distància_en_km)`` o ``(None, None)``.
    """
    if not signals_data:
        return None, None

    best_sig: Optional[dict] = None
    min_dist = float("inf")

    search_space = signals_data.get(track, signals_data) if track in signals_data else signals_data

    def find_in_groups(data: Any) -> None:
        nonlocal best_sig, min_dist
        if isinstance(data, list):
            for sig in data:
                sig_pk = float(sig["pk_abs"])
                dist = abs(pk - sig_pk)
                if dist < min_dist:
                    min_dist = dist
                    best_sig = sig
        elif isinstance(data, dict):
            for group, content in data.items():
                if line_filter and group not in line_filter:
                    continue
                find_in_groups(content)

    find_in_groups(search_space)
    return best_sig, min_dist


def find_nearest_signal_id(pk: float, signals_data: Optional[dict],
                           line_filter: Any = None, is_ascendant: bool = True) -> Optional[str]:
    """
    Retorna l'ID de la senyal més propera al ``pk`` indicat, o ``None``.

    Wrapper de conveniència sobre :func:`get_closest_signal` que selecciona
    automàticament la via (``Via1`` ascendent / ``Via2`` descendent) i extreu
    només l'ID. Elimina els 5 blocs duplicats que feien servir aquesta lògica
    a ``detect_anomalies`` i ``get_event_based_summary``.
    """
    if not signals_data:
        return None
    track = "Via1" if is_ascendant else "Via2"
    sig, _ = get_closest_signal(pk, signals_data, line_filter, track=track)
    return sig["id"] if sig else None


# ---------------------------------------------------------------------------
# PK (PUNT QUILÒMETRIC)
# ---------------------------------------------------------------------------

def calculate_pk_at_index(idx: Any, df: Any, km_col: str,
                         starting_pk: Optional[float], is_ascendant: bool) -> float:
    """
    Calcula la PK exacta d'un índex del DataFrame basant-se en la distància
    acumulada des de l'inici del registre i l'origen de calibratge.

    - Si ``starting_pk`` és ``None``, retorna 0 (sense calibratge).
    - Si ``is_ascendant`` és ``True``, el PK augmenta amb la distància;
      si és ``False``, disminueix.
    """
    if starting_pk is None:
        return 0.0
    init_km = df[km_col].iloc[0]
    curr_km = df[km_col].loc[idx]
    dist_km = (curr_km - init_km)
    return starting_pk + (dist_km if is_ascendant else -dist_km)
