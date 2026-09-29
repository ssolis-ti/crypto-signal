"""
El camino principal del pipeline (DataCollector -> CCXTDriver) debe descartar la vela en
formacion igual que DataManager.get_ohlcv (Principio II, specs/001-no-repaint-signals/).
"""
import time
from unittest.mock import MagicMock

from behaviour.data import DataCollector

FOUR_H_MS = 4 * 3600 * 1000


def _collector(ohlcv):
    interface = MagicMock()
    interface.get_historical_data.return_value = ohlcv
    return DataCollector(interface, indicator_conf={}, informant_conf={}, strategy_analyzer=MagicMock())


def test_unclosed_4h_candle_is_dropped():
    now_ms = int(time.time() * 1000)
    open_candle_start = now_ms - (now_ms % FOUR_H_MS)  # vela de 4h en curso
    closed = [open_candle_start - FOUR_H_MS, 1, 1, 1, 1, 1]
    forming = [open_candle_start, 1, 1, 1, 1, 1]

    result = _collector([closed, forming])._get_historical_data('BTC/USDT', 'binance', '4h')

    assert result == [closed]


def test_required_period_is_fetched_without_any_indicator():
    now_ms = int(time.time() * 1000)
    start = now_ms - (now_ms % FOUR_H_MS)
    closed = [start - FOUR_H_MS, 1, 1, 1, 1, 1]
    interface = MagicMock()
    interface.get_historical_data.return_value = [closed]
    collector = DataCollector(interface, indicator_conf={}, informant_conf={},
                              strategy_analyzer=MagicMock(), required_periods=('4h',))

    data = collector.get_all_historical_data({'binance': {'BTC/USDT': {}}})

    assert data['binance']['BTC/USDT']['4h'] == [closed]


def test_no_required_periods_fetches_nothing_extra():
    interface = MagicMock()
    collector = DataCollector(interface, indicator_conf={}, informant_conf={}, strategy_analyzer=MagicMock())

    data = collector.get_all_historical_data({'binance': {'BTC/USDT': {}}})

    assert data['binance']['BTC/USDT'] == {}
    interface.get_historical_data.assert_not_called()


def test_closed_candles_are_kept():
    now_ms = int(time.time() * 1000)
    open_candle_start = now_ms - (now_ms % FOUR_H_MS)
    older = [open_candle_start - 2 * FOUR_H_MS, 1, 1, 1, 1, 1]
    closed = [open_candle_start - FOUR_H_MS, 1, 1, 1, 1, 1]

    result = _collector([older, closed])._get_historical_data('BTC/USDT', 'binance', '4h')

    assert result == [older, closed]
