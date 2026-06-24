# FGC OTMR Analyst

Aplicació web d'anàlisi de registres telemètrics OTMR (On-Train Monitoring Recorder) per a **Ferrocarrils de la Generalitat de Catalunya (FGC)**.

Desenvolupada amb Streamlit, permet carregar registres en format Excel/CSV/PDF, analitzar velocitats, frenades, senyals i esdeveniments operatius, i generar informes executius en format Word amb suport per a diagnòstic mitjançant IA.

**Versió**: 5.1 | **Python**: 3.9+ | **Llicència**: Projecte intern FGC

## Inici ràpid

```bash
# 1. Clonar el repositori
git clone <repo-url> && cd analisi-de-registros

# 2. Crear entorn virtual i instal·lar dependències
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
pip install -r requirements.txt

# 3. Configurar clau API d'IA (opcional)
cp kilo.json.example kilo.json
# Edita kilo.json i afegeix la teva clau OpenRouter

# 4. Executar l'aplicació
streamlit run app.py
```

## Estructura del projecte

```
analisi-de-registros/
├── app.py                  # Aplicació Streamlit (UI principal)
├── requirements.txt        # Dependències de runtime
├── kilo.json.example       # Plantilla de configuració IA
├── assets/                 # Recursos estàtics (logo, etc.)
├── src/
│   ├── config.py           # Versió, paleta de colors, SETTINGS, PATHS
│   ├── geo.py              # Estacions, senyals, càlcul de PK
│   ├── analytics.py        # KPIs, anomalies, events, context IA
│   ├── data_processing.py  # Faceter (re-exporta tot per compatibilitat)
│   ├── utils.py            # Helpers: load_json, normalize_distance, etc.
│   ├── openrouter_client.py# Client IA (OpenRouter / DeepSeek)
│   ├── ai_memory.py        # Memòria d'aprenentatge de l'IA
│   ├── report_generator.py # Generació d'informes Word
│   ├── svg_component.py    # Componente SVG interactiu
│   ├── settings.json       # Llindars operatius (per perfils de tren)
│   ├── mappings.json       # Mapeig de columnes per UT
│   ├── stations.json       # Base de dades d'estacions (PK, branques)
│   ├── signals.json        # Senyals de via per PK
│   └── rules.json          # Motor de regles per detecció d'anomalies
└── tests/
    ├── conftest.py         # Fixtures compartides (mock_df, cols)
    ├── test_config.py      # Tests de configuració
    ├── test_geo.py         # Tests d'estacions, senyals, PK
    ├── test_analytics.py   # Tests de KPIs, events, anomalies
    └── test_utils.py       # Tests d'utilitats
```

## Funcionalitats

- 📊 **Càrrega de registres**: Excel (.xlsx), CSV i PDF amb extracció automàtica de taules
- 🚆 **Mapa interactiu**: Esquema de la xarxa FGC amb posició del tren en temps real
- ⏱️ **Cursor de telemetria**: Navegació per registre operacional sincronitzat
- 🚀 **Detecció d'anomalies**: Sobrevelocitats, frenades brusques (m/s²), FU, bolet/emergència
- 📍 **Calibratge PK**: Sistema de Punt Quilomètric amb estació d'origen i sentit de marxa
- 🛤️ **Senyals de via**: Integració amb senyals de Via 1 (ascendent) i Via 2 (descendent)
- 🤖 **Diagnòstic IA**: Anàlisi automàtic del viatge via OpenRouter (DeepSeek)
- 📋 **Informe Word**: Generació d'informe oficial FGC amb gràfics i cronologia
- 🎯 **Anàlisi ràpid**: Botons d'estacions, senyals i ATP/ATO per a selecció ràpida de variables

## Glosari FGC

| Terme | Significat |
|-------|-----------|
| **OTMR** | On-Train Monitoring Recorder — Registra telemetria del tren |
| **PK** | Punt Quilomètric — Distància al llarg de la via (km) |
| **UT** | Unitat de Tren — Ex: UT 113-114, UT 115 |
| **ATP** | Automatic Train Protection — Mode de conducció amb protecció automàtica |
| **ATO** | Automatic Train Operation — Mode de conducció totalment automàtic |
| **FU** | Fre d'Urgència — Frenada d'emergència activada pel sistema |
| **Bolet / Seta** | Botó d'emergència activat pel maquinista |
| **Via 1** | Via ascendent (PK creixent en direcció PC→Terrassa/Sabadell) |
| **Via 2** | Via descendent (PK decreixent) |
| **Tronc Comú** | Tram compartit Plaça Catalunya — Sarrià |
| **Roll-back** | Moviment invers del tren (retrocés) |
| **Matrícula** | Identificador únic de la unitat de tren (ex: UT 114.22) |

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## Contribuir

1. Crear una branca: `git checkout -b feature/nom-descriptiu`
2. Fer canvis i tests
3. Verificar: `python -m pytest tests/ -v`
4. Commit i push
5. Obrir Pull Request contra `main`
