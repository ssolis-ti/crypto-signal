"""
Tests adversariales para Area 5:
- analyzers/utils.py (convert_to_dataframe) con entradas degeneradas:
  lista vacia, columnas faltantes (5 cols), columnas de mas (>6 cols), filas malformadas.
- analyzers/indicators/wyckoff.py (WyckoffPrimitives) con entradas degeneradas:
  NaN, inf, volumen negativo, columnas faltantes, una sola fila.
- Garantizar que NO explote el ciclo ni produzca eventos falsos (false positives).
"""
import numpy as np
import pandas as pd
import pytest

from analyzers.utils import IndicatorUtils
from analyzers.indicators.wyckoff import WyckoffPrimitives


class TestIndicatorUtilsAdversarial:
    """Pruebas adversariales sobre convert_to_dataframe."""

    def test_empty_list_returns_empty_dataframe_with_columns(self):
        utils = IndicatorUtils()
        # Lista vacia no debe explotar con ValueError: Length mismatch
        df = utils.convert_to_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert set(df.columns) == {'open', 'high', 'low', 'close', 'volume'}

    def test_less_than_six_columns_handling(self):
        utils = IndicatorUtils()
        # Fila con solo 5 elementos (falta volumen)
        data = [[1700000000000, 100.0, 105.0, 95.0, 102.0]]
        # No debe explotar con unhandled ValueError si se sanitiza o descarta
        try:
            df = utils.convert_to_dataframe(data)
            # Si completa o descarta
            assert isinstance(df, pd.DataFrame)
        except ValueError:
            pass  # Es aceptable si levanta un ValueError controlado

    def test_more_than_six_columns_truncated_gracefully(self):
        utils = IndicatorUtils()
        # Fila con 7 elementos (exchange devuelve extra data)
        data = [[1700000000000, 100.0, 105.0, 95.0, 102.0, 1000.0, 999.0]]
        df = utils.convert_to_dataframe(data)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert df['volume'].iloc[0] == 1000.0

    def test_numeric_coercion_from_strings(self):
        utils = IndicatorUtils()
        data = [["1700000000000", "100.0", "105.0", "95.0", "102.0", "500.0"]]
        df = utils.convert_to_dataframe(data)
        assert np.issubdtype(df['close'].dtype, np.number)
        assert df['close'].iloc[0] == 102.0


class TestWyckoffPrimitivesAdversarial:
    """Pruebas sobre WyckoffPrimitives con datos degenerados."""

    @pytest.fixture
    def single_row_df(self):
        index = pd.to_datetime([1700000000000], unit='ms', utc=True)
        return pd.DataFrame({
            'open': [100.0],
            'high': [105.0],
            'low': [95.0],
            'close': [102.0],
            'volume': [500.0],
        }, index=index)

    def test_single_row_does_not_crash_nor_fire_events(self, single_row_df):
        # Una sola fila: todas las primitivas deben retornar NaN / False sin excepcion
        rel_vol = WyckoffPrimitives.relative_volume(single_row_df)
        assert len(rel_vol) == 1
        assert pd.isna(rel_vol.iloc[0])

        rel_range = WyckoffPrimitives.relative_range(single_row_df)
        assert pd.isna(rel_range.iloc[0])

        climax = WyckoffPrimitives.is_climax(single_row_df)
        assert not climax.iloc[0]

        thin = WyckoffPrimitives.is_thin_move(single_row_df)
        assert not thin.iloc[0]

        springs = WyckoffPrimitives.detect_springs(single_row_df)
        assert not springs['is_spring'].iloc[0]

        upthrusts = WyckoffPrimitives.detect_upthrusts(single_row_df)
        assert not upthrusts['is_upthrust'].iloc[0]

    def test_negative_volume_does_not_produce_false_positive_breakouts(self):
        """Volumen negativo (dato corrupto) nunca debe generar relative_volume >= 2.5 ni activar spring."""
        # 30 velas con volumen negativo o cero
        n = 35
        dates = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
        df = pd.DataFrame({
            'open': [100.0] * n,
            'high': [105.0] * n,
            'low': [95.0] * n,
            'close': [100.0] * n,
            'volume': [-500.0] * n,  # Volumen negativo corrupto
        }, index=dates)

        # Hacer que la vela 25 rompa soporte y la 26 vuelva a entrar
        df.loc[dates[25], 'low'] = 90.0
        df.loc[dates[26], 'close'] = 101.0

        rel_vol = WyckoffPrimitives.relative_volume(df)
        # Relative volume con volumen negativo NO debe ser considerado volumen positivo extremo
        springs = WyckoffPrimitives.detect_springs(df)

        # Si se detecta un spring en vela 26, su break_relative_volume no debe ser >= 2.5 valido
        break_rv = springs['break_relative_volume'].iloc[26]
        assert pd.isna(break_rv) or break_rv <= 0 or not springs['is_spring'].iloc[26]

    def test_inf_and_nan_in_ohlcv_does_not_fire_false_events(self):
        """Precios infinitos (+inf, -inf) o NaNs no deben crear falsos resortes (springs)."""
        n = 35
        dates = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
        df = pd.DataFrame({
            'open': [100.0] * n,
            'high': [105.0] * n,
            'low': [95.0] * n,
            'close': [100.0] * n,
            'volume': [100.0] * n,
        }, index=dates)

        # Inyectar inf y nan
        df.loc[dates[20], 'low'] = -np.inf
        df.loc[dates[21], 'close'] = np.inf
        df.loc[dates[22], 'high'] = np.nan

        springs = WyckoffPrimitives.detect_springs(df)
        # No debe haber springs generados por -inf/+inf
        assert not springs['is_spring'].any()

    def test_missing_required_column_raises_clear_error_or_handles_safely(self):
        dates = pd.date_range("2026-01-01", periods=10, freq="4h", tz="UTC")
        df_no_volume = pd.DataFrame({
            'open': [100.0] * 10,
            'high': [105.0] * 10,
            'low': [95.0] * 10,
            'close': [100.0] * 10,
        }, index=dates)

        with pytest.raises((KeyError, ValueError)):
            WyckoffPrimitives.relative_volume(df_no_volume)
