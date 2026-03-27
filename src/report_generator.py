from docx import Document  # type: ignore
from docx.shared import Inches  # type: ignore
import io
import os

def safe_add_heading(doc, text, level):
    """Añade un encabezado de forma segura, evitando errores de estilos inexistentes (Heading 1 vs Título 1)."""
    try:
        doc.add_heading(text, level=level)
    except Exception:
        # Fallback si el estilo no existe en la plantilla
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.bold = True
        run.font.size = Inches(0.2) if level == 1 else Inches(0.15)

def generate_word_report(df, kpis, project_info, chart_img=None, notes=None, template_path="/Users/grek/IA/Analisis registros/plantilla informe registros.docx"):
    """
    Genera el informe Word utilizando una plantilla base avanzada con detección de anomalías y gráficos.
    """
    if not os.path.exists(template_path):
        doc = Document()
        doc.add_heading("INFORME D'ANÀLISI TELEMÈTRICA", 0)
    else:
        doc = Document(template_path)

    # --- 1. ACTUALIZAR METADATOS (Tabla 0) ---
    if len(doc.tables) > 0:
        meta_table = doc.tables[0]
        for row in meta_table.rows:
            for cell in row.cells:
                text = cell.text
                if "MOTIU:" in text: cell.text = f"MOTIU: {project_info.get('motiu', '')}"
                elif "LLOC:" in text: cell.text = "LLOC: "
                elif "DATA:" in text: cell.text = "DATA: "
                elif "HORA:" in text: cell.text = "HORA: "
                elif "TREN:" in text: cell.text = "TREN: "
                elif "UT:" in text: cell.text = "UT: "
                elif "AGENT DE CONDUCCIÓ:" in text: cell.text = "AGENT DE CONDUCCIÓ: "

    # --- 2. INSERTAR GRÁFICO ---
    if chart_img:
        safe_add_heading(doc, "Visualització Telemètrica", level=1)
        doc.add_picture(io.BytesIO(chart_img), width=Inches(6.0))
        doc.add_paragraph("Legenda: Canal de velocitat (blau), consigna (vermell - si existeix).")

    # --- 3. ACTUALIZAR DATOS DE BLOQUES (Tabla 1) ---
    if len(doc.tables) > 1:
        data_table = doc.tables[1]
        # Limpiar filas excepto cabecera
        while len(data_table.rows) > 1:
            tbl = data_table._tbl
            tr = data_table.rows[-1]._tr
            tbl.remove(tr)

        if isinstance(kpis, list):
            for block in kpis:
                row_cells = data_table.add_row().cells
                row_cells[0].text = str(block.get('start_time', '---'))
                row_cells[1].text = str(block.get('start_km', '---'))
                row_cells[2].text = str(block.get('distance', '---'))
                row_cells[3].text = str(block.get('max_speed', '---'))
                row_cells[4].text = str(block.get('avg_speed', '---'))
                
                anom = block.get('anomalies', 0)
                obs_text = "Circulació nominal"
                if int(anom) > 0:
                    obs_text = f"⚠️ ALERTA: {anom} incidències."
                row_cells[5].text = f"{obs_text} (T: {block.get('duration', '---')}s)"

    # --- 4. SECCIÓN DE OBSERVACIONES ---
    if notes:
        safe_add_heading(doc, "Anàlisi i Diagnòstic Tècnic", level=1)
        doc.add_paragraph(notes)

    doc.add_paragraph("\nInforme generat pel Sistema d'Anàlisi OTMR v4.2")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
