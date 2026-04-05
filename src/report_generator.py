from docx import Document  # type: ignore
from docx.shared import Inches, Pt  # type: ignore
from docx.enum.text import WD_ALIGN_PARAGRAPH # type: ignore

import matplotlib.pyplot as plt
import io
import os
import pandas as pd

def create_sparkline(data, color='#0052A3'):
    """Genera una imagen de mini-gráfico (sparkline) para insertar en el Word."""
    plt.figure(figsize=(1.5, 0.4))
    plt.plot(data, color=color, linewidth=1.5)
    plt.fill_between(range(len(data)), data, color=color, alpha=0.1)
    plt.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close()
    buf.seek(0)
    return buf

def safe_add_heading(doc, text, level):
    """Añade un encabezado de forma segura."""
    try:
        doc.add_heading(text, level=level)
    except Exception:
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(14) if level == 1 else Pt(12)

def safe_add_paragraph(doc, text="", style=None):
    """Añade un párrafo de forma segura, manejando estilos inexistentes."""
    try:
        return doc.add_paragraph(text, style=style)
    except Exception:
        p = doc.add_paragraph()
        if style and ('List Bullet' in style or 'Bullet' in style):
            p.add_run("• ")
        if text:
            p.add_run(text)
        return p


def generate_word_report(df, kpis, project_info, chart_img=None, notes=None, op_events=None, template_path="/Users/grek/IA/Analisis registros/plantilla informe registros.docx"):
    """Genera el informe Word con deteccion de eventos y zoom plots."""
    if not os.path.exists(template_path):
        doc = Document()
        doc.add_heading("INFORME D'ANÀLISI TELEMÈTRICA", 0)
    else:
        doc = Document(template_path)

    # 1. Metadatos
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                t = cell.text.upper()
                if "UT:" in t: cell.text = f"UT: {project_info.get('u', '')}"
                elif "ANÀLISI DE REGISTRE:" in t: cell.text = f"ANÀLISI DE REGISTRE: {notes if notes else ''}"

    # 2. Análisis del cuerpo
    for p in doc.paragraphs:
        if "Anàlisi dels registres" in p.text:
            p.add_run(f"\n\n{notes if notes else '(Sense observacions)'}")
            break

    # 3. Línia de Temps + Zooms
    if op_events:
        safe_add_heading(doc, "Línia de Temps Operativa", level=1)
        for ev in op_events:
            p = safe_add_paragraph(doc, style='List Bullet')

            t_str = ev.get('time', '--:--')
            e_txt = ev.get('event', 'Event')
            run = p.add_run(f"[{t_str}] {e_txt}")
            run.bold = True
            p.add_run(f": {ev.get('details', '')}")
            
            # Zoom si es anomalia o canvi real
            if ev.get('is_anomaly') or "Canvi" in e_txt or "Sortida" in e_txt:
                try:
                    time_col = df.columns[0] # Assumpció de temps
                    # Cercar index aproximat
                    idx = (df[time_col].astype(str).str.contains(t_str)).idxmax()
                    z_df = df.iloc[max(0, idx-20):min(len(df), idx+20)]
                    plt.figure(figsize=(5, 1.8))
                    plt.plot(range(len(z_df)), z_df[df.columns[1]], color='#0052A3')
                    plt.axvline(x=len(z_df)//2, color='red', linestyle='--')
                    plt.title(f"Zoom: {e_txt}", fontsize=9)
                    z_buf = io.BytesIO()
                    plt.savefig(z_buf, format='png', bbox_inches='tight')
                    plt.close()
                    doc.add_picture(z_buf, width=Inches(3.5))
                except: pass

    # 4. Gràfic General
    if chart_img:
        safe_add_heading(doc, "Visualització Telemetria General", level=1)
        doc.add_picture(io.BytesIO(chart_img), width=Inches(5.8))

    # 5. Taula Kpis (Opcional si es vol detallar)
    if kpis and len(doc.tables) > 1:
        tbl = doc.tables[1]
        for row in kpis[:15]: # Limitar a 15 minuts per no fer-lo infinit
            r = tbl.add_row().cells
            num_cells = len(r)
            if num_cells > 0: r[0].text = row.get('start_time','--')
            if num_cells > 3: r[3].text = row.get('distance','0')
            if num_cells > 4: r[4].text = row.get('max_speed','0')
            if num_cells > 6: r[6].text = row.get('anomalies','')

    doc.add_paragraph(f"\nGenerat automàticament OTMR PRO v4.96 - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
