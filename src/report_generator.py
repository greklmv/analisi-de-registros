from docx import Document  # type: ignore
from docx.shared import Inches, Pt  # type: ignore
import matplotlib.pyplot as plt
import io
import os

def create_sparkline(data, color='#00d2ff'):
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

    # --- 1. ACTUALIZAR METADATOS Y LIMPIEZA DE TABLAS ---
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text.upper()
                if "MOTIU:" in text: cell.text = f"MOTIU: {project_info.get('motiu', '')}"
                elif "LLOC:" in text: cell.text = "LLOC: "
                elif "DATA:" in text: cell.text = "DATA: "
                elif "HORA:" in text: cell.text = "HORA: "
                elif "TREN:" in text: cell.text = "TREN: "
                elif "UT:" in text: cell.text = f"UT: {project_info.get('ut', '')}"
                elif "AGENT DE CONDUCCIÓ:" in text: cell.text = "AGENT DE CONDUCCIÓ: "
                elif "ANÀLISI DE REGISTRE" in text:
                    cell.text = f"ANÀLISI DE REGISTRE: {notes if notes else ''}"
                elif "SIGNAT" in text and "NOM" in text:
                    cell.text = "SIGNAT (NOM I COGNOM): "

    # --- 1b. LIMPIEZA DE "ANÀLISI DELS REGISTRES" EN EL CUERPO DEL DOCUMENTO ---
    # Buscamos la sección de análisis y eliminamos los puntos por defecto
    target_found = False
    paragraphs_to_remove = []
    
    # Textos por defecto a eliminar (según imagen del usuario)
    defaults = [
        "Es realitza tota la circulació en mode ATP",
        "El maquinista no actua sobre el bolet",
        "En cap moment entra l'anti bloqueig",
        "El maquinista ultrapassa l'estació"
    ]

    for i, p in enumerate(doc.paragraphs):
        p_text = p.text.strip()
        
        # Si encontramos el encabezado, marcamos para insertar notas
        if "Anàlisi dels registres" in p_text:
            target_found = True
            # Limpiamos el texto del encabezado por si tiene basura, pero mantenemos el párrafo
            # p.text = "Anàlisi dels registres:" 
            continue
            
        if target_found:
            # Si el párrafo contiene alguno de los textos por defecto, lo marcamos para borrar
            is_default = any(d.lower() in p_text.lower() for d in defaults)
            if is_default or (p_text and p_text[0].isdigit() and "." in p_text[:3]):
                paragraphs_to_remove.append(p)
            elif p_text == "" and len(paragraphs_to_remove) < 10: # Seguir limpiando espacios vacíos inmediatos
                paragraphs_to_remove.append(p)
            else:
                # Si encontramos texto que NO es por defecto ni un número de lista, paramos de limpiar
                if p_text != "":
                    break

    # Insertar las notas del usuario si existen
    if target_found:
        # Buscamos el párrafo del título otra vez para insertar justo después
        for p in doc.paragraphs:
            if "Anàlisi dels registres" in p.text:
                new_p = p.insert_paragraph_before("") # Hack para insertar después: creamos uno antes y movemos? 
                # En python-docx es difícil insertar después. Usaremos el último párrafo eliminado como ancla o simplemente añadiremos al final si no hay ancla.
                if notes:
                    p.add_run(f"\n\n{notes}")
                else:
                    p.add_run("\n\n(No s'han afegit observacions)")
                break

    # Eliminamos físicamente los párrafos marcados (puntos por defecto)
    for p in paragraphs_to_remove:
        p.text = "" # No se puede borrar fácilmente, así que vaciamos el texto

    # --- 2. INSERTAR GRÁFICO ---
    if chart_img:
        safe_add_heading(doc, "Visualització Telemètrica", level=1)
        doc.add_picture(io.BytesIO(chart_img), width=Inches(6.0))
        doc.add_paragraph("Llegenda: Canal de velocitat (blau), consigna (vermell - si existeix).")

    # --- 3. ACTUALIZAR DATOS DE BLOQUES (Tabla 1) ---
    if len(doc.tables) > 1:
        data_table = doc.tables[1]
        # Limpiar filas excepto cabecera
        while len(data_table.rows) > 1:
            tbl = data_table._tbl
            tr = data_table.rows[-1]._tr
            tbl.remove(tr)

        if isinstance(kpis, list):
            for entry in kpis:
                row_cells = data_table.add_row().cells
                row_cells[0].text = str(entry.get('start_time', '---'))
                
                # Inserir Ubicació/Estació si la taula té prou espai (més de 6 columnes)
                col_offset = 0
                if len(row_cells) > 6:
                    row_cells[1].text = str(entry.get('location', 'Tram Obert'))
                    col_offset = 1
                
                row_cells[col_offset + 1].text = str(entry.get('ut_indicator', '---'))
                row_cells[col_offset + 2].text = str(entry.get('distance', '0 m'))
                row_cells[col_offset + 3].text = str(entry.get('max_speed', '0'))
                row_cells[col_offset + 4].text = str(entry.get('avg_speed', '0'))
                
                # Inserir Sparkline si hi ha dades
                speed_history = entry.get('speed_history', [])
                if len(row_cells) > (col_offset + 5) and len(speed_history) > 2:
                    spark_buf = create_sparkline(speed_history)
                    paragraph = row_cells[col_offset + 5].paragraphs[0]
                    run = paragraph.add_run()
                    run.add_picture(spark_buf, width=Inches(1.0))

                # Alertes (Anomalies)
                obs_final = entry.get('anomalies', '')
                if entry.get('has_rollback'):
                    obs_final = "⚠️ ROLL-BACK DETECTAT! " + obs_final
                
                target_cell = col_offset + 6
                if target_cell < len(row_cells):
                    row_cells[target_cell].text = obs_final

    # --- 4. FIN DEL DOCUMENTO ---
    doc.add_paragraph("\nInforme generat pel Sistema d'Anàlisi OTMR v4.96")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
