"""
Fixtures compartides pels tests del projecte FGC OTMR Analyst.

Carrega dades de prova (mock FGC) i noms de columna estàndard perquè tots
els tests operin sobre el mateix registre sintètic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Afegeix l'arrel del projecte al PYTHONPATH per permetre `import src.…`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def mock_df() -> pd.DataFrame:
    """DataFrame sintètic FGC (500 files) amb velocitat, PK, FU i ATO/ATP."""
    from src.data_processing import load_data
    return load_data("MOCK_FGC")


@pytest.fixture
def cols(mock_df: pd.DataFrame) -> dict:
    """Retorna els noms de columna estàndard trobats al mock_df."""
    df = mock_df
    return {
        "speed": "VELOCIDAD",
        "km": "KM",
        "time": "Hora",
        "fu": "Fre d'Urgència",
        "ato": "Mode ATO",
        "atp": "Mode ATP",
    }
