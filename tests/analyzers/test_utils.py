"""
Tests para la consistencia UTC del indice del DataFrame de indicadores
(specs/002-utc-internal-time/).
"""
import pandas

from analyzers.utils import IndicatorUtils


def _row(ts_ms, price=100.0):
    return [ts_ms, price, price, price, price, 1.0]


class TestConvertToDataframe:
    def test_index_is_utc_aware(self):
        df = IndicatorUtils().convert_to_dataframe([_row(1735689600000)])
        assert df.index.tz is not None
        assert str(df.index.tz) == "UTC"

    def test_known_epoch_maps_to_expected_utc_value(self):
        # 1735689600000 ms == 2025-01-01T00:00:00Z
        df = IndicatorUtils().convert_to_dataframe([_row(1735689600000)])
        expected = pandas.Timestamp("2025-01-01T00:00:00Z")
        assert df.index[0] == expected

    def test_result_independent_of_process_local_timezone(self, monkeypatch):
        # Simula que datetime.fromtimestamp (si se siguiera usando) dependeria del TZ
        # del host, forzando una zona no-UTC en el entorno del proceso; el resultado
        # NO debe cambiar porque ya no pasamos por datetime.fromtimestamp/strftime.
        monkeypatch.setenv("TZ", "America/Santiago")
        df = IndicatorUtils().convert_to_dataframe([_row(1735689600000)])
        assert df.index[0] == pandas.Timestamp("2025-01-01T00:00:00Z")

    def test_columns_and_row_count_unchanged(self):
        rows = [_row(1735689600000), _row(1735693200000, price=101.0)]
        df = IndicatorUtils().convert_to_dataframe(rows)
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert len(df) == 2
