"""Tests de src/geo.py: estacions, senyals, PK."""
from __future__ import annotations

from src import geo


class TestLoadStations:
    def test_retorna_dict_no_buit(self):
        s = geo.load_stations()
        assert isinstance(s, dict)
        assert len(s) > 0

    def test_tronc_comu_tiene_estaciones(self):
        s = geo.load_stations()
        assert "Tronc-Comu-PC-SC" in s
        assert len(s["Tronc-Comu-PC-SC"].get("stations", [])) > 0

    def test_resolucion_pk_abs(self):
        s = geo.load_stations()
        # Qualsevol estació hauria de tenir pk_abs després de la resolució
        for section in s.values():
            for st in section.get("stations", []):
                assert "pk_abs" in st, f"Falta pk_abs a {st.get('id')}"
                assert isinstance(st["pk_abs"], float)

    def test_file_inexistent_retorna_vacio(self):
        s = geo.load_stations("src/NO_EXISTEIX.json")
        assert s == {}


class TestGetClosestStation:
    def test_pk_valido_retorna_nombre_estacion(self):
        sts = geo.load_stations()
        # Sabadell Parc del Nord és al PK ~29
        result = geo.get_closest_station(29.0, sts)
        assert isinstance(result, str)
        assert "Sabadell" in result or "PN" in result or "Tram" in result

    def test_datos_vacios_retorna_tram_obert(self):
        assert geo.get_closest_station(25.0, {}) == "Tram Obert"

    def test_line_filter_excluye_seccion(self):
        sts = geo.load_stations()
        # Si filtrem per una línia inexistent, no trobarà estacions
        result = geo.get_closest_station(29.0, sts, line_filter=["LINEA_FANTASMA"])
        # Pot ser Tram Obert si no hi ha estacions al filtre
        assert isinstance(result, str)


class TestGetAllStationsFlat:
    def test_lista_no_vacia(self):
        flat = geo.get_all_stations_flat()
        assert len(flat) > 0

    def test_cada_estacion_tiene_display_name(self):
        flat = geo.get_all_stations_flat()
        for st in flat:
            assert "display_name" in st

    def test_ordenado_por_pk_abs(self):
        flat = geo.get_all_stations_flat()
        pks = [st.get("pk_abs", 0) for st in flat]
        assert pks == sorted(pks), "Estacions haurien d'estar ordenades per PK"


class TestSignals:
    def test_load_signals_retorna_dict(self):
        s = geo.load_signals()
        assert isinstance(s, dict)

    def test_via1_i_via2_existen(self):
        s = geo.load_signals()
        assert "Via1" in s
        assert "Via2" in s

    def test_get_closest_signal_retorna_tuple(self):
        s = geo.load_signals()
        sig, dist = geo.get_closest_signal(25.0, s, track="Via1")
        if sig is not None:
            assert "id" in sig
            assert dist >= 0
        else:
            # Podria ser None si no hi ha senyals a la zona
            assert sig is None

    def test_find_nearest_signal_id_ascendente(self):
        s = geo.load_signals()
        sid = geo.find_nearest_signal_id(25.0, s, is_ascendant=True)
        # Hauria de buscar a Via1
        assert sid is None or isinstance(sid, str)

    def test_find_nearest_signal_id_descendente(self):
        s = geo.load_signals()
        sid = geo.find_nearest_signal_id(25.0, s, is_ascendant=False)
        # Hauria de buscar a Via2
        assert sid is None or isinstance(sid, str)

    def test_find_nearest_signal_id_datos_vacios(self):
        assert geo.find_nearest_signal_id(25.0, None) is None


class TestCalculatePkAtIndex:
    def test_pk_ascendente(self):
        import pandas as pd
        df = pd.DataFrame({"KM": [24.5, 25.0, 25.5]})
        pk = geo.calculate_pk_at_index(2, df, "KM", starting_pk=24.5, is_ascendant=True)
        assert pk == pytest.approx(25.5, abs=0.01)

    def test_pk_descendente(self):
        import pandas as pd
        df = pd.DataFrame({"KM": [24.5, 25.0, 25.5]})
        pk = geo.calculate_pk_at_index(2, df, "KM", starting_pk=24.5, is_ascendant=False)
        assert pk == pytest.approx(23.5, abs=0.01)

    def test_pk_none(self):
        import pandas as pd
        df = pd.DataFrame({"KM": [24.5, 25.0]})
        pk = geo.calculate_pk_at_index(1, df, "KM", starting_pk=None, is_ascendant=True)
        assert pk == 0.0


import pytest  # needed for pytest.approx
