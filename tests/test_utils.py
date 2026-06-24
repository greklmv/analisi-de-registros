"""Tests de src/utils.py: load_json, normalize_distance, segment_by_blocks, get_sheet_names."""
from __future__ import annotations

import pandas as pd
import pytest


class TestLoadJson:
    def test_fitxer_existent(self):
        from src.utils import load_json
        data = load_json("src/settings.json")
        assert isinstance(data, dict)
        # settings.json pot tenir estructura plana o per perfils
        any_has = any("OVERSPEED_THRESHOLD" in v if isinstance(v, dict) else False
                      for v in data.values())
        assert any_has or "OVERSPEED_THRESHOLD" in data

    def test_fitxer_inexistent_retorna_fallback(self):
        from src.utils import load_json
        data = load_json("src/NO_EXISTEIX.json", fallback={"key": "val"})
        assert data == {"key": "val"}

    def test_fitxer_malformat_retorna_fallback(self):
        from src.utils import load_json
        # Crear un fitxer JSON temporal malformat
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            os.write(fd, b"{malformed json content")
            os.close(fd)
            data = load_json(path, fallback="default")
            assert data == "default"
        finally:
            os.unlink(path)

    def test_path_absolut(self):
        from src.utils import load_json
        import os
        abs_path = os.path.abspath("src/settings.json")
        data = load_json(abs_path)
        assert isinstance(data, dict)


class TestNormalizeDistance:
    def test_km_a_metres(self):
        from src.utils import normalize_distance
        df = pd.DataFrame({"KM": [24.5, 25.0, 25.5]})
        result = normalize_distance(df.copy(), "KM")
        assert "KM_M" in result.columns
        # Valors < 2000 → s'assumeixen KM, es multipliquen per 1000
        assert result["KM_M"].iloc[0] == pytest.approx(24500, abs=1)

    def test_metres_no_es_multipliquen(self):
        from src.utils import normalize_distance
        # Valors alts → s'assumeixen metres, no es multipliquen
        df = pd.DataFrame({"KM": [24500.0, 25000.0]})
        result = normalize_distance(df.copy(), "KM")
        assert result["KM_M"].iloc[0] == pytest.approx(24500.0, abs=1)

    def test_columna_inexistent_no_afegeix(self):
        from src.utils import normalize_distance
        df = pd.DataFrame({"X": [1, 2]})
        result = normalize_distance(df.copy(), "NOEXIST")
        assert "NOEXIST_M" not in result.columns


class TestSegmentByBlocks:
    def test_df_amb_parada(self):
        from src.utils import segment_by_blocks
        vel = [80] * 20 + [0] * 15 + [80] * 20
        df = pd.DataFrame({"Velocitat": vel})
        blocks = segment_by_blocks(df.copy(), "Velocitat")
        assert len(blocks) >= 2, "Hauria de segmentar en almenys 2 blocs"

    def test_df_sense_parada_retorna_un_bloc(self):
        from src.utils import segment_by_blocks
        df = pd.DataFrame({"Velocitat": [80] * 100})
        blocks = segment_by_blocks(df.copy(), "Velocitat")
        assert len(blocks) == 1

    def test_columna_inexistent_retorna_un_bloc(self):
        from src.utils import segment_by_blocks
        df = pd.DataFrame({"X": [1, 2, 3]})
        blocks = segment_by_blocks(df.copy(), "NOEXIST")
        assert len(blocks) == 1


class TestGetSheetNames:
    def test_fitxer_no_excel_retorna_vacio(self):
        from src.utils import get_sheet_names
        # Objecte qualsevol que no és fitxer Excel
        assert get_sheet_names("no_es_fitxer.txt") == []

    def test_fitxer_excel_real(self):
        from src.utils import get_sheet_names
        import os
        # Busquem un Excel real al projecte si n'hi ha
        excel_files = []
        for root, _, files in os.walk("."):
            for f in files:
                if f.endswith(".xlsx") and "node_modules" not in root and ".venv" not in root:
                    excel_files.append(os.path.join(root, f))
        if excel_files:
            with open(excel_files[0], "rb") as fh:
                names = get_sheet_names(fh)
                assert isinstance(names, list)
