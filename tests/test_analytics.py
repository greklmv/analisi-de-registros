"""Tests de src/analytics.py: KPIs, minute summary, events, anomalies, AI context."""
from __future__ import annotations

import pytest


class TestCalculateKpis:
    def test_retorna_dict_con_camps_requerits(self, mock_df, cols):
        from src.analytics import calculate_kpis
        kpis = calculate_kpis(mock_df, cols["km"], cols["speed"], cols["time"])
        assert kpis is not None
        for key in ("distance", "max_speed", "avg_speed", "duration", "anomalies"):
            assert key in kpis

    def test_no_mutar_df_caller(self, mock_df, cols):
        from src.analytics import calculate_kpis
        original_sum = mock_df[cols["speed"]].sum()
        calculate_kpis(mock_df, cols["km"], cols["speed"], cols["time"])
        after_sum = mock_df[cols["speed"]].sum()
        assert after_sum == original_sum, "calculate_kpis ha de fer .copy()"

    def test_kpi_idempotente(self, mock_df, cols):
        from src.analytics import calculate_kpis
        k1 = calculate_kpis(mock_df, cols["km"], cols["speed"], cols["time"])
        k2 = calculate_kpis(mock_df, cols["km"], cols["speed"], cols["time"])
        assert k1["distance"] == k2["distance"]

    def test_columnas_invalidas_retorna_none(self, mock_df):
        from src.analytics import calculate_kpis
        assert calculate_kpis(mock_df, "NOEXISTE_KM", "NOEXISTE_VEL") is None

    def test_max_speed_es_float(self, mock_df, cols):
        from src.analytics import calculate_kpis
        kpis = calculate_kpis(mock_df, cols["km"], cols["speed"], cols["time"])
        # max_speed és un string com "85.0"
        assert isinstance(kpis["max_speed"], str)
        assert float(kpis["max_speed"]) > 0


class TestGetMinuteSummary:
    def test_retorna_lista_no_vacia(self, mock_df, cols):
        from src.analytics import get_minute_summary
        log = get_minute_summary(mock_df, cols["time"], cols["speed"], cols["km"])
        assert isinstance(log, list)
        assert len(log) > 0

    def test_cada_entrada_tiene_camps_requerits(self, mock_df, cols):
        from src.analytics import get_minute_summary
        log = get_minute_summary(mock_df, cols["time"], cols["speed"], cols["km"])
        for row in log:
            for key in ("start_time", "location", "max_speed", "avg_speed", "max_decel_m_s2"):
                assert key in row, f"Falta camp {key}"

    def test_decel_en_ms2_es_negativo_en_algun_caso(self, mock_df, cols):
        from src.analytics import get_minute_summary
        log = get_minute_summary(mock_df, cols["time"], cols["speed"], cols["km"])
        # El tren frena al final, així que hi ha d'haver deceleració
        has_decel = any(row["max_decel_m_s2"] < -0.1 for row in log)
        assert has_decel, "Hauria d'haver deceleració en algun minut"

    def test_df_vacio_retorna_lista_vacia(self):
        from src.analytics import get_minute_summary
        import pandas as pd
        empty = pd.DataFrame()
        assert get_minute_summary(empty, "T", "V", "KM") == []


class TestGetEventBasedSummary:
    def test_retorna_lista(self, mock_df, cols):
        from src.analytics import get_event_based_summary
        events = get_event_based_summary(mock_df, cols["km"], cols["speed"], cols["time"], starting_pk=24.5)
        assert isinstance(events, list)
        assert len(events) > 0

    def test_cada_event_tiene_time_y_event(self, mock_df, cols):
        from src.analytics import get_event_based_summary
        events = get_event_based_summary(mock_df, cols["km"], cols["speed"], cols["time"], starting_pk=24.5)
        for e in events:
            assert "time" in e, "Falta 'time'"
            assert "event" in e, "Falta 'event'"

    def test_detecta_fu(self, mock_df, cols):
        from src.analytics import get_event_based_summary
        events = get_event_based_summary(mock_df, cols["km"], cols["speed"], cols["time"], starting_pk=24.5)
        fu_events = [e for e in events if "URGÈNCIA" in e.get("event", "")]
        # El mock té FU activat a les files 410-430
        assert len(fu_events) > 0, "Hauria de detectar el FU del mock"


class TestGetAiContext:
    def test_retorna_string_no_buit(self, mock_df, cols):
        from src.analytics import get_ai_context, calculate_kpis, get_event_based_summary
        kpis = calculate_kpis(mock_df, cols["km"], cols["speed"], cols["time"])
        events = get_event_based_summary(mock_df, cols["km"], cols["speed"], cols["time"], starting_pk=24.5)
        ctx = get_ai_context(mock_df, kpis, events)
        assert isinstance(ctx, str)
        assert len(ctx) > 50

    def test_contiene_seccion_kpis(self, mock_df, cols):
        from src.analytics import get_ai_context, calculate_kpis, get_event_based_summary
        kpis = calculate_kpis(mock_df, cols["km"], cols["speed"], cols["time"])
        events = get_event_based_summary(mock_df, cols["km"], cols["speed"], cols["time"], starting_pk=24.5)
        ctx = get_ai_context(mock_df, kpis, events)
        assert "RESUM EXECUTIU" in ctx

    def test_df_vacio_retorna_mensaje(self):
        from src.analytics import get_ai_context
        import pandas as pd
        empty = pd.DataFrame()
        ctx = get_ai_context(empty, {}, [])
        assert "No hi ha dades" in ctx
