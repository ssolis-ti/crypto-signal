"""
Tests para WyckoffAlerter (specs/023-wyckoff-live-alerts/).
"""
import pytest

from analysis.wyckoff_alerts import WyckoffAlerter, EXTREME_VOLUME_THRESHOLD, LOOKBACK


class RecordingNotifier:
    def __init__(self):
        self.messages = []

    def send_direct_text(self, message):
        self.messages.append(message)


def _flat_range_df(n_flat=20, low=99.0, high=101.0, close=100.0):
    closes = [close] * n_flat
    lows = [low] * n_flat
    highs = [high] * n_flat
    volumes = [100.0] * n_flat
    return closes, lows, highs, volumes


def _to_ohlcv_list(closes, lows, highs, volumes, start_ts=1735689600000, step_ms=4 * 3600 * 1000):
    return [
        [start_ts + i * step_ms, closes[i], highs[i], lows[i], closes[i], volumes[i]]
        for i in range(len(closes))
    ]


FIXTURE_FLAT_CANDLES = 30  # comodamente por encima de LOOKBACK+CONFIRM_WINDOW+5 (min_history)


def _spring_fixture(confirm_close=100.0, extreme_volume=True):
    closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
    break_volume = 1000.0 if extreme_volume else 105.0
    closes += [97.0, confirm_close]
    lows += [95.0, 98.0]
    highs += [98.0, 101.0]
    volumes += [break_volume, 100.0]
    return _to_ohlcv_list(closes, lows, highs, volumes)


def _no_event_fixture():
    closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
    closes += [100.0, 100.0]
    lows += [99.2, 99.2]
    highs += [100.8, 100.8]
    volumes += [100.0, 100.0]
    return _to_ohlcv_list(closes, lows, highs, volumes)


class TestWyckoffAlerterSpring:
    def test_confirmed_spring_sends_dual_framed_alert(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())

        assert len(notifier.messages) == 1
        msg = notifier.messages[0]
        assert 'SPRING' in msg
        assert 'BTC/USDT' in msg
        assert 'Rapida' in msg
        assert 'Sostenida' in msg
        assert '72-78%' in msg
        assert '64%' in msg
        assert '+2.84%' in msg
        assert '10%' in msg

    def test_no_alert_without_extreme_volume(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture(extreme_volume=False))

        assert notifier.messages == []

    def test_no_alert_when_no_event(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _no_event_fixture())

        assert notifier.messages == []


class TestWyckoffAlerterUpthrust:
    def test_confirmed_upthrust_sends_cold_framed_alert(self):
        closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
        closes += [103.0, 100.0]
        lows += [102.0, 99.0]
        highs += [105.0, 102.0]
        volumes += [1000.0, 100.0]
        ohlcv = _to_ohlcv_list(closes, lows, highs, volumes)

        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'ETH/USDT', '4h', ohlcv)

        assert len(notifier.messages) == 1
        assert 'UPTHRUST' in notifier.messages[0]


class TestWyckoffAlerterDedup:
    def test_same_confirming_candle_does_not_alert_twice(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        ohlcv = _spring_fixture()

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', ohlcv)
        alerter.check_and_alert('binance', 'BTC/USDT', '4h', ohlcv)  # mismo ciclo repetido

        assert len(notifier.messages) == 1

    def test_different_pairs_alert_independently(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        ohlcv = _spring_fixture()

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', ohlcv)
        alerter.check_and_alert('binance', 'ETH/USDT', '4h', ohlcv)

        assert len(notifier.messages) == 2


class TestWyckoffAlerterGuards:
    def test_disabled_never_alerts(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=False)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())

        assert notifier.messages == []

    def test_wrong_candle_period_not_checked(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '1h', _spring_fixture())

        assert notifier.messages == []

    def test_insufficient_history_no_op(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        short_ohlcv = _to_ohlcv_list(*_flat_range_df(n_flat=5))

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', short_ohlcv)

        assert notifier.messages == []

    def test_empty_historical_data_no_op(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', [])

        assert notifier.messages == []

    def test_detection_exception_is_caught_not_propagated(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        malformed = [[1, 'not-a-number', 2, 3, 4, 5]] * (LOOKBACK + 10)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', malformed)  # no debe lanzar

        assert notifier.messages == []
