# Especificacions Tècniques: Analitzador Telemètric de Registres FGC

## 1. Objectiu del Projecte
Desenvolupament d'una eina web basada en Streamlit per a l'anàlisi automatitzada de registres jurídics ferroviaris (telemètria) i la generació d'informes operatius.

## 2. Tecnologies Utilitzades
- **Llenguatge:** Python 3.9+
- **Framework UI:** Streamlit (Interfície interactiva)
- **Processament de Dades:** Pandas (Gestió de DataFrames)
- **Formats Suportats:** Excel (.xlsx, .xls), CSV

## 3. Funcionalitats Principals
- **Gestió de Dades:** Pujada de fitxers segura i selecció dinàmica de fulls de càlcul.
- **Detecció de Variables:** Identificació automàtica de columnes numèriques i categòriques.
- **Anàlisi Selectiva:** Interfície per seleccionar variables específiques per a l'estudi.
- **Visualització:** Vista prèvia de dades amb formatació premium i resums estadístics (mitjanes, freqüències, valors nuls).

## 4. Estructura de l'Aplicació (`app.py`)
L'aplicació segueix una estructura modular:
- Configuració de pàgina i estils personalitzats (CSS).
- Lògica per a la lectura i validació de dades.
- Secció de selecció de variables mitjançant `st.multiselect`.
- Motor d'anàlisi estadística i visualització de taules.

## 5. Pròxims Passos
- Implementació de gràfics dinàmics (Plotly/Matplotlib).
- Exportació automàtica d'informes en format PDF/Word.
- Integració amb el Protocol Avançat d'Anàlisi Telemètrica.
