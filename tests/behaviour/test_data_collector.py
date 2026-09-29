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


def _skewed_collector(ohlcv, server_minus_local_seconds):
    interface = MagicMock()
    interface.get_historical_data.return_value = ohlcv
    interface.get_server_time_ms.return_value = int((time.time() + server_minus_local_seconds) * 1000)
    return DataCollector(interface, indicator_conf={}, informant_conf={}, strategy_analyzer=MagicMock())


def test_local_clock_ahead_does_not_treat_forming_candle_as_closed():
    """Reloj local 10 min adelantado: por el reloj local la vela ya cerro; por el del exchange todavia no."""
    now_ms = int(time.time() * 1000)
    forming = [now_ms - FOUR_H_MS - 2 * 60 * 1000, 1, 1, 1, 1, 1]   # cerraria hace 2 min segun el reloj local
    older = [forming[0] - FOUR_H_MS, 1, 1, 1, 1, 1]

    result = _skewed_collector([older, forming], -600)._get_historical_data('BTC/USDT', 'binance', '4h')

    assert result == [older]


def test_local_clock_behind_does_not_hide_a_closed_candle():
    """Reloj local 10 min atrasado: por el reloj local la vela sigue abierta; por el del exchange ya cerro."""
    now_ms = int(time.time() * 1000)
    just_closed = [now_ms - FOUR_H_MS + 5 * 60 * 1000, 1, 1, 1, 1, 1]  # cerraria en 5 min segun el reloj local
    older = [just_closed[0] - FOUR_H_MS, 1, 1, 1, 1, 1]

    result = _skewed_collector([older, just_closed], 600)._get_historical_data('BTC/USDT', 'binance', '4h')

    assert result == [older, just_closed]


def test_clock_offset_is_cached_between_pairs():
    now_ms = int(time.time() * 1000)
    start = now_ms - (now_ms % FOUR_H_MS)
    collector = _skewed_collector([[start - FOUR_H_MS, 1, 1, 1, 1, 1]], 0)

    collector._get_historical_data('BTC/USDT', 'binance', '4h')
    collector._get_historical_data('ETH/USDT', 'binance', '4h')

    assert collector.exchange_interface.get_server_time_ms.call_count == 1


def test_clock_check_failure_falls_back_to_local_clock():
    now_ms = int(time.time() * 1000)
    open_candle_start = now_ms - (now_ms % FOUR_H_MS)
    closed = [open_candle_start - FOUR_H_MS, 1, 1, 1, 1, 1]
    forming = [open_candle_start, 1, 1, 1, 1, 1]
    interface = MagicMock()
    interface.get_historical_data.return_value = [closed, forming]
    interface.get_server_time_ms.side_effect = RuntimeError('sin red')
    collector = DataCollector(interface, indicator_conf={}, informant_conf={}, strategy_analyzer=MagicMock())

    assert collector._get_historical_data('BTC/USDT', 'binance', '4h') == [closed]
