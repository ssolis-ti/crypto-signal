"""
Tests para WyckoffPrimitives (specs/013-wyckoff-effort-result/).
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
