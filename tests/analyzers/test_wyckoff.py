"""
Tests para WyckoffPrimitives (specs/013-wyckoff-effort-result/,
specs/014-wyckoff-range-spring-upthrust/).
"""
import numpy as np
import pandas as pd
import pytest

from analyzers.indicators.wyckoff import WyckoffPrimitives


def _ohlcv_df(closes, volumes=None, highs=None, lows=None):
    n = len(closes)
    volumes = volumes if volumes is not None else [100.0] * n
    highs = highs if highs is not None else [c + 1.0 for c in closes]
    lows = lows if lows is not None else [c - 1.0 for c in closes]
    return pd.DataFrame({
        'open': closes, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes,
    })


class TestRelativeVolume:
    def test_matches_simple_moving_average(self):
        volumes = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
        df = _ohlcv_df(closes=[100.0] * len(volumes), volumes=volumes)

        result = WyckoffPrimitives.relative_volume(df, period=3)

        expected_sma = pd.Series(volumes).rolling(3).mean()
        expected = pd.Series(volumes) / expected_sma
        pd.testing.assert_series_equal(
            result.reset_index(drop=True), expected, check_names=False
        )

    def test_nan_during_warmup(self):
        volumes = [10.0, 20.0, 30.0, 40.0]
        df = _ohlcv_df(closes=[100.0] * len(volumes), volumes=volumes)

        result = WyckoffPrimitives.relative_volume(df, period=3)

        assert result.iloc[:2].isna().all()
        assert not pd.isna(result.iloc[2])

    def test_zero_average_volume_is_nan_not_inf(self):
        volumes = [0.0, 0.0, 0.0, 5.0]
        df = _ohlcv_df(closes=[100.0] * len(volumes), volumes=volumes)

        result = WyckoffPrimitives.relative_volume(df, period=3)

        assert pd.isna(result.iloc[2])  # SMA of [0,0,0] = 0 -> guarded to NaN


class TestRelativeRange:
    def test_nan_during_warmup(self):
        closes = [100.0, 101.0, 99.0, 102.0, 98.0, 103.0]
        df = _ohlcv_df(closes=closes)

        result = WyckoffPrimitives.relative_range(df, period=3)

        assert result.iloc[0] != result.iloc[0] or pd.isna(result.iloc[0])  # NaN

    def test_zero_atr_on_flat_series_is_nan_not_inf_or_exception(self):
        closes = [100.0] * 10
        df = _ohlcv_df(closes=closes, highs=[100.0] * 10, lows=[100.0] * 10)

        result = WyckoffPrimitives.relative_range(df, period=3)

        assert not np.isinf(result.fillna(0)).any()
        assert result.iloc[-1] != result.iloc[-1] or pd.isna(result.iloc[-1])


class TestEffortResultRatio:
    def test_high_ratio_for_climax_shaped_candle(self):
        n = 30
        closes = [100.0 + (i % 3) for i in range(n)]  # leve variacion, rango normal
        volumes = [100.0] * n
        # ultima vela: volumen muy alto, rango muy chico (climax-shaped)
        volumes[-1] = 1000.0
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        highs[-1] = closes[-1] + 0.01
        lows[-1] = closes[-1] - 0.01
        df = _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

        ratio = WyckoffPrimitives.effort_result_ratio(df, volume_period=5, range_period=5)

        assert ratio.iloc[-1] > 1.0

    def test_low_ratio_for_thin_move_shaped_candle(self):
        n = 30
        closes = [100.0 + (i % 3) for i in range(n)]
        volumes = [100.0] * n
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        # ultima vela: rango enorme, volumen normal (thin-move-shaped)
        highs[-1] = closes[-1] + 20.0
        lows[-1] = closes[-1] - 20.0
        df = _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

        ratio = WyckoffPrimitives.effort_result_ratio(df, volume_period=5, range_period=5)

        assert ratio.iloc[-1] < 1.0

    def test_no_inf_or_exception_on_degenerate_input(self):
        df = _ohlcv_df(closes=[0.0] * 10, volumes=[0.0] * 10, highs=[0.0] * 10, lows=[0.0] * 10)

        ratio = WyckoffPrimitives.effort_result_ratio(df, volume_period=3, range_period=3)

        assert not np.isinf(ratio.fillna(0)).any()


class TestClimaxAndThinMoveFlags:
    def _climax_fixture(self):
        n = 30
        closes = [100.0 + (i % 3) for i in range(n)]
        volumes = [100.0] * n
        volumes[-1] = 1000.0
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        highs[-1] = closes[-1] + 0.01
        lows[-1] = closes[-1] - 0.01
        return _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

    def _thin_move_fixture(self):
        n = 30
        closes = [100.0 + (i % 3) for i in range(n)]
        volumes = [100.0] * n
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        highs[-1] = closes[-1] + 20.0
        lows[-1] = closes[-1] - 20.0
        return _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

    def test_is_climax_true_for_climax_fixture(self):
        df = self._climax_fixture()
        flags = WyckoffPrimitives.is_climax(df, volume_period=5, range_period=5)
        assert bool(flags.iloc[-1]) is True

    def test_is_climax_false_for_thin_move_fixture(self):
        df = self._thin_move_fixture()
        flags = WyckoffPrimitives.is_climax(df, volume_period=5, range_period=5)
        assert bool(flags.iloc[-1]) is False

    def test_is_thin_move_true_for_thin_move_fixture(self):
        df = self._thin_move_fixture()
        flags = WyckoffPrimitives.is_thin_move(df, volume_period=5, range_period=5)
        assert bool(flags.iloc[-1]) is True

    def test_is_thin_move_false_for_climax_fixture(self):
        df = self._climax_fixture()
        flags = WyckoffPrimitives.is_thin_move(df, volume_period=5, range_period=5)
        assert bool(flags.iloc[-1]) is False

    def test_flags_are_false_not_nan_during_warmup(self):
        df = self._climax_fixture()

        climax_flags = WyckoffPrimitives.is_climax(df, volume_period=5, range_period=5)
        thin_flags = WyckoffPrimitives.is_thin_move(df, volume_period=5, range_period=5)

        assert climax_flags.iloc[0] == False  # noqa: E712 (explicit bool, not NaN)
        assert thin_flags.iloc[0] == False  # noqa: E712
        assert climax_flags.dtype == bool
        assert thin_flags.dtype == bool


def _flat_range_df(n_flat=5, low=99.0, high=101.0, close=100.0):
    """`n_flat` velas planas que establecen un rango: soporte=low, resistencia=high."""
    closes = [close] * n_flat
    lows = [low] * n_flat
    highs = [high] * n_flat
    volumes = [100.0] * n_flat
    return closes, lows, highs, volumes


class TestDetectTradingRange:
    def test_support_resistance_match_prior_window(self):
        closes, lows, highs, volumes = _flat_range_df(n_flat=5)
        # una vela extra despues del rango, para leer el rango "vigente" ahi
        closes += [100.0]
        lows += [99.5]
        highs += [100.5]
        volumes += [100.0]
        df = _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

        ranges = WyckoffPrimitives.detect_trading_range(df, lookback=5)

        assert ranges['support'].iloc[5] == pytest.approx(99.0)
        assert ranges['resistance'].iloc[5] == pytest.approx(101.0)
        assert ranges['range_width_pct'].iloc[5] == pytest.approx(2.0)

    def test_insufficient_history_is_nan(self):
        closes, lows, highs, volumes = _flat_range_df(n_flat=3)
        df = _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

        ranges = WyckoffPrimitives.detect_trading_range(df, lookback=5)

        assert ranges['support'].isna().all()

    def test_current_candle_does_not_define_its_own_range(self):
        """Si la vela actual se incluyera en su propio rolling min/max, nunca podria
        'romper' el rango que ella misma define -- por eso detect_trading_range usa
        shift(1) (ver docstring)."""
        closes, lows, highs, volumes = _flat_range_df(n_flat=5)
        closes += [80.0]  # vela con minima muy por debajo del rango previo
        lows += [50.0]
        highs += [80.0]
        volumes += [100.0]
        df = _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

        ranges = WyckoffPrimitives.detect_trading_range(df, lookback=5)

        # El soporte "vigente" en la vela de ruptura sigue siendo 99 (de las 5 previas),
        # no 50 (que incluiria la propia vela de ruptura).
        assert ranges['support'].iloc[5] == pytest.approx(99.0)


class TestDetectSprings:
    def _spring_fixture(self, confirm_close=100.0):
        closes, lows, highs, volumes = _flat_range_df(n_flat=5)
        closes += [97.0, confirm_close]    # [5]=ruptura, [6]=posible confirmacion
        lows += [95.0, 98.0]
        highs += [98.0, 101.0]
        volumes += [100.0, 100.0]
        return _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

    def test_flags_confirmation_candle_when_price_returns_above_support(self):
        df = self._spring_fixture(confirm_close=100.0)  # vuelve por encima de 99

        result = WyckoffPrimitives.detect_springs(df, lookback=5, confirm_window=3)

        assert bool(result['is_spring'].iloc[6]) is True
        assert bool(result['is_spring'].iloc[5]) is False

    def test_no_flag_when_price_does_not_return_within_window(self):
        closes, lows, highs, volumes = _flat_range_df(n_flat=5)
        closes += [97.0, 95.0, 94.0, 93.0]  # nunca vuelve por encima de 99
        lows += [95.0, 94.0, 93.0, 92.0]
        highs += [98.0, 96.0, 95.0, 94.0]
        volumes += [100.0] * 4
        df = _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

        result = WyckoffPrimitives.detect_springs(df, lookback=5, confirm_window=3)

        assert not result['is_spring'].any()

    def test_no_breakdown_no_event(self):
        closes, lows, highs, volumes = _flat_range_df(n_flat=5)
        closes += [100.0, 100.0]  # dentro del rango, sin ruptura
        lows += [99.2, 99.2]
        highs += [100.8, 100.8]
        volumes += [100.0, 100.0]
        df = _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

        result = WyckoffPrimitives.detect_springs(df, lookback=5, confirm_window=3)

        assert not result['is_spring'].any()

    def test_confirmed_event_carries_relative_volume_context(self):
        df = self._spring_fixture(confirm_close=100.0)

        result = WyckoffPrimitives.detect_springs(df, lookback=5, confirm_window=3,
                                                    volume_period=3)

        assert not pd.isna(result['break_relative_volume'].iloc[6])
        assert not pd.isna(result['confirm_relative_volume'].iloc[6])


class TestDetectUpthrusts:
    def _upthrust_fixture(self, confirm_close=100.0):
        closes, lows, highs, volumes = _flat_range_df(n_flat=5)
        closes += [103.0, confirm_close]   # [5]=ruptura al alza, [6]=posible confirmacion
        lows += [102.0, 99.0]
        highs += [105.0, 102.0]
        volumes += [100.0, 100.0]
        return _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

    def test_flags_confirmation_candle_when_price_returns_below_resistance(self):
        df = self._upthrust_fixture(confirm_close=100.0)  # vuelve por debajo de 101

        result = WyckoffPrimitives.detect_upthrusts(df, lookback=5, confirm_window=3)

        assert bool(result['is_upthrust'].iloc[6]) is True
        assert bool(result['is_upthrust'].iloc[5]) is False

    def test_no_flag_when_price_does_not_return_within_window(self):
        closes, lows, highs, volumes = _flat_range_df(n_flat=5)
        closes += [103.0, 105.0, 106.0, 107.0]  # nunca vuelve por debajo de 101
        lows += [102.0, 104.0, 105.0, 106.0]
        highs += [105.0, 106.0, 107.0, 108.0]
        volumes += [100.0] * 4
        df = _ohlcv_df(closes=closes, volumes=volumes, highs=highs, lows=lows)

        result = WyckoffPrimitives.detect_upthrusts(df, lookback=5, confirm_window=3)

        assert not result['is_upthrust'].any()

    def test_independent_from_spring_flags(self):
        """Ambos flags pueden coexistir en el mismo DataFrame sin interferirse."""
        df = self._upthrust_fixture(confirm_close=100.0)

        springs = WyckoffPrimitives.detect_springs(df, lookback=5, confirm_window=3)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=5, confirm_window=3)

        assert not springs['is_spring'].any()
        assert bool(upthrusts['is_upthrust'].iloc[6]) is True


class TestZeroVolumeDoesNotSilencePair:
    """
    Una vela sin volumen (normal en pares ilquidos) no debe convertir en NaN el volumen relativo
    de todas las velas siguientes: TA-Lib propaga un NaN a toda la serie. Los ceros cuentan en el
    promedio, que es la definicion con la que se valido el edge (specs/017).
    """

    def _df(self, volumes):
        n = len(volumes)
        return pd.DataFrame({
            'open': [100.0] * n, 'high': [101.0] * n, 'low': [99.0] * n,
            'close': [100.0] * n, 'volume': volumes,
        })

    def test_relative_volume_recovers_after_a_zero_volume_candle(self):
        volumes = [100.0] * 60
        volumes[10] = 0.0
        volumes[-1] = 1000.0  # pico extremo mucho despues del cero

        rel = WyckoffPrimitives.relative_volume(self._df(volumes))

        assert not pd.isna(rel.iloc[-1])
        assert rel.iloc[-1] >= 2.5

    def test_negative_volume_yields_nan_not_false_extreme_volume(self):
        volumes = [-100.0] * 30
        volumes[-1] = -1500.0

        rel = WyckoffPrimitives.relative_volume(self._df(volumes))

        assert pd.isna(rel.iloc[-1])
