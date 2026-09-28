"""
Tests para MarketContext (specs/010-btc-change-1h-fix/).

Primera cobertura de este modulo (Principio VI: analysis/ requiere tests) --
enfocada en el fix de btc_change_1h, la funcionalidad que motivo este slice.
"""
from unittest.mock import MagicMock

import pytest

from analysis.market_context import MarketContext


def _candle(close):
    # [timestamp, open, high, low, close, volume]
    return [0, close, close, close, close, 1.0]


def _tickers_with_btc(percentage=0.0, change=0.0):
    return {
        'BTC/USDT': {'percentage': percentage, 'change': change, 'last': 90000.0},
    }


def _make_context(data_manager):
    return MarketContext(data_manager, settings=None)


class TestComputeChange1h:
    def test_normal_computation_uses_real_ohlcv(self):
        dm = MagicMock()
        dm.get_tickers.return_value = _tickers_with_btc(percentage=1.0)
        dm.get_ohlcv.return_value = [_candle(100.0), _candle(105.0)]

        mc = _make_context(dm)
        context = mc.get_context('binance')

        assert context.btc_change_1h == pytest.approx(5.0)
        dm.get_ohlcv.assert_called_with('binance', 'BTC/USDT', '1h')

    def test_insufficient_candles_returns_zero(self):
        dm = MagicMock()
        dm.get_tickers.return_value = _tickers_with_btc()
        dm.get_ohlcv.return_value = [_candle(100.0)]

        mc = _make_context(dm)
        context = mc.get_context('binance')

        assert context.btc_change_1h == 0.0

    def test_empty_candles_returns_zero(self):
        dm = MagicMock()
        dm.get_tickers.return_value = _tickers_with_btc()
        dm.get_ohlcv.return_value = []

        mc = _make_context(dm)
        context = mc.get_context('binance')

        assert context.btc_change_1h == 0.0

    def test_zero_previous_close_does_not_raise(self):
        dm = MagicMock()
        dm.get_tickers.return_value = _tickers_with_btc()
        dm.get_ohlcv.return_value = [_candle(0.0), _candle(100.0)]

        mc = _make_context(dm)
        context = mc.get_context('binance')

        assert context.btc_change_1h == 0.0

    def test_ohlcv_exchange_error_isolated_from_rest_of_context(self):
        """FR-003: un fallo al pedir el 1h no debe tirar abajo todo get_context."""
        dm = MagicMock()
        dm.get_tickers.return_value = _tickers_with_btc(percentage=2.5)
        dm.get_ohlcv.side_effect = RuntimeError('network down')

        mc = _make_context(dm)
        context = mc.get_context('binance')

        assert context.btc_change_1h == 0.0
        # El resto del contexto se calculo normalmente pese al fallo del 1h.
        assert context.btc_change_24h == 2.5
        assert context.btc_trend == 'bullish'  # 2.5% >= DEFAULT_BULLISH_THRESHOLD (2.0%)

    def test_regression_large_24h_absolute_delta_no_longer_leaks_into_1h(self):
        """
        Reproduce el bug original: un ticker con un delta absoluto de 24h grande
        (ej. -630 en precio) ya no debe aparecer como un porcentaje de 1h imposible --
        porque btc_change_1h ahora ni siquiera lee el campo 'change' del ticker.
        """
        dm = MagicMock()
        dm.get_tickers.return_value = _tickers_with_btc(percentage=-0.75, change=-630.06)
        dm.get_ohlcv.return_value = [_candle(84000.0), _candle(83800.0)]

        mc = _make_context(dm)
        context = mc.get_context('binance')

        assert abs(context.btc_change_1h) < 20
        assert context.btc_change_1h != -630.06
