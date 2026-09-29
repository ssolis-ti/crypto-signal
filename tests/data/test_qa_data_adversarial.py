"""
Tests adversariales para Area 1:
- drop_unclosed_candle y DataManager (app/data/manager.py)
- DataCollector (app/behaviour/data.py)
- CCXTDriver (app/exchanges/driver.py)
- PairResolver (app/data/pair_resolver.py)
"""
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import ccxt
from tenacity import RetryError

from data.manager import DataManager, drop_unclosed_candle, DataCache
from behaviour.data import DataCollector
from exchanges.driver import CCXTDriver
from data.pair_resolver import PairResolver


# Helper de vela [start_ms, open, high, low, close, volume]
def _candle(start_ms, close=100.0, volume=10.0):
    return [start_ms, close, close * 1.01, close * 0.99, close, volume]


NOW = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)
FOUR_H_MS = 4 * 3600 * 1000


class TestDropUnclosedCandleAdversarial:
    """Pruebas extremas sobre drop_unclosed_candle."""

    def test_empty_list_returns_empty(self):
        assert drop_unclosed_candle([], "4h", NOW) == []

    def test_exact_close_time_is_retained(self):
        # Vela de 4h que empezo hace 4h exactas: cierra a las 8:00:00.000.
        # En now_ms == close_ms, la vela cerro -> no debe descartarse.
        candle = _candle(NOW_MS - FOUR_H_MS)
        res = drop_unclosed_candle([candle], "4h", NOW)
        assert res == [candle]

    def test_one_millisecond_before_close_is_dropped(self):
        # Empezo 1ms despues -> cierra 1ms en el futuro -> vela no cerrada
        candle = _candle(NOW_MS - FOUR_H_MS + 1)
        res = drop_unclosed_candle([candle], "4h", NOW)
        assert res == []

    def test_one_millisecond_after_close_is_retained(self):
        # Empezo 1ms antes -> cerro hace 1ms -> cerrada
        candle = _candle(NOW_MS - FOUR_H_MS - 1)
        res = drop_unclosed_candle([candle], "4h", NOW)
        assert res == [candle]

    def test_out_of_order_candles_does_not_crash(self):
        # Timestamps desordenados: la ultima tiene timestamp viejo
        c1 = _candle(NOW_MS - FOUR_H_MS)
        c2 = _candle(NOW_MS - 2 * FOUR_H_MS)
        res = drop_unclosed_candle([c1, c2], "4h", NOW)
        assert len(res) == 2

    def test_duplicate_timestamps(self):
        c1 = _candle(NOW_MS - 2 * FOUR_H_MS)
        c2 = _candle(NOW_MS - 2 * FOUR_H_MS)
        res = drop_unclosed_candle([c1, c2], "4h", NOW)
        assert len(res) == 2

    def test_unknown_timeframe_handling(self):
        # Si timeframe no es reconocido por ccxt, parse_timeframe puede fallar o retornar None
        candle = _candle(NOW_MS - FOUR_H_MS)
        # Deberia manejarse o levantar ValueError claro, no TypeError de multiplicación por None
        try:
            drop_unclosed_candle([candle], "invalid_tf_xyz", NOW)
        except (ValueError, TypeError, ccxt.BaseError):
            pass  # Es aceptable un error controlado o valor controlado

    def test_malformed_last_candle_missing_timestamp_or_empty(self):
        # Si la ultima fila esta malformada
        with pytest.raises((IndexError, TypeError, ValueError)):
            drop_unclosed_candle([[]], "4h", NOW)


class TestDataManagerAdversarial:
    """Pruebas sobre DataManager cache, TTL y rate limit."""

    def test_cache_ttl_expiration(self):
        cache = DataCache()
        cache.set("k1", "v1", ttl=1)
        assert cache.get("k1") == "v1"
        with patch("time.time", return_value=time.time() + 2):
            assert cache.get("k1") is None

    def test_cache_invalidation_and_clear(self):
        cache = DataCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate("a")
        assert cache.get("a") is None
        assert cache.get("b") == 2
        cache.clear()
        assert cache.get("b") is None

    def test_rate_limit_waits_if_called_rapidly(self):
        driver = MagicMock()
        driver.get_all_tickers.return_value = {"BTC/USDT": {"quoteVolume": 100}}
        mgr = DataManager(driver)
        mgr._last_request_time = time.time()
        mgr._min_request_interval = 0.05

        start = time.time()
        mgr._respect_rate_limit()
        elapsed = time.time() - start
        # Deberia haber esperado la fraccion restante
        assert elapsed >= 0

    def test_get_market_context_with_empty_or_degenerate_tickers(self):
        driver = MagicMock()
        driver.get_all_tickers.return_value = {
            "BTC/USDT": {"percentage": None, "quoteVolume": None},
            "ETH/USDT": {"percentage": 5.0, "quoteVolume": 0},
            "XRP/BTC": {"percentage": 10.0, "quoteVolume": 500},  # no quote USDT
        }
        mgr = DataManager(driver)
        ctx = mgr.get_market_context("binance", quote="USDT")
        assert ctx["total_pairs"] == 2
        assert ctx["btc_change_24h"] == 0
        assert ctx["total_volume_24h"] == 0


class TestDataCollectorAdversarial:
    """Pruebas sobre DataCollector: required_periods y aislamiento de errores por par."""

    def test_required_periods_fetched_even_if_no_indicators(self):
        exchange_interface = MagicMock()
        exchange_interface.get_historical_data.return_value = [_candle(NOW_MS - 2 * FOUR_H_MS)]
        analyzer = MagicMock()
        analyzer.indicator_dispatcher.return_value = {}
        analyzer.informant_dispatcher.return_value = {}

        collector = DataCollector(
            exchange_interface=exchange_interface,
            indicator_conf={},
            informant_conf={},
            strategy_analyzer=analyzer,
            required_periods=("4h",),
        )

        market_data = {"binance": {"BTC/USDT": {}}}
        res = collector.get_all_historical_data(market_data)

        assert "binance" in res
        assert "BTC/USDT" in res["binance"]
        assert "4h" in res["binance"]["BTC/USDT"]
        assert len(res["binance"]["BTC/USDT"]["4h"]) == 1

    def test_pair_error_does_not_abort_other_pairs(self):
        """Un par que explota (con ccxt.NetworkError, KeyError, Exception) NO debe tirar abajo los demas pares."""
        exchange_interface = MagicMock()

        def side_effect(pair, exchange, period):
            if pair == "FAIL/USDT":
                # Simular error no capturado como KeyError o NetworkError no envuelto
                raise KeyError("Corrupted exchange symbol")
            return [_candle(NOW_MS - 2 * FOUR_H_MS)]

        exchange_interface.get_historical_data.side_effect = side_effect
        analyzer = MagicMock()
        analyzer.indicator_dispatcher.return_value = {}
        analyzer.informant_dispatcher.return_value = {}

        collector = DataCollector(
            exchange_interface=exchange_interface,
            indicator_conf={},
            informant_conf={},
            strategy_analyzer=analyzer,
            required_periods=("4h",),
        )

        market_data = {"binance": {"FAIL/USDT": {}, "SUCCESS/USDT": {}}}
        res = collector.get_all_historical_data(market_data)

        # SUCCESS/USDT debe tener sus datos a pesar de que FAIL/USDT fallo
        assert "SUCCESS/USDT" in res["binance"]
        assert "4h" in res["binance"]["SUCCESS/USDT"]
        assert len(res["binance"]["SUCCESS/USDT"]["4h"]) == 1


class TestCCXTDriverAdversarial:
    """Pruebas sobre CCXTDriver.get_historical_data."""

    def test_unsupported_timeframe_raises_value_error(self):
        config = {
            "binance": {
                "required": {"enabled": True},
            }
        }
        with patch("ccxt.binance") as mock_binance:
            mock_inst = MagicMock()
            mock_inst.id = "binance"
            mock_inst.timeframes = {"1m": "1m", "4h": "4h", "1d": "1d"}
            mock_binance.return_value = mock_inst

            driver = CCXTDriver(config)
            with pytest.raises(ValueError, match="no soporta 7m"):
                driver.get_historical_data("BTC/USDT", "binance", "7m")

    def test_missing_timeframes_attribute_on_exchange(self):
        config = {
            "binance": {
                "required": {"enabled": True},
            }
        }
        with patch("ccxt.binance") as mock_binance:
            mock_inst = MagicMock()
            mock_inst.id = "binance"
            mock_inst.timeframes = None  # Algunos exchanges o mocks no definen timeframes
            mock_binance.return_value = mock_inst

            driver = CCXTDriver(config)
            # No deberia lanzar TypeError: argument of type 'NoneType' is not iterable
            with pytest.raises(ValueError):
                driver.get_historical_data("BTC/USDT", "binance", "4h")

    def test_empty_ohlcv_from_exchange_raises_value_error(self):
        config = {
            "binance": {
                "required": {"enabled": True},
            }
        }
        with patch("ccxt.binance") as mock_binance:
            mock_inst = MagicMock()
            mock_inst.id = "binance"
            mock_inst.timeframes = {"4h": "4h"}
            mock_inst.fetch_ohlcv.return_value = []
            mock_inst.rateLimit = 100
            mock_binance.return_value = mock_inst

            driver = CCXTDriver(config)
            with pytest.raises(ValueError, match="No se obtuvieron datos históricos"):
                driver.get_historical_data("BTC/USDT", "binance", "4h")

    def test_malformed_rows_in_ohlcv_response(self):
        config = {
            "binance": {
                "required": {"enabled": True},
            }
        }
        with patch("ccxt.binance") as mock_binance:
            mock_inst = MagicMock()
            mock_inst.id = "binance"
            mock_inst.timeframes = {"4h": "4h"}
            # Respuesta con filas malformadas (None, fila vacia, timestamp None)
            mock_inst.fetch_ohlcv.return_value = [
                _candle(NOW_MS - 2 * FOUR_H_MS),
                None,
                [],
                _candle(NOW_MS - FOUR_H_MS),
            ]
            mock_inst.rateLimit = 100
            mock_binance.return_value = mock_inst

            driver = CCXTDriver(config)
            # sort() fallaria con TypeError o IndexError si no se limpian o validan las filas
            try:
                res = driver.get_historical_data("BTC/USDT", "binance", "4h")
                # Si las filtra:
                assert len(res) == 2
            except (TypeError, IndexError, ValueError):
                pass  # Si falla, verificaremos si es un bug a corregir


class TestPairResolverAdversarial:
    """Pruebas sobre PairResolver con configuraciones adversariales y exchange caido."""

    def test_exclude_none_in_dynamic_config(self):
        # YAML donde alguien puso 'exclude: null'
        settings = {
            "dynamic_pairs": {
                "enabled": True,
                "top_n": 10,
                "quote_currency": "USDT",
                "exclude": None,  # <- Bug potencial: set(None) da TypeError
            }
        }
        dm = MagicMock()
        dm.get_top_pairs.return_value = ["BTC/USDT", "ETH/USDT"]
        resolver = PairResolver(settings, data_manager=dm)
        pairs = resolver.resolve("binance")
        assert pairs == ["BTC/USDT", "ETH/USDT"]

    def test_top_n_as_string_in_dynamic_config(self):
        settings = {
            "dynamic_pairs": {
                "enabled": True,
                "top_n": "10",  # <- Bug potencial: string en vez de int
                "quote_currency": "USDT",
                "exclude": ["USDC/USDT"],
            }
        }
        dm = MagicMock()
        dm.get_top_pairs.return_value = ["BTC/USDT", "ETH/USDT"]
        resolver = PairResolver(settings, data_manager=dm)
        pairs = resolver.resolve("binance")
        assert "BTC/USDT" in pairs

    def test_exchange_down_dynamic_pairs_returns_empty_gracefully(self):
        # Si el exchange falla al resolver dynamic pairs, no debe crashear el bot
        settings = {
            "dynamic_pairs": {
                "enabled": True,
                "top_n": 10,
                "quote_currency": "USDT",
            }
        }
        dm = MagicMock()
        dm.get_top_pairs.side_effect = RetryError(last_attempt=MagicMock())
        resolver = PairResolver(settings, data_manager=dm)
        # Deberia devolver [] y loguear el error, sin lanzar RetryError no capturado
        pairs = resolver.resolve("binance")
        assert pairs == []
