"""
Tests adversariales para Area 3:
- app/behaviour/core.py y app/behaviour/strategies.py
- Behaviour.run con datos parciales: par sin '4h', historial de 3 velas, OHLCV con NaN/ceros
- Aislamiento de excepciones: un par con error no debe matar el ciclo ni impedir analizar los demas pares
- Orden de ejecucion: wyckoff_alerter antes de strategy_executor
"""
from unittest.mock import MagicMock, patch, call
import pytest
import pandas as pd
import numpy as np

from behaviour.core import Behaviour
from behaviour.strategies import StrategyExecutor


def _candle(start_ms=1700000000000, close=100.0, volume=10.0):
    return [start_ms, close, close * 1.01, close * 0.99, close, volume]


class TestBehaviourCoreAdversarial:
    """Pruebas adversariales sobre el ciclo de Behaviour.run."""

    @pytest.fixture
    def mock_env(self):
        config = MagicMock()
        config.settings = {
            "enable_charts": False,
            "timezone": "UTC",
            "wyckoff_alerts": {"enabled": True},
            "correlation": {"enabled": False},
        }
        config.indicators = {}
        config.informants = {}
        config.crossovers = {}
        exchange = MagicMock()
        notifier = MagicMock()
        return config, exchange, notifier

    def test_pair_without_4h_does_not_crash_nor_stop_other_pairs(self, mock_env):
        config, exchange, notifier = mock_env
        behaviour = Behaviour(config, exchange, notifier)

        # Simular que all_historical_data tiene par1 sin '4h' y par2 con '4h'
        c_4h = [_candle(1700000000000 + i * 14400000) for i in range(35)]
        historical_data = {
            "binance": {
                "NO_4H/USDT": {"1d": [_candle()]},
                "HAS_4H/USDT": {"4h": c_4h},
            }
        }
        behaviour.data_collector.get_all_historical_data = MagicMock(return_value=historical_data)
        behaviour.strategy_executor.test_strategies = MagicMock(return_value={"binance": {}})

        with patch.object(behaviour.wyckoff_alerter, "_collect_pair", return_value=[]) as mock_check:
            behaviour.run({"binance": {"NO_4H/USDT": {}, "HAS_4H/USDT": {}}}, output_mode="cli")

            # Solo HAS_4H debe haber llamado a check_and_alert con '4h'
            assert mock_check.call_count == 1
            mock_check.assert_called_once_with("binance", "HAS_4H/USDT", "4h", c_4h)
            # strategy_executor debe haberse ejecutado
            behaviour.strategy_executor.test_strategies.assert_called_once()
            notifier.notify_all.assert_called_once()

    def test_short_history_three_candles_and_nan_zeros(self, mock_env):
        config, exchange, notifier = mock_env
        behaviour = Behaviour(config, exchange, notifier)

        # Par con solo 3 velas y par con NaNs y ceros
        nan_candle = [1700000000000, np.nan, np.nan, np.nan, 0.0, 0.0]
        historical_data = {
            "binance": {
                "SHORT/USDT": {"4h": [_candle(), _candle(), _candle()]},
                "DEGEN/USDT": {"4h": [nan_candle for _ in range(30)]},
            }
        }
        behaviour.data_collector.get_all_historical_data = MagicMock(return_value=historical_data)

        # No debe crashear
        behaviour.run({"binance": {"SHORT/USDT": {}, "DEGEN/USDT": {}}}, output_mode="cli")
        notifier.notify_all.assert_called_once()

    def test_exception_in_wyckoff_alerter_does_not_abort_strategy_executor_or_notifier(self, mock_env):
        config, exchange, notifier = mock_env
        behaviour = Behaviour(config, exchange, notifier)

        historical_data = {
            "binance": {
                "PAIR1/USDT": {"4h": [_candle() for _ in range(35)]},
                "PAIR2/USDT": {"4h": [_candle() for _ in range(35)]},
            }
        }
        behaviour.data_collector.get_all_historical_data = MagicMock(return_value=historical_data)
        behaviour.strategy_executor.test_strategies = MagicMock(return_value={"binance": {"PAIR1/USDT": {}, "PAIR2/USDT": {}}})

        def side_effect(ex, pair, period, data):
            if pair == "PAIR1/USDT":
                raise RuntimeError("Catastrophic error in Wyckoff detection")

        with patch.object(behaviour.wyckoff_alerter, "_collect_pair", side_effect=side_effect) as mock_check:
            # No debe propagar RuntimeError
            behaviour.run({"binance": {"PAIR1/USDT": {}, "PAIR2/USDT": {}}}, output_mode="cli")

            # PAIR2 debe haber sido chequeado a pesar de la excepcion en PAIR1
            assert mock_check.call_count == 2
            # strategy_executor y notifier deben completarse
            behaviour.strategy_executor.test_strategies.assert_called_once()
            notifier.notify_all.assert_called_once()

    def test_wyckoff_alerter_runs_before_strategy_executor(self, mock_env):
        config, exchange, notifier = mock_env
        behaviour = Behaviour(config, exchange, notifier)

        historical_data = {
            "binance": {
                "BTC/USDT": {"4h": [_candle() for _ in range(35)]},
            }
        }
        behaviour.data_collector.get_all_historical_data = MagicMock(return_value=historical_data)

        call_order = []
        with patch.object(behaviour.wyckoff_alerter, "_collect_pair", side_effect=lambda *args: call_order.append("wyckoff") or []), \
             patch.object(behaviour.strategy_executor, "test_strategies", side_effect=lambda *args: (call_order.append("strategies"), {"binance": {}})[1]):
            behaviour.run({"binance": {"BTC/USDT": {}}}, output_mode="cli")

            assert call_order == ["wyckoff", "strategies"]

    def test_strategy_executor_pair_isolation_on_indicator_error(self):
        """Si un par o indicador falla con ValueError o IndexError en StrategyExecutor, no debe abortar los demas pares."""
        config = MagicMock()
        config.indicators = {
            "rsi": [{"enabled": True, "candle_period": "1d", "signal": ["rsi"], "period_count": 14}]
        }
        config.informants = {}
        config.crossovers = {}

        analyzer = MagicMock()
        dispatcher = {}

        def bad_rsi(**kwargs):
            hist = kwargs.get("historical_data")
            if len(hist) < 5:
                raise ValueError("Too few rows for RSI")
            return pd.DataFrame({"rsi": [50.0], "is_hot": [False], "is_cold": [False]})

        dispatcher["rsi"] = bad_rsi
        analyzer.indicator_dispatcher.return_value = dispatcher
        analyzer.informant_dispatcher.return_value = {}
        analyzer.crossover_dispatcher.return_value = {}

        executor = StrategyExecutor(config, analyzer)

        market_data = {
            "binance": {
                "FAIL/USDT": {},
                "GOOD/USDT": {},
            }
        }
        all_hist = {
            "binance": {
                "FAIL/USDT": {"1d": [_candle()]},  # Solo 1 vela -> dispara ValueError
                "GOOD/USDT": {"1d": [_candle() for _ in range(20)]},
            }
        }

        # No debe lanzar ValueError; GOOD/USDT debe ser analizado
        res = executor.test_strategies(market_data, all_hist, output_mode="cli")
        assert "binance" in res
        assert "GOOD/USDT" in res["binance"]
        assert "FAIL/USDT" in res["binance"]
        assert len(res["binance"]["GOOD/USDT"]["indicators"]["rsi"]) == 1
        assert isinstance(res["binance"]["GOOD/USDT"]["indicators"]["rsi"][0]["result"], pd.DataFrame)
