"""
Tests para el fix de repintado (specs/001-no-repaint-signals/).

Cubre:
- T004: la funcion pura drop_unclosed_candle en aislamiento.
- T005: DataManager.get_ohlcv usa la funcion antes de cachear (prueba de cableado).
- T006: dos llamadas consecutivas sin avanzar el tiempo dan resultados identicos
  (Acceptance Scenario 2 de la spec).
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from data.manager import DataManager, drop_unclosed_candle


def _candle(start_ms, close=100.0):
    return [start_ms, close, close, close, close, 1.0]


# Referencia fija: 2026-01-01T08:00:00Z (multiplo exacto de 4h y de 1d en epoch)
NOW = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)
FOUR_H_MS = 4 * 3600 * 1000
ONE_D_MS = 86400 * 1000


class TestDropUnclosedCandle:
    """T004: la funcion pura, sin red ni cache."""

    def test_empty_input_is_noop(self):
        assert drop_unclosed_candle([], "4h", NOW) == []

    def test_all_closed_candles_are_unchanged(self):
        # dos velas 4h que cerraron antes de NOW
        ohlcv = [_candle(NOW_MS - 2 * FOUR_H_MS), _candle(NOW_MS - FOUR_H_MS)]
        result = drop_unclosed_candle(ohlcv, "4h", NOW)
        assert result == ohlcv

    def test_trailing_unclosed_candle_is_dropped(self):
        closed = _candle(NOW_MS - FOUR_H_MS)
        # empieza en NOW - 1h: cierra en NOW + 3h, todavia no cerro
        unclosed = _candle(NOW_MS - 3600 * 1000)
        result = drop_unclosed_candle([closed, unclosed], "4h", NOW)
        assert result == [closed]

    def test_single_unclosed_element_returns_empty(self):
        unclosed = _candle(NOW_MS - 3600 * 1000)
        assert drop_unclosed_candle([unclosed], "4h", NOW) == []

    def test_only_trims_the_tail_not_earlier_rows(self):
        # si (por un bug hipotetico) una vela intermedia pareciera "no cerrada",
        # igual solo se recorta la ultima: no se re-filtra toda la serie
        closed_1 = _candle(NOW_MS - 3 * FOUR_H_MS)
        closed_2 = _candle(NOW_MS - 2 * FOUR_H_MS)
        unclosed_tail = _candle(NOW_MS - 3600 * 1000)
        result = drop_unclosed_candle([closed_1, closed_2, unclosed_tail], "4h", NOW)
        assert result == [closed_1, closed_2]

    @pytest.mark.parametrize("timeframe,period_ms", [("4h", FOUR_H_MS), ("1d", ONE_D_MS)])
    @pytest.mark.parametrize("offset_ms,should_keep", [
        (0, True),        # cierra exactamente ahora -> cerrada (<=)
        (-1000, True),    # cerro hace 1s -> cerrada
        (1000, False),    # cierra en 1s -> NO cerrada
    ])
    def test_boundary_exact_close_time(self, timeframe, period_ms, offset_ms, should_keep):
        start_ms = NOW_MS - period_ms + offset_ms
        candle = _candle(start_ms)
        result = drop_unclosed_candle([candle], timeframe, NOW)
        assert (result == [candle]) is should_keep

    def test_defaults_to_real_utc_now_when_not_provided(self):
        # una vela 1d que empezo hace 2 dias esta cerrada sin importar la hora real
        two_days_ago_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - 2 * ONE_D_MS
        candle = _candle(two_days_ago_ms)
        assert drop_unclosed_candle([candle], "1d") == [candle]


class TestDataManagerGetOhlcvWiring:
    """T005: confirma que get_ohlcv aplica el trim antes de cachear (no solo la funcion pura)."""

    def _manager_with_driver(self, ohlcv_response):
        driver = MagicMock()
        driver.get_historical_data.return_value = ohlcv_response
        return DataManager(driver), driver

    def test_get_ohlcv_trims_unclosed_trailing_candle(self, monkeypatch):
        closed = _candle(NOW_MS - FOUR_H_MS)
        unclosed = _candle(NOW_MS - 3600 * 1000)
        manager, driver = self._manager_with_driver([closed, unclosed])

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW

        monkeypatch.setattr("data.manager.datetime", _FrozenDatetime)

        result = manager.get_ohlcv("binance", "BTC/USDT", "4h")

        assert result == [closed]
        driver.get_historical_data.assert_called_once()

    def test_cached_result_is_already_trimmed(self, monkeypatch):
        closed = _candle(NOW_MS - FOUR_H_MS)
        unclosed = _candle(NOW_MS - 3600 * 1000)
        manager, driver = self._manager_with_driver([closed, unclosed])

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW

        monkeypatch.setattr("data.manager.datetime", _FrozenDatetime)

        first = manager.get_ohlcv("binance", "BTC/USDT", "4h")
        second = manager.get_ohlcv("binance", "BTC/USDT", "4h")

        # T006: dos llamadas, un solo fetch real (la segunda vino de cache),
        # y resultados identicos -> no hay repintado entre ciclos consecutivos.
        assert first == second == [closed]
        driver.get_historical_data.assert_called_once()

    def test_short_history_all_unclosed_yields_empty_not_error(self, monkeypatch):
        unclosed = _candle(NOW_MS - 3600 * 1000)
        manager, driver = self._manager_with_driver([unclosed])

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW

        monkeypatch.setattr("data.manager.datetime", _FrozenDatetime)

        result = manager.get_ohlcv("binance", "BTC/USDT", "4h")
        assert result == []


class TestGetTopPairs:
    """specs/006-deferred-cleanup-findings/: cobertura previamente inexistente, ademas de
    confirmar que la limpieza del logging DEBUG (001-F3) no cambio el comportamiento."""

    def _manager_with_tickers(self, tickers):
        driver = MagicMock()
        driver.get_all_tickers.return_value = tickers
        return DataManager(driver)

    def test_filters_by_quote_currency(self):
        manager = self._manager_with_tickers({
            'BTC/USDT': {'quoteVolume': 100},
            'ETH/BTC': {'quoteVolume': 999},
        })

        result = manager.get_top_pairs('binance', quote='USDT')

        assert result == ['BTC/USDT']

    def test_filters_by_min_volume(self):
        manager = self._manager_with_tickers({
            'BTC/USDT': {'quoteVolume': 100},
            'ETH/USDT': {'quoteVolume': 5},
        })

        result = manager.get_top_pairs('binance', quote='USDT', min_volume=50)

        assert result == ['BTC/USDT']

    def test_sorts_descending_by_volume_and_truncates_to_top_n(self):
        manager = self._manager_with_tickers({
            'A/USDT': {'quoteVolume': 10},
            'B/USDT': {'quoteVolume': 300},
            'C/USDT': {'quoteVolume': 200},
        })

        result = manager.get_top_pairs('binance', quote='USDT', top_n=2)

        assert result == ['B/USDT', 'C/USDT']

    def test_missing_or_null_quote_volume_treated_as_zero(self):
        manager = self._manager_with_tickers({
            'A/USDT': {},
            'B/USDT': {'quoteVolume': None},
        })

        result = manager.get_top_pairs('binance', quote='USDT', min_volume=0)

        assert set(result) == {'A/USDT', 'B/USDT'}

    def test_no_matching_tickers_returns_empty_list(self):
        manager = self._manager_with_tickers({'ETH/BTC': {'quoteVolume': 999}})

        assert manager.get_top_pairs('binance', quote='USDT') == []

    def test_linear_usdt_perpetuals_are_kept_and_other_contracts_are_not(self):
        manager = self._manager_with_tickers({
            'BTC/USDT:USDT': {'quoteVolume': 500},
            'ETH/USDT:USDT': {'quoteVolume': 400},
            'BTC/USDT:USDT-261225': {'quoteVolume': 900},
            'ETH/USDC:USDC': {'quoteVolume': 800},
            'BTC/USD:BTC': {'quoteVolume': 700},
            'SOL/USDT': {'quoteVolume': 50},
        })

        result = manager.get_top_pairs('binance', quote='USDT', top_n=10)

        assert result == ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT']
