"""
Tests para la consistencia UTC de rendering/utils.py::convert_to_dataframe
(specs/006-deferred-cleanup-findings/, cierra el hallazgo 002-F2).

Mismo patron que tests/analyzers/test_utils.py (specs/002-utc-internal-time/), aplicado a la
funcion equivalente usada por ChartRenderer para el eje X de los graficos.
"""
import pandas

from rendering.utils import convert_to_dataframe


def _row(ts_ms, price=100.0):
    return [ts_ms, price, price, price, price, 1.0]


class TestConvertToDataframe:
    def test_index_is_utc_aware(self):
        df = convert_to_dataframe([_row(1735689600000)])
        assert df.index.tz is not None
        assert str(df.index.tz) == "UTC"

    def test_known_epoch_maps_to_expected_utc_value(self):
        # 1735689600000 ms == 2025-01-01T00:00:00Z
        df = convert_to_dataframe([_row(1735689600000)])
        expected = pandas.Timestamp("2025-01-01T00:00:00Z")
        assert df.index[0] == expected

    def test_result_independent_of_process_local_timezone(self, monkeypatch):
        monkeypatch.setenv("TZ", "America/Santiago")
        df = convert_to_dataframe([_row(1735689600000)])
        assert df.index[0] == pandas.Timestamp("2025-01-01T00:00:00Z")

    def test_columns_and_row_count_unchanged(self):
        rows = [_row(1735689600000), _row(1735693200000, price=101.0)]
        df = convert_to_dataframe(rows)
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert len(df) == 2

    # Nota: convert_to_dataframe([]) levanta ValueError (columns length mismatch) igual que su
    # funcion hermana en analyzers/utils.py (ver specs/002-utc-internal-time/checklists/
    # requirements.md, Addendum). Es un bug pre-existente no relacionado con el fix UTC de este
    # slice -- ningun caller real pasa lista vacia (rendering/core.py::create_chart solo se llama
    # con candles_data no vacios, ver notifications/core.py::create_charts). No se agrega un test
    # de "no-raise" aqui para no documentar como contrato un comportamiento que en realidad falla.
