import streamlit as st
from src.config import PALETTE
from src.data_processing import load_stations

def render_network_schematic(origin_id=None, pos_id=None, signals_data=None):
    network = load_stations()
    if not network: return ""
    t = PALETTE
    
    # Mantenim SPACING alt per omplir el quadre, però millorem marges de noms
    X_START, Y_MAIN, SPACING, NODE_CH = 40, 150, 62, 22
    LABEL_OFFSET = 32 # Distància del nom al node
    
    trunk = network.get("Tronc-Comu-PC-SC", {}).get("stations", [])
    x_sc = X_START + (len(trunk)-1)*SPACING
    
    s1 = network.get("Ramal-S1-Terrassa", {}).get("stations", [])
    x_last_s1 = x_sc + 60 + (len(s1)-1) * SPACING if s1 else x_sc
    
    s2 = network.get("Ramal-S2-Sabadell", {}).get("stations", [])
    x_last_s2 = x_sc + 60 + (len(s2)-1) * SPACING if s2 else x_sc
    
    W_SVG = max(x_last_s1, x_last_s2) + 60
    H_SVG = 380 # Augmentem H per donar aire als noms de dalt i baix
    
    svg = f'<svg width="100%" height="{H_SVG}" viewBox="0 0 {W_SVG} {H_SVG}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" style="background:transparent; border-radius:32px;">'
    svg += f"""<style>
        .schematic-line {{ stroke:#97eaf4; stroke-width:3; fill:none; stroke-linecap:round; opacity: 0.8; }}
        .schematic-node {{ fill:#ffffff; stroke:#7eb6be; stroke-width:1.5; cursor:pointer; transition:all 0.3s ease-out; transform-box: fill-box; transform-origin: center; }}
        .schematic-node:hover {{ stroke:{t['primary']}; stroke-width:3; fill:#f0feff; transform: scale(1.3); }}
        .schematic-node-pos {{ fill:{t['primary']}; stroke:{t['secondary']}; stroke-width:2; border-radius: 50%; filter:drop-shadow(0 4px 10px rgba(0,102,102,0.3)); }}
        .schematic-node-origin {{ fill:#FF8A65; stroke:#9b3e20; stroke-width:2; }}
        .schematic-label {{ font-family:'Manrope',sans-serif; font-size:11px; font-weight:600; fill:{t['on_surface']}; pointer-events:none; }}
        .schematic-signal {{ stroke:#008080; stroke-width:2.5; fill:none; stroke-linecap:round; }}
    </style>"""
    
    VIA_OFF = 5 
    NODE_H = 26
    x_coords = {}
    
    # Tronc Comú (Doble Via)
    svg += f'<line x1="{X_START}" y1="{Y_MAIN-VIA_OFF}" x2="{x_sc}" y2="{Y_MAIN-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
    svg += f'<line x1="{X_START}" y1="{Y_MAIN+VIA_OFF}" x2="{x_sc}" y2="{Y_MAIN+VIA_OFF}" class="schematic-line" />'
    
    for i, s in enumerate(trunk):
        x = X_START + i * SPACING
        x_coords[s['id']] = x
        cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
        svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{Y_MAIN-13}" width="12" height="{NODE_H}" rx="8" class="{cls}"/><text x="{x}" y="{Y_MAIN+LABEL_OFFSET+6}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'

    x_gr = x_coords.get("GR", X_START + 2*SPACING)
    l7_st = network.get("Ramal-L7", {}).get("stations", [])
    if l7_st:
        y_l7 = Y_MAIN + 65
        x_first_l7 = x_gr + SPACING
        x_last_l7 = x_first_l7 + (len(l7_st)-1) * SPACING
        svg += f'<path d="M {x_gr} {Y_MAIN-VIA_OFF} L {x_first_l7} {y_l7-VIA_OFF} L {x_last_l7} {y_l7-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
        svg += f'<path d="M {x_gr} {Y_MAIN+VIA_OFF} L {x_first_l7} {y_l7+VIA_OFF} L {x_last_l7} {y_l7+VIA_OFF}" class="schematic-line" />'
        for i, s in enumerate(l7_st):
            x = x_first_l7 + i * SPACING
            cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
            svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{y_l7-13}" width="12" height="{NODE_H}" rx="8" class="{cls}"/><text x="{x}" y="{y_l7+LABEL_OFFSET+6}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'

    x_sr = x_coords.get("SR", X_START + 7*SPACING)
    l12_st = network.get("Ramal-L12", {}).get("stations", [])
    if l12_st:
        y_l12 = Y_MAIN - 65
        x_first_l12 = x_sr + SPACING
        x_last_l12 = x_first_l12 + (len(l12_st)-1) * SPACING
        svg += f'<path d="M {x_sr} {Y_MAIN-VIA_OFF} L {x_first_l12} {y_l12-VIA_OFF} L {x_last_l12} {y_l12-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
        svg += f'<path d="M {x_sr} {Y_MAIN+VIA_OFF} L {x_first_l12} {y_l12+VIA_OFF} L {x_last_l12} {y_l12+VIA_OFF}" class="schematic-line" />'
        for i, s in enumerate(l12_st):
            x = x_first_l12 + i * SPACING
            cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
            svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{y_l12-13}" width="12" height="{NODE_H}" rx="8" class="{cls}"/><text x="{x}" y="{y_l12-LABEL_OFFSET}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'

    y_s1 = Y_MAIN - 90
    x_first_s1 = x_sc + SPACING
    x_last_s1 = x_first_s1 + (len(s1)-1) * SPACING
    svg += f'<path d="M {x_sc} {Y_MAIN-VIA_OFF} L {x_first_s1} {y_s1-VIA_OFF} L {x_last_s1} {y_s1-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
    svg += f'<path d="M {x_sc} {Y_MAIN+VIA_OFF} L {x_first_s1} {y_s1+VIA_OFF} L {x_last_s1} {y_s1+VIA_OFF}" class="schematic-line" />'
    for i, s in enumerate(s1):
        x = x_first_s1 + i * SPACING
        cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
        svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{y_s1-13}" width="12" height="{NODE_H}" rx="8" class="{cls}"/><text x="{x}" y="{y_s1-LABEL_OFFSET}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'
    
    y_s2 = Y_MAIN + 90
    x_first_s2 = x_sc + SPACING
    x_last_s2 = x_first_s2 + (len(s2)-1) * SPACING
    svg += f'<path d="M {x_sc} {Y_MAIN-VIA_OFF} L {x_first_s2} {y_s2-VIA_OFF} L {x_last_s2} {y_s2-VIA_OFF}" class="schematic-line" style="opacity:0.6;" />'
    svg += f'<path d="M {x_sc} {Y_MAIN+VIA_OFF} L {x_first_s2} {y_s2+VIA_OFF} L {x_last_s2} {y_s2+VIA_OFF}" class="schematic-line" />'
    for i, s in enumerate(s2):
        x = x_first_s2 + i * SPACING
        cls = "schematic-node-pos" if s['id']==pos_id else ("schematic-node-origin" if s['id']==origin_id else "schematic-node")
        svg += f'<a href="/?station_origin={s["id"]}" target="_self"><rect x="{x-6}" y="{y_s2-13}" width="12" height="{NODE_H}" rx="8" class="{cls}"/><text x="{x}" y="{y_s2+LABEL_OFFSET+6}" text-anchor="middle" class="schematic-label">{s["id"]}</text></a>'

    # --- Dibuixar Senyals si n'hi ha ---
    if signals_data:
        for via_name, via_groups in signals_data.items():
            is_v1 = via_name == "Via1"
            y_off = VIA_OFF if is_v1 else -VIA_OFF
            sig_color = "#f59e0b" if is_v1 else "#ef4444"
            via_label = "Via 1" if is_v1 else "Via 2"
            
            # Tronc Comú
            trunk_pks = [s['pk_abs'] for s in trunk]
            for sig in via_groups.get("Tronc-Comu", []):
                spk = float(sig["pk_abs"])
                if trunk_pks[0] <= spk <= trunk_pks[-1]:
                    for i in range(len(trunk)-1):
                        p1, p2 = trunk_pks[i], trunk_pks[i+1]
                        if p1 <= spk <= p2:
                            sx = x_coords[trunk[i]['id']] + (spk-p1)/(p2-p1)*(x_coords[trunk[i+1]['id']]-x_coords[trunk[i]['id']])
                            svg += f'<g><title>Senyal {sig["id"]} [{via_label}] (PK {spk:.3f})</title><line x1="{sx}" y1="{Y_MAIN+y_off-6}" x2="{sx}" y2="{Y_MAIN+y_off+6}" style="stroke:{sig_color}; stroke-width:2; fill:none;" /></g>'
                            break

            # S1 Branch
            s1_pks = [s['pk_abs'] for s in s1]
            if s1:
                for sig in via_groups.get("Ramal-S1", []):
                    spk = float(sig["pk_abs"])
                    if min(s1_pks) <= spk <= max(s1_pks):
                        for i in range(len(s1)-1):
                            p1, p2 = s1_pks[i], s1_pks[i+1]
                            p_min, p_max = min(p1, p2), max(p1, p2)
                            if p_min <= spk <= p_max:
                                sx = x_first_s1 + i*SPACING + (spk-p1)/(p2-p1)*SPACING
                                svg += f'<g><title>Senyal {sig["id"]} [{via_label}] (PK {spk:.3f})</title><line x1="{sx}" y1="{y_s1+y_off-6}" x2="{sx}" y2="{y_s1+y_off+6}" style="stroke:{sig_color}; stroke-width:2; fill:none;" /></g>'
                                break

            # S2 Branch
            s2_pks = [s['pk_abs'] for s in s2]
            if s2:
                for sig in via_groups.get("Ramal-S2", []):
                    spk = float(sig["pk_abs"])
                    if min(s2_pks) <= spk <= max(s2_pks):
                        for i in range(len(s2)-1):
                            p1, p2 = s2_pks[i], s2_pks[i+1]
                            p_min, p_max = min(p1, p2), max(p1, p2)
                            if p_min <= spk <= p_max:
                                sx = x_first_s2 + i*SPACING + (spk-p1)/(p2-p1)*SPACING
                                svg += f'<g><title>Senyal {sig["id"]} [{via_label}] (PK {spk:.3f})</title><line x1="{sx}" y1="{y_s2+y_off-6}" x2="{sx}" y2="{y_s2+y_off+6}" style="stroke:{sig_color}; stroke-width:2; fill:none;" /></g>'
                                break

            # L7 Branch
            l7_pks = [s['pk_abs'] for s in l7_st]
            if l7_st:
                for sig in via_groups.get("Ramal-L7", []):
                    spk = float(sig["pk_abs"])
                    if min(l7_pks) <= spk <= max(l7_pks):
                        for i in range(len(l7_st)-1):
                            p1, p2 = l7_pks[i], l7_pks[i+1]
                            p_min, p_max = min(p1, p2), max(p1, p2)
                            if p_min <= spk <= p_max:
                                sx = x_first_l7 + i*SPACING + (spk-p1)/(p2-p1)*SPACING
                                svg += f'<g><title>Senyal {sig["id"]} [{via_label}] (PK {spk:.3f})</title><line x1="{sx}" y1="{y_l7+y_off-6}" x2="{sx}" y2="{y_l7+y_off+6}" style="stroke:{sig_color}; stroke-width:2; fill:none;" /></g>'
                                break

    svg += f'<g transform="translate(20, 15)">'
    svg += f'<rect x="0" y="0" width="12" height="12" rx="4" fill="#97eaf4" style="opacity:0.8;"/><text x="18" y="10" style="font-family:Manrope; font-size:10px; font-weight:600; fill:{t["on_surface_variant"]};">VIA 2 / DESC</text>'
    svg += f'<rect x="100" y="0" width="12" height="12" rx="4" fill="#006666" style="opacity:0.4;"/><text x="118" y="10" style="font-family:Manrope; font-size:10px; font-weight:600; fill:{t["on_surface"]};">VIA 1 / ASC</text>'
    svg += f'<line x1="200" y1="6" x2="212" y2="6" style="stroke:#008080; stroke-width:3; stroke-linecap:round;"/><text x="218" y="10" style="font-family:Manrope; font-size:10px; font-weight:600; fill:{t["on_surface"]};">SENYAL ACTIVA</text>'
    svg += f'<rect x="310" y="0" width="12" height="12" rx="4" fill="{t["primary"]}"/><text x="328" y="10" style="font-family:Manrope; font-size:10px; font-weight:600; fill:{t["on_surface"]};">POSICIÓ ACTUAL</text>'
    svg += f'</g>'
    svg += '</svg>'
    return svg
