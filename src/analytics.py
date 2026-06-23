"""
Lògica d'anàlisi del projecte FGC OTMR Analyst.

Conté:
- ``get_minute_summary``: agrupació per minut amb PK, estacions i alertes.
- ``detect_anomalies``: detecció de FU, Bolet, sobrevelocitats.
- ``get_event_based_summary``: cronologia d'esdeveniments operatius.
- ``calculate_kpis``: indicadors clau del viatge.
- ``get_ai_context``: preparació del context textual per a l'IA.

Depèn de :mod:`src.config` (SETTINGS) i :mod:`src.geo` (estacions, senyals, PK).
"""
from __future__ import annotations

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
from typing import Any, Optional

from src.config import SETTINGS
from src.geo import (
    load_stations, get_closest_station,
    load_signals, find_nearest_signal_id,
    calculate_pk_at_index,
)


def get_minute_summary(df, time_col='Hora', speed_col='Velocitat', km_col='KM',
                       extra_cols=None, starting_pk=None, line_filter=None,
                       is_ascendant=True):
    """Agrupa les dades en blocs per minut amb seguiment de PK absoluta basat en estació d'origen i sentit de marxa."""
    if df.empty: return []
    if extra_cols is None: extra_cols = []

    # Pre-càlcul del valor inicial d'odòmetre per a increments relatius
    try:
        initial_odometer = float(df[km_col].iloc[0])
    except (IndexError, KeyError, ValueError, TypeError):
        initial_odometer = 0.0

    df_temp = df.copy()
    df_temp[speed_col] = pd.to_numeric(df_temp[speed_col], errors='coerce').fillna(0)
    
    # Filtro Anti-Ruido: Suavizado EMA (Exponential Moving Average) para evitar falsos picos
    df_temp[speed_col] = df_temp[speed_col].ewm(span=3, adjust=False).mean()
    
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

        # Detecció de la ubicació (estació) amb el nou sistema PK i sentit
        if starting_pk is not None:
            dist_km = (total_acc_dist / 1000)
            current_pk = (starting_pk + dist_km) if is_ascendant else (starting_pk - dist_km)
        else:
            current_pk = ut_raw if ut_raw < 150 else ut_raw / 1000

        loc_name = get_closest_station(current_pk, stations_data, line_filter=line_filter)

        # Distància d'aquest minut
        delta_km = abs(block[km_col].max() - block[km_col].min())
        delta_m = delta_km * 1000 if delta_km < 150 else delta_km

        # Alertes telemètriques
        alerts = []
        if max_v > SETTINGS["OVERSPEED_THRESHOLD"]: alerts.append(f"🔴 EXCÉS VELOCITAT ({max_v:.1f} km/h)")

        # Càlcul físic de deceleració: a = Δv(m/s) / Δt(s) -> m/s^2
        v_diff = block[speed_col].diff().fillna(0)
        t_diff_s = block.index.to_series().diff().dt.total_seconds().fillna(1)
        a_m_s2 = (v_diff / 3.6) / t_diff_s  # acceleració en m/s^2
        decel_m_s2 = a_m_s2.mean()

        # El llindar BRUSQUE_BRAKING_THRESHOLD està en m/s^2
        if (a_m_s2 < SETTINGS["BRUSQUE_BRAKING_THRESHOLD"]).any():
            alerts.append(f"⚠️ FRENADA BRUSCA ({a_m_s2.min():.1f} m/s²)")

        # DETECCIÓ DE CANVIS D'ESTAT (0 <-> 1) en variables seleccionades
        extra_data = {}
        for col in extra_cols:
            if col in [speed_col, km_col, str(time_col)]: continue

            col_series = block[col]
            unique_vals = set(col_series.dropna().unique())
            is_digital = unique_vals.issubset({0, 1, 0.0, 1.0, '0', '1', 0.0})
            if not is_digital: continue

            current_state = last_states.get(col)
            if pd.isna(current_state):
                first_valid = col_series.dropna()
                current_state = first_valid.iloc[0] if not first_valid.empty else np.nan

            changes_in_block = []
            for val in col_series:
                if pd.isna(val) or pd.isna(current_state) or val == current_state:
                    if pd.isna(current_state) and not pd.isna(val):
                        current_state = val
                    continue

                emoji = "⬆️" if str(val) == "1" else "⬇️"
                changes_in_block.append(f"CANVI {col}: {current_state} {emoji} {val}")
                current_state = val

            last_states[col] = current_state

            if changes_in_block:
                alerts.extend(changes_in_block)

            try:
                if pd.api.types.is_numeric_dtype(col_series):
                    extra_data[f"var_{col}"] = f"{col_series.mean():.1f}"
                else:
                    extra_data[f"var_{col}"] = str(col_series.mode().iloc[0]) if not col_series.mode().empty else "---"
            except Exception:
                extra_data[f"var_{col}"] = "---"

        # Detecció de ROLL-BACK
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
            "max_decel_m_s2": float(a_m_s2.min()),
            "anomalies": ", ".join(alerts) if alerts else "",
            "speed_history": block[speed_col].tolist(),
            "has_rollback": has_rb,
            "count": len(block)
        }
        row.update(extra_data)
        summary.append(row)
        total_acc_dist = float(total_acc_dist) + float(delta_m)

    return summary


def detect_anomalies(df, speed_col, km_col, time_col, starting_pk=0.0,
                     is_ascendant=True, line_filter=None, signals_data=None):
    """
    Detecta automàticament punts crítics en la telemetria utilitzant rules.json (Motor de Regles).
    - FU, Bolet, sobrevelocitats, etc.
    """
    anomalies = []
    if df.empty: return anomalies

    import os
    from src.utils import load_json
    
    rules = load_json(os.path.join(os.path.dirname(__file__), "rules.json"), fallback={})
    
    # 1. Generem columnes temporals per al motor de regles (ex: ACCELERACION)
    df_eval = df.copy()
    if 'ACCELERACION' not in df_eval.columns:
        v_diff = df_eval[speed_col].diff().fillna(0)
        t_diff_s = df_eval.index.to_series().diff().dt.total_seconds().fillna(1)
        df_eval['ACCELERACION'] = (v_diff / 3.6) / t_diff_s

    # Inyectamos settings locales para que @OVERSPEED_THRESHOLD funcione
    env = dict(SETTINGS)
    
    # 2. Avaluar regles definides a rules.json
    for rule_id, rule_def in rules.items():
        cond = rule_def.get("condition")
        if not cond: continue
        
        cond_safe = cond.replace("VELOCIDAD", f"`{speed_col}`")
        
        try:
            mask = df_eval.eval(cond_safe, local_dict=env)
            matches = df_eval[mask]
        except Exception as e:
            import logging
            logging.warning(f"Error evaluando regla {rule_id}: {e}")
            continue
            
        if not matches.empty:
            diff = matches.index.to_series().diff().dt.total_seconds().fillna(100)
            groups = (diff > 10).cumsum()
            for _, g in matches.groupby(groups):
                t_start = pd.to_datetime(g[time_col].iloc[0]).strftime('%H:%M:%S')
                v_max = g[speed_col].max()
                idx_max = g[speed_col].idxmax()
                pk_val = calculate_pk_at_index(idx_max, df, km_col, starting_pk, is_ascendant)
    
                sig_id = find_nearest_signal_id(pk_val, signals_data, line_filter, is_ascendant)
                sig_info = f" (Prop de Senyal {sig_id})" if sig_id else ""
    
                msg = rule_def.get("message", "Anomalia").replace("@OVERSPEED_THRESHOLD", str(env.get('OVERSPEED_THRESHOLD')))
                msg = msg.replace("@BRUSQUE_BRAKING_THRESHOLD", str(env.get('BRUSQUE_BRAKING_THRESHOLD')))
                
                anomalies.append({
                    "time": t_start,
                    "event": rule_def.get("event_label", rule_id),
                    "details": f"{msg} Velocitat màx: {v_max:.1f} km/h{sig_info}.",
                    "type": rule_id,
                    "pk": pk_val,
                    "severity": rule_def.get("severity", "Mitjana")
                })

    # 3. Mantenim detecció estricta de FU / Bolet antiga per compatibilitat fins que s'afegeixin a rules.json
    fu_cols = [c for c in df.columns if any(k in str(c).upper() for k in ["FU", "FRE D'URGÈNCIA", "URGENCIA", "N-FE"])]
    bolet_cols = [c for c in df.columns if any(k in str(c).upper() for k in ["BOLET", "SETA", "EMERGÈNCIA", "EMERGENCIA"])]
    for col in list(dict.fromkeys(fu_cols + bolet_cols)):
        vals = pd.to_numeric(df[col], errors='coerce').fillna(0)
        activates = df[(vals.shift(1) == 0) & (vals == 1)]
        for idx, row in activates.iterrows():
            t = pd.to_datetime(row[time_col]).strftime('%H:%M:%S')
            pk_val = calculate_pk_at_index(idx, df, km_col, starting_pk, is_ascendant)

            sig_id = find_nearest_signal_id(pk_val, signals_data, line_filter, is_ascendant)
            sig_info = f" (Prop de Senyal {sig_id})" if sig_id else ""

            is_fu = any(k in str(col).upper() for k in ["FU", "URGÈNCIA", "URGENCIA"])
            label = "⚠️ FRE D'URGÈNCIA" if is_fu else "🚨 BOLET / EMERGÈNCIA"
            anomalies.append({
                "time": t,
                "event": label,
                "details": f"Activació de {col} a {row[speed_col]:.1f} km/h{sig_info}.",
                "type": "SEGURETAT",
                "pk": pk_val,
                "severity": "Crítica"
            })

    return sorted(anomalies, key=lambda x: x['time'])


def get_event_based_summary(df, km_col, speed_col, time_col, starting_pk=0.0,
                           line_filter=None, is_ascendant=True):
    """
    Genera un resum d'esdeveniments operatius: Sortides i Estacionaments.
    Ideal per al resum executiu net.
    """
    if df.empty: return []

    # Carreguem dades estacions i senyals
    stations_data = load_stations()
    signals_data = load_signals()

    # 1. Definir estats: 0 = Parat, 1 = Moviment
    df_state = df.copy()
    df_state[speed_col] = pd.to_numeric(df_state[speed_col], errors='coerce').fillna(0)
    df_state[km_col] = pd.to_numeric(df_state[km_col], errors='coerce').fillna(0)

    df_state['is_moving'] = (df_state[speed_col] > SETTINGS["MOVING_SPEED_THRESHOLD"]).astype(int)

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

        st_info_str = get_closest_station(current_pk, stations_data, line_filter=line_filter)
        loc_name = st_info_str if st_info_str else "Tram Obert"

        try:
            t1 = pd.to_datetime(group[time_col].iloc[0])
            t2 = pd.to_datetime(group[time_col].iloc[-1])
            duration_sec = (t2 - t1).total_seconds()
        except (IndexError, KeyError, ValueError, TypeError):
            duration_sec = 0

        if not is_moving:
            if duration_sec > SETTINGS["MIN_STATION_STOP_TIME_S"]:
                sig_id = find_nearest_signal_id(current_pk, signals_data, line_filter, is_ascendant)
                sig_info = f" | {sig_id}" if sig_id else ""
                events.append({
                    "time": start_time,
                    "event": f"🅿️ Estacionat a {loc_name}",
                    "details": f"Aturat durant {int(duration_sec)}s (PK {current_pk:.3f}){sig_info}",
                    "pk": current_pk
                })
        else:
            # Mode de Conducció Predominant
            mode_l = "ATP"
            atp_sub = next((c for c in group.columns if "ATP" in str(c).upper()), None)
            ato_sub = next((c for c in group.columns if "ATO" in str(c).upper()), None)
            if atp_sub and ato_sub:
                if (group[ato_sub] == 1).sum() > (group[atp_sub] == 1).sum(): mode_l = "ATO"

            sig_id = find_nearest_signal_id(current_pk, signals_data, line_filter, is_ascendant)
            sig_info = f" | {sig_id}" if sig_id else ""
            if i > 0:
                events.append({
                    "time": start_time,
                    "event": f"🚀 Sortida ({mode_l}) de {loc_name}",
                    "details": f"Velocitat màx: {group[speed_col].max():.1f} km/h (PK {current_pk:.3f}){sig_info}",
                    "pk": current_pk,
                    "mode": mode_l
                })
            else:
                events.append({
                    "time": start_time,
                    "event": f"🚄 En circulació {mode_l} (inici)",
                    "details": f"Passant per {loc_name}{sig_info} (PK {current_pk:.3f})",
                    "pk": current_pk,
                    "mode": mode_l
                })

    # --- INTEGRACIÓ D'ANOMALIES ---
    anomalies = detect_anomalies(df_state, speed_col, km_col, time_col, starting_pk, is_ascendant, line_filter, signals_data)
    for a in anomalies:
        events.append({
            "time": a["time"],
            "event": a["event"],
            "details": f"{a['details']} (PK {a['pk']:.3f})",
            "pk": a["pk"],
            "is_anomaly": True,
            "severity": a["severity"]
        })

    return sorted(events, key=lambda x: x['time'])


def calculate_kpis(df, km_col='KM', speed_col='Velocitat', time_col='Hora'):
    """Calculate KPIs with real time diffs and anomaly detection."""
    try:
        cols = df.columns
        if km_col not in cols or speed_col not in cols:
            return None

        # Conversió a numèric per seguretat
        df[speed_col] = pd.to_numeric(df[speed_col], errors='coerce').fillna(0)
        
        # Filtro Anti-Ruido: Suavizado EMA
        df[speed_col] = df[speed_col].ewm(span=3, adjust=False).mean()
        
        df[km_col] = pd.to_numeric(df[km_col], errors='coerce').fillna(0)

        raw_start_km = float(df[km_col].iloc[0])
        raw_end_km = float(df[km_col].iloc[-1])

        if time_col in cols:
            start_t = pd.to_datetime(df[time_col].iloc[0], errors='coerce')
            end_t = pd.to_datetime(df[time_col].iloc[-1], errors='coerce')
            duration_td = (end_t - start_t).total_seconds() if pd.notnull(start_t) and pd.notnull(end_t) else float(len(df))
        else:
            duration_td = float(len(df))

        # Detecció d'anomalies (acceleració en m/s^2)
        v_diff = df[speed_col].diff().fillna(0)
        if time_col in cols:
            t_diff_s = pd.to_datetime(df[time_col], errors='coerce') \
                         .diff().dt.total_seconds().fillna(1)
        else:
            t_diff_s = pd.Series([1.0] * len(df), index=df.index)
        a_m_s2 = (v_diff / 3.6) / t_diff_s
        has_brusque_braking = bool((a_m_s2 < SETTINGS["BRUSQUE_BRAKING_THRESHOLD"]).any())
        has_overspeed = bool((df[speed_col] > SETTINGS["OVERSPEED_THRESHOLD"]).any())

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


def get_ai_context(df, kpis, events) -> str:
    """Prepara un resum textual compacte per a l'IA."""
    if df.empty: return "No hi ha dades disponibles."

    summary = []
    summary.append("### RESUM EXECUTIU (KPIs)")
    summary.append(f"- Unitat: {df.get('MATRICULA_UT', ['Desconeguda'])[0]}")
    summary.append(f"- Distància total: {kpis.get('distance', '---')} km")
    summary.append(f"- Velocitat màxima: {kpis.get('max_speed', '---')} km/h")
    summary.append(f"- Durada: {kpis.get('duration', '---')} segons")
    summary.append(f"- Anomalies detectades: {kpis.get('anomalies', 'Cap')}")

    summary.append("\n### CRONOLOGIA D'ESDEVENIMENTS")
    for ev in events:
        if ev.get("is_anomaly") or "Sortida" in ev["event"] or "Estacionat" in ev["event"]:
            summary.append(f"- {ev['time']} | {ev['event']} | {ev['details']}")

    return "\n".join(summary)
