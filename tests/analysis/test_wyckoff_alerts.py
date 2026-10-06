"""
Tests para WyckoffAlerter (specs/023-wyckoff-live-alerts/).
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pandas as pd
import pytest

from analyzers.utils import IndicatorUtils
from analyzers.indicators.wyckoff import WyckoffPrimitives
from analysis.wyckoff_alerts import (
    WyckoffAlerter, EXTREME_VOLUME_THRESHOLD, LOOKBACK,
    CANDLE_SECONDS, MAX_DEDUP_SIGNATURES,
)

STALE_ALERT_SECONDS = 2 * 3600  # umbral del aviso tardio (analysis/alert_text.py: mas de 2 h)


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


def _liquid(ohlcv, factor=500):
    """Escala el volumen sin cambiar el volumen relativo. 500 deja las velas de juguete sobre 20 millones USD."""
    out = []
    for row in ohlcv:
        row = list(row)
        row[5] = row[5] * factor
        out.append(row)
    return out


class TestWyckoffAlerterSpring:
    def test_confirmed_spring_sends_a_plain_language_buy_plan(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())

        assert len(notifier.messages) == 1
        msg = notifier.messages[0]
        assert msg.startswith('🟢 <b>OPORTUNIDAD DE COMPRA: BTC/USDT</b>')
        assert 'Paso a paso' in msg
        assert 'stop loss' in msg and '−10%' in msg
        assert 'a precio de mercado' in msg
        assert '72 h después' in msg
        assert 'no promedies a la baja' in msg
        assert not any(word in msg for word in ('Spring', 'Upthrust', 'Wyckoff', 'backtest', 'Backtest', 'trampa')), 'el aviso no debe traer jerga tecnica'

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
    def test_confirmed_upthrust_is_recorded_and_not_sent(self, tmp_path):
        closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
        closes += [103.0, 100.0]
        lows += [102.0, 99.0]
        highs += [105.0, 102.0]
        volumes += [1000.0, 100.0]
        ohlcv = _to_ohlcv_list(closes, lows, highs, volumes)

        path = tmp_path / 'record.jsonl'
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path))

        alerter.check_and_alert('binance', 'ETH/USDT', '4h', ohlcv)
        alerter.check_and_alert('binance', 'ETH/USDT', '4h', ohlcv)

        assert notifier.messages == []
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert len(records) == 1
        assert records[0]['direction'] == 'cold' and records[0]['pair'] == 'ETH/USDT'


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


class TestWyckoffAlerterTwitterSentiment:
    def test_twitter_disabled_by_default_omits_section(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)  # twitter_sentiment_enabled defaults False

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())

        assert len(notifier.messages) == 1
        assert 'Twitter' not in notifier.messages[0]

    def test_twitter_enabled_appends_section_when_analyzer_returns_result(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, twitter_sentiment_enabled=True)

        fake_result = {
            'sentiment_extreme': 'capitulation', 'social_spike_confirmed': True,
            'catalyst_present': False, 'summary': 'Resumen de prueba.',
        }
        with patch.object(alerter.twitter_sentiment, 'analyze', return_value=fake_result):
            alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())

        assert len(notifier.messages) == 1
        assert 'Twitter' in notifier.messages[0]
        assert 'Resumen de prueba.' in notifier.messages[0]

    def test_twitter_enabled_but_analyzer_returns_none_omits_section(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, twitter_sentiment_enabled=True)

        with patch.object(alerter.twitter_sentiment, 'analyze', return_value=None):
            alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())

        assert len(notifier.messages) == 1
        assert 'Twitter' not in notifier.messages[0]


def _volume_spike_no_event_fixture():
    closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
    closes += [100.5]
    lows += [99.5]
    highs += [100.8]
    volumes += [1000.0]  # 10x el promedio, sin romper el rango
    return _to_ohlcv_list(closes, lows, highs, volumes)


def _velocity(ratio):
    return {'current': 3.0 * ratio, 'baseline': 3.0, 'ratio': ratio, 'max_views': 0,
            'tweets': [{'text': 'x'}]}


class TestRumorRadar:
    def _alerter(self, tmp_path, radar=True, twitter=True):
        return WyckoffAlerter(RecordingNotifier(), enabled=True, twitter_sentiment_enabled=twitter,
                              rumor_radar_enabled=radar, record_path=str(tmp_path / 'radar.jsonl'))

    def test_radar_disabled_by_default(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, twitter_sentiment_enabled=True)
        with patch.object(alerter.twitter_sentiment, 'mention_velocity') as mock_vel:
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', _volume_spike_no_event_fixture())
        mock_vel.assert_not_called()
        assert notifier.messages == []

    def test_radar_requires_twitter(self, tmp_path):
        alerter = self._alerter(tmp_path, radar=True, twitter=False)
        assert alerter.rumor_radar_enabled is False

    def test_accelerating_mentions_are_recorded_and_not_sent(self, tmp_path):
        alerter = self._alerter(tmp_path)
        with patch.object(alerter.twitter_sentiment, 'mention_velocity', return_value=_velocity(3.0)), \
             patch.object(alerter.twitter_sentiment, 'analyze', return_value={
                 'current': 9.0, 'baseline': 3.0, 'ratio': 3.0, 'max_views': 0,
                 'sentiment_extreme': 'euphoria', 'social_spike_confirmed': False,
                 'catalyst_present': True, 'summary': 'Rumor de listing.'}):
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', _volume_spike_no_event_fixture())

        assert alerter.notifier.messages == []
        record = json.loads((tmp_path / 'radar.jsonl').read_text().strip())
        assert record['type'] == 'radar' and record['alert_sent'] is False
        assert record['sentiment'] == 'euphoria' and record['pair'] == 'SOL/USDT'

    def test_quiet_mentions_record_without_alert(self, tmp_path):
        alerter = self._alerter(tmp_path)
        with patch.object(alerter.twitter_sentiment, 'mention_velocity', return_value=_velocity(1.2)):
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', _volume_spike_no_event_fixture())

        assert alerter.notifier.messages == []
        record = json.loads((tmp_path / 'radar.jsonl').read_text().strip())
        assert record['alert_sent'] is False

    def test_same_candle_queries_twitter_once(self, tmp_path):
        alerter = self._alerter(tmp_path)
        ohlcv = _volume_spike_no_event_fixture()
        with patch.object(alerter.twitter_sentiment, 'mention_velocity', return_value=_velocity(1.2)) as mock_vel:
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
        assert mock_vel.call_count == 1

    def test_twitter_failure_retries_next_cycle_then_gives_up(self, tmp_path):
        alerter = self._alerter(tmp_path)
        ohlcv = _volume_spike_no_event_fixture()
        with patch.object(alerter.twitter_sentiment, 'mention_velocity', return_value=None) as mock_vel:
            for _ in range(5):
                alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
        assert mock_vel.call_count == 3  # RADAR_MAX_FAILURES, luego se marca la vela

    def test_twitter_recovers_on_second_cycle(self, tmp_path):
        alerter = self._alerter(tmp_path)
        ohlcv = _volume_spike_no_event_fixture()
        with patch.object(alerter.twitter_sentiment, 'mention_velocity',
                          side_effect=[None, _velocity(1.1)]) as mock_vel:
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
        assert mock_vel.call_count == 2
        assert (tmp_path / 'radar.jsonl').exists()

    def test_normal_volume_does_not_query_twitter(self, tmp_path):
        alerter = self._alerter(tmp_path)
        with patch.object(alerter.twitter_sentiment, 'mention_velocity') as mock_vel:
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', _no_event_fixture())
        mock_vel.assert_not_called()


class TestDedupSurvivesRestart:
    def test_wyckoff_alert_not_repeated_after_restart(self, tmp_path):
        path = str(tmp_path / 'record.jsonl')
        first = WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=path)
        first.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())
        assert len(first.notifier.messages) == 1

        restarted = WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=path)
        restarted.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())
        assert restarted.notifier.messages == []

    def test_radar_candle_not_requeried_after_restart(self, tmp_path):
        path = str(tmp_path / 'record.jsonl')
        first = WyckoffAlerter(RecordingNotifier(), enabled=True, twitter_sentiment_enabled=True,
                               rumor_radar_enabled=True, record_path=path)
        ohlcv = _volume_spike_no_event_fixture()
        with patch.object(first.twitter_sentiment, 'mention_velocity', return_value=_velocity(1.1)):
            first.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)

        restarted = WyckoffAlerter(RecordingNotifier(), enabled=True, twitter_sentiment_enabled=True,
                                   rumor_radar_enabled=True, record_path=path)
        with patch.object(restarted.twitter_sentiment, 'mention_velocity') as mock_vel:
            restarted.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
        mock_vel.assert_not_called()

    def test_corrupt_record_lines_are_ignored(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        path.write_text('esto no es json\n{"type": "wyckoff"}\n')
        alerter = WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=str(path))
        assert alerter._alerted_signatures == {}


class TestDedupPruneAndStale:
    def test_prune_drops_oldest_and_keeps_newest(self):
        alerter = WyckoffAlerter(RecordingNotifier(), enabled=True)
        for i in range(6):
            alerter._remember(f'sig_{i}')
        alerter._prune_signatures(max_size=3)
        assert list(alerter._alerted_signatures) == ['sig_3', 'sig_4', 'sig_5']

    def test_fresh_alert_has_no_stale_notice(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        ohlcv = _spring_fixture()
        last_open = datetime.fromtimestamp(ohlcv[-1][0] / 1000, tz=timezone.utc)
        with patch.object(WyckoffAlerter, '_now_utc', return_value=last_open + timedelta(hours=4, minutes=5)):
            alerter.check_and_alert('binance', 'BTC/USDT', '4h', ohlcv)
        assert 'Aviso tardío' not in notifier.messages[0]

    def test_alert_after_long_downtime_is_marked_stale(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        ohlcv = _spring_fixture()
        last_open = datetime.fromtimestamp(ohlcv[-1][0] / 1000, tz=timezone.utc)
        with patch.object(WyckoffAlerter, '_now_utc', return_value=last_open + timedelta(hours=8)):
            alerter.check_and_alert('binance', 'BTC/USDT', '4h', ohlcv)
        assert 'Aviso tardío' in notifier.messages[0]
        assert 'hace 4.0 h' in notifier.messages[0]


class TestSignalQualityContext:
    """Profundidad de la barrida y springs simultaneos: se muestran y registran, NUNCA filtran."""

    def test_sweep_depth_is_measured_on_the_breaking_candle(self):
        from analyzers.utils import IndicatorUtils
        # soporte 99.0; la vela de ruptura llega a 95.0 -> (99-95)/99 = 4.04%
        df = IndicatorUtils().convert_to_dataframe(_spring_fixture())
        depth = WyckoffAlerter._sweep_depth(df, 'hot')
        assert depth == pytest.approx(4.04, abs=0.01)

    def test_isolated_liquid_spring_is_recorded_and_not_sent(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path))
        pairs = {'BTC/USDT': _liquid(_spring_fixture())}
        pairs.update({f'Q{i}/USDT': _liquid(_no_event_fixture()) for i in range(9)})  # 1 de 10 = 10%
        alerter.check_cycle('binance', pairs)
        alerter.check_cycle('binance', pairs)

        assert notifier.messages == []
        assert not (tmp_path / 'telegram_sent.jsonl').exists()
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert len(records) == 1
        assert records[0]['pair'] == 'BTC/USDT' and records[0]['eligible'] is True
        assert records[0]['concurrent_pairs'] == 1 and records[0]['watched_pairs'] == 10

    def test_illiquid_spring_stays_out_of_a_wide_order(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path))
        pairs = {f'P{i}/USDT': _liquid(_spring_fixture()) for i in range(3)}
        pairs.update({f'Q{i}/USDT': _liquid(_no_event_fixture()) for i in range(7)})
        pairs['DUST/USDT'] = _spring_fixture()
        alerter.check_cycle('binance', pairs)

        assert len(notifier.messages) == 1
        assert 'DUST' not in notifier.messages[0]
        assert all(f'P{i}/USDT' in notifier.messages[0] for i in range(3))
        dust = [json.loads(line) for line in path.read_text().splitlines() if '"DUST/USDT"' in line]
        assert len(dust) == 1 and dust[0]['eligible'] is False

    def test_simultaneous_springs_are_counted_and_sent_as_one_message(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        pairs = {f'P{i}/USDT': _liquid(_spring_fixture()) for i in range(5)}
        pairs.update({f'Q{i}/USDT': _liquid(_no_event_fixture()) for i in range(5)})  # 5 de 10 = 50%
        alerter.check_cycle('binance', pairs)

        assert len(notifier.messages) == 1, 'las señales de una misma vela salen juntas en UN mensaje'
        msg = notifier.messages[0]
        assert 'pánico generalizado' in msg and '5 de 10 monedas (50%)' in msg
        assert all(f'P{i}/USDT' in msg for i in range(5)), 'la lista trae las 5 monedas con precio y stop'
        assert 'Compra (long) <b>varias monedas de la lista</b>' in msg

    def test_a_single_liquid_pair_is_wide_and_is_sent(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path))
        alerter.check_cycle('binance', {'BTC/USDT': _liquid(_spring_fixture())})  # 1 de 1 = 100%

        assert len(notifier.messages) == 1
        sent = json.loads((tmp_path / 'telegram_sent.jsonl').read_text().strip())
        assert sent['kind'] == 'wyckoff_hot' and sent['pairs'] == ['BTC/USDT']
        assert 'Entrada:' in sent['text'] and 'Stop:' in sent['text'] and 'Salida:' in sent['text']

    def test_context_is_recorded_for_forward_validation(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        alerter = WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=str(path))
        alerter.check_cycle('binance', {'BTC/USDT': _spring_fixture()})  # volumen de juguete: no es elegible

        record = json.loads(path.read_text().strip())
        assert record['type'] == 'wyckoff'
        assert record['eligible'] is False
        assert record['concurrent_pairs'] is None
        assert record['sweep_depth_pct'] == pytest.approx(4.04, abs=0.01)
        assert 'change_24h_pct' in record
        assert not (tmp_path / 'telegram_sent.jsonl').exists()

    def test_microstructure_snapshot_is_recorded_not_shown(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path), microstructure_enabled=True)
        alerter.microstructure.snapshot = lambda exchange, pair: {'funding_rate_pct': 0.01}
        alerter.check_cycle('binance', {'BTC/USDT': _liquid(_spring_fixture())})

        assert json.loads(path.read_text().strip())['micro'] == {'funding_rate_pct': 0.01}
        assert '0.01' not in notifier.messages[0] and 'micro' not in notifier.messages[0].lower()

    def test_microstructure_failure_never_breaks_the_alert(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path), microstructure_enabled=True)

        def boom(exchange, pair):
            raise RuntimeError('binance caido')
        alerter.microstructure.snapshot = boom
        alerter.check_cycle('binance', {'BTC/USDT': _liquid(_spring_fixture())})

        assert len(notifier.messages) == 1
        assert json.loads(path.read_text().strip())['micro'] is None

    def test_disabled_check_cycle_does_nothing(self):
        notifier = RecordingNotifier()
        WyckoffAlerter(notifier, enabled=False).check_cycle('binance', {'BTC/USDT': _spring_fixture()})
        assert notifier.messages == []

    def test_one_pair_failing_does_not_stop_the_cycle(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        pairs = {'BAD/USDT': [[1, 'x']] * 40, 'BTC/USDT': _liquid(_spring_fixture())}
        alerter.check_cycle('binance', pairs)
        assert len(notifier.messages) == 1


class TestExecutionGuidanceAndWeekend:
    """Guia de ejecucion medida con velas de 1 minuto (specs/036-minutos-criticos/)."""

    def test_spring_message_has_execution_guidance(self):
        notifier = RecordingNotifier()
        WyckoffAlerter(notifier, enabled=True).check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())

        msg = notifier.messages[0]
        assert 'ahora, a precio de mercado' in msg
        assert 'Esperar más no mejora el resultado' in msg
        assert 'No cierres antes por miedo' in msg
        assert 'no lo muevas ni lo quites' in msg

    def test_upthrust_does_not_send_a_trade_message(self):
        closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
        closes += [103.0, 100.0]
        lows += [102.0, 99.0]
        highs += [105.0, 102.0]
        volumes += [1000.0, 100.0]
        notifier = RecordingNotifier()
        WyckoffAlerter(notifier, enabled=True).check_and_alert(
            'binance', 'ETH/USDT', '4h', _to_ohlcv_list(closes, lows, highs, volumes))

        assert notifier.messages == []

    def test_weekend_is_decided_by_the_closing_time_of_the_candle(self):
        # vela 4h que abre viernes 20:00 UTC cierra sabado 00:00 -> cuenta como fin de semana
        assert WyckoffAlerter._is_weekend_close(pd.Timestamp('2026-09-25 20:00', tz='UTC')) is True
        # vela que abre sabado 20:00 cierra domingo 00:00 -> fin de semana
        assert WyckoffAlerter._is_weekend_close(pd.Timestamp('2026-09-26 20:00', tz='UTC')) is True
        # vela que abre domingo 20:00 cierra lunes 00:00 -> no
        assert WyckoffAlerter._is_weekend_close(pd.Timestamp('2026-09-27 20:00', tz='UTC')) is False
        assert WyckoffAlerter._is_weekend_close(pd.Timestamp('2026-09-29 12:00', tz='UTC')) is False
        assert WyckoffAlerter._is_weekend_close(None) is False

    def test_weekend_flag_is_recorded(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=str(path)).check_cycle(
            'binance', {'BTC/USDT': _spring_fixture()})
        assert 'weekend_close' in json.loads(path.read_text().strip())


class TestMessageHonestyAndRadarStale:
    def test_spring_message_is_honest_about_risk_and_never_assumes_the_capital(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())

        msg = notifier.messages[0]
        assert 'no es seguro' in msg.lower() or 'No es seguro' in msg
        assert '4 a 5 de cada 10' in msg
        assert 'deslistaron' in msg
        assert 'No es asesoría financiera' in msg
        assert '+92%' not in msg  # cifra de un formato distinto; se presentaba como tasa de la estrategia
        # el capital del operador no es el de la config de prueba de Freqtrade (100 USDT, 3 x 30)
        assert '100 USDT' not in msg and '30 USDT' not in msg

    def test_radar_after_downtime_is_recorded_and_not_sent(self, tmp_path):
        alerter = WyckoffAlerter(RecordingNotifier(), enabled=True, twitter_sentiment_enabled=True,
                                 rumor_radar_enabled=True, record_path=str(tmp_path / 'radar.jsonl'))
        ohlcv = _volume_spike_no_event_fixture()
        last_open = datetime.fromtimestamp(ohlcv[-1][0] / 1000, tz=timezone.utc)
        with patch.object(WyckoffAlerter, '_now_utc', return_value=last_open + timedelta(hours=9)), \
             patch.object(alerter.twitter_sentiment, 'mention_velocity', return_value=_velocity(3.0)), \
             patch.object(alerter.twitter_sentiment, 'analyze', return_value={
                 'current': 9.0, 'baseline': 3.0, 'ratio': 3.0, 'max_views': 0,
                 'sentiment_extreme': None, 'social_spike_confirmed': False,
                 'catalyst_present': False, 'summary': ''}):
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)

        assert alerter.notifier.messages == []
        assert json.loads((tmp_path / 'radar.jsonl').read_text().strip())['alert_sent'] is False


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


# ─────────────────────────────────────────────────────────────────────────────
# QA adversarial: bordes de umbral, degenerados y comportamiento documentado.
# ─────────────────────────────────────────────────────────────────────────────

def _fake_detection(df, spring=False, upthrust=False,
                    spring_rv=float('nan'), upthrust_rv=float('nan')):
    """DataFrames de deteccion con el flag y el volumen de ruptura solo en la ultima vela."""
    springs = pd.DataFrame({
        'is_spring': [False] * (len(df) - 1) + [spring],
        'break_relative_volume': [float('nan')] * (len(df) - 1) + [spring_rv],
    }, index=df.index)
    upthrusts = pd.DataFrame({
        'is_upthrust': [False] * (len(df) - 1) + [upthrust],
        'break_relative_volume': [float('nan')] * (len(df) - 1) + [upthrust_rv],
    }, index=df.index)
    return springs, upthrusts


class TestVolumeThresholdBoundary:
    """El edge se valido con `>= 2.5x`; el borde exacto debe disparar."""

    def _run(self, spring=True, upthrust=False,
             spring_rv=float('nan'), upthrust_rv=float('nan')):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        ohlcv = _no_event_fixture()
        df = IndicatorUtils().convert_to_dataframe(ohlcv)
        springs, upthrusts = _fake_detection(
            df, spring=spring, upthrust=upthrust,
            spring_rv=spring_rv, upthrust_rv=upthrust_rv)
        with patch.object(WyckoffPrimitives, 'detect_springs', return_value=springs), \
             patch.object(WyckoffPrimitives, 'detect_upthrusts', return_value=upthrusts):
            alerter.check_and_alert('binance', 'BTC/USDT', '4h', ohlcv)
        return notifier.messages

    def test_exactly_25x_relative_volume_alerts(self):
        messages = self._run(spring_rv=2.5)
        assert len(messages) == 1
        assert messages[0].startswith('🟢')

    def test_just_below_25x_does_not_alert(self):
        assert self._run(spring_rv=2.4999) == []

    def test_nan_break_volume_never_alerts(self):
        # Volumen relativo NaN (p. ej. promedio 0) no debe tomarse como extremo.
        assert self._run(spring_rv=float('nan')) == []

    def test_spring_wins_over_upthrust_on_same_candle(self):
        # Documenta la precedencia actual: si una misma vela cierra ambos eventos,
        # solo se envia el Spring (la rama `elif` del upthrust no se evalua).
        messages = self._run(spring=True, upthrust=True, spring_rv=3.0, upthrust_rv=3.0)
        assert len(messages) == 1
        assert messages[0].startswith('🟢')
        assert 'OPORTUNIDAD DE COMPRA' in messages[0]
        assert 'Aviso informativo' not in messages[0]


class TestDetectionDegenerateInputs:
    def test_all_zero_volume_does_not_alert_or_crash(self):
        closes, lows, highs, _ = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
        closes += [97.0, 100.0]
        lows += [95.0, 98.0]
        highs += [98.0, 101.0]
        volumes = [0.0] * (FIXTURE_FLAT_CANDLES + 2)
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h',
                                _to_ohlcv_list(closes, lows, highs, volumes))

        assert notifier.messages == []

    def test_flat_range_never_breaks(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        ohlcv = _to_ohlcv_list(*_flat_range_df(n_flat=FIXTURE_FLAT_CANDLES + 5))

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', ohlcv)

        assert notifier.messages == []

    @staticmethod
    def _late_fixture(extra_candles):
        """Spring confirmado y despues `extra_candles` velas tranquilas (el bot estaba apagado)."""
        closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
        closes += [97.0, 100.0] + [100.5] * extra_candles
        lows += [95.0, 98.0] + [99.5] * extra_candles
        highs += [98.0, 101.0] + [101.0] * extra_candles
        volumes += [1000.0, 100.0] + [100.0] * extra_candles
        return _to_ohlcv_list(closes, lows, highs, volumes)

    def test_spring_confirmed_while_bot_was_off_is_alerted_late(self):
        """Antes se perdia en silencio (solo se miraba la ultima vela); ahora se avisa hasta 12h despues."""
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', self._late_fixture(2))

        assert len(notifier.messages) == 1
        assert 'Aviso tardío' in notifier.messages[0]
        assert 'OPORTUNIDAD DE COMPRA' in notifier.messages[0]

    def test_late_spring_is_not_repeated_on_later_cycles(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        data = self._late_fixture(1)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', data)
        alerter.check_and_alert('binance', 'BTC/USDT', '4h', data)
        alerter.check_and_alert('binance', 'BTC/USDT', '4h', self._late_fixture(2))  # una vela mas

        assert len(notifier.messages) == 1

    def test_spring_older_than_the_limit_is_not_alerted(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)

        alerter.check_and_alert('binance', 'BTC/USDT', '4h', self._late_fixture(4))  # 16h: ya no vale la pena

        assert notifier.messages == []

    def test_already_alerted_spring_is_not_repeated_after_restart(self, tmp_path):
        path = str(tmp_path / 'record.jsonl')
        first = WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=path)
        first.check_and_alert('binance', 'BTC/USDT', '4h', self._late_fixture(0))  # a tiempo
        restarted_notifier = RecordingNotifier()
        restarted = WyckoffAlerter(restarted_notifier, enabled=True, record_path=path)

        restarted.check_and_alert('binance', 'BTC/USDT', '4h', self._late_fixture(2))  # PC apagada un rato

        assert restarted_notifier.messages == []

    def test_late_events_count_as_concurrent_pairs(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        pairs = {f'P{i}/USDT': _liquid(self._late_fixture(1)) for i in range(5)}

        alerter.check_cycle('binance', pairs)

        assert len(notifier.messages) == 1
        assert '5 de 5 monedas' in notifier.messages[0]


class TestChange24h:
    def test_fewer_than_seven_candles_returns_none(self):
        assert WyckoffAlerter._change_24h(pd.DataFrame({'close': [1.0] * 6})) is None

    def test_seven_candles_uses_the_close_seven_back(self):
        df = pd.DataFrame({'close': [100.0] * 6 + [110.0]})
        assert WyckoffAlerter._change_24h(df) == pytest.approx(10.0)

    def test_zero_price_seven_candles_back_returns_none(self):
        df = pd.DataFrame({'close': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
        assert WyckoffAlerter._change_24h(df) is None


class TestStaleNoticeBoundaries:
    def _alerter(self):
        return WyckoffAlerter(RecordingNotifier(), enabled=True)

    def _closed_at(self):
        # timestamp = apertura de la vela; cierra CANDLE_SECONDS despues.
        return datetime(2026, 9, 29, 8, 0, tzinfo=timezone.utc)

    def test_exactly_two_hours_after_close_has_no_notice(self):
        from analysis.alert_text import late_notice
        ts = self._closed_at()
        now = ts + timedelta(seconds=CANDLE_SECONDS + STALE_ALERT_SECONDS)
        with patch.object(WyckoffAlerter, '_now_utc', return_value=now):
            assert late_notice(self._alerter()._elapsed_hours(ts)) == ''

    def test_one_second_over_two_hours_has_notice(self):
        from analysis.alert_text import late_notice
        ts = self._closed_at()
        now = ts + timedelta(seconds=CANDLE_SECONDS + STALE_ALERT_SECONDS + 1)
        with patch.object(WyckoffAlerter, '_now_utc', return_value=now):
            assert 'Aviso tardío' in late_notice(self._alerter()._elapsed_hours(ts))

    def test_future_timestamp_has_no_notice(self):
        from analysis.alert_text import late_notice
        ts = self._closed_at()
        with patch.object(WyckoffAlerter, '_now_utc', return_value=ts + timedelta(hours=1)):
            assert late_notice(self._alerter()._elapsed_hours(ts)) == ''

    def test_missing_timestamp_has_no_notice(self):
        from analysis.alert_text import late_notice
        assert late_notice(self._alerter()._elapsed_hours(None)) == ''

    def test_naive_timestamp_raises_type_error(self):
        # Caracterizacion: la ruta de produccion siempre entrega index UTC-aware
        # (convert_to_dataframe(..., utc=True)); un timestamp naive rompe la resta.
        with pytest.raises(TypeError):
            self._alerter()._elapsed_hours(datetime(2026, 9, 29, 8, 0))


class TestDedupRecordLoading:
    def _load(self, tmp_path, content):
        path = tmp_path / 'record.jsonl'
        path.write_text(content, encoding='utf-8')
        return WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=str(path))

    def test_empty_file_loads_nothing(self, tmp_path):
        alerter = self._load(tmp_path, '')
        assert alerter._alerted_signatures == {}

    def test_truncated_last_line_keeps_previous_valid_signatures(self, tmp_path):
        valid = json.dumps({'type': 'wyckoff', 'direction': 'hot', 'exchange': 'binance',
                            'pair': 'BTC/USDT', 'candle': '2026-01-01T00:00:00+00:00'})
        alerter = self._load(tmp_path, valid + '\n{"type": "wyckoff", "direction": "col')
        assert list(alerter._alerted_signatures) == [
            'binance:BTC/USDT:hot:2026-01-01T00:00:00+00:00']

    def test_line_missing_candle_or_pair_is_ignored(self, tmp_path):
        alerter = self._load(
            tmp_path,
            json.dumps({'type': 'wyckoff', 'direction': 'hot'}) + '\n')
        assert alerter._alerted_signatures == {}

    def test_radar_and_wyckoff_signatures_are_both_loaded(self, tmp_path):
        lines = [
            json.dumps({'type': 'radar', 'exchange': 'binance', 'pair': 'SOL/USDT',
                        'candle': '2026-01-01T00:00:00+00:00'}),
            json.dumps({'type': 'wyckoff', 'direction': 'cold', 'exchange': 'binance',
                        'pair': 'ETH/USDT', 'candle': '2026-01-01T04:00:00+00:00'}),
        ]
        alerter = self._load(tmp_path, '\n'.join(lines) + '\n')
        assert set(alerter._alerted_signatures) == {
            'binance:SOL/USDT:radar:2026-01-01T00:00:00+00:00',
            'binance:ETH/USDT:cold:2026-01-01T04:00:00+00:00',
        }

    def test_more_than_max_lines_keeps_only_the_last_window(self, tmp_path):
        lines = [
            json.dumps({'type': 'wyckoff', 'direction': 'hot', 'exchange': 'binance',
                        'pair': 'BTC/USDT', 'candle': f'2026-01-01T00:{i:02d}:00+00:00'})
            for i in range(MAX_DEDUP_SIGNATURES + 100)
        ]
        alerter = self._load(tmp_path, '\n'.join(lines) + '\n')
        assert len(alerter._alerted_signatures) == MAX_DEDUP_SIGNATURES


class TestRadarEdges:
    def _alerter(self, tmp_path, radar_min_ratio=2.0):
        return WyckoffAlerter(RecordingNotifier(), enabled=True, twitter_sentiment_enabled=True,
                              rumor_radar_enabled=True, radar_min_ratio=radar_min_ratio,
                              record_path=str(tmp_path / 'radar.jsonl'))

    def _analyze_result(self):
        return {'current': 6.0, 'baseline': 3.0, 'ratio': 3.0, 'max_views': 0,
                'sentiment_extreme': 'none', 'social_spike_confirmed': False,
                'catalyst_present': False, 'summary': ''}

    def test_ratio_exactly_at_threshold_is_recorded_not_sent(self, tmp_path):
        alerter = self._alerter(tmp_path)
        with patch.object(alerter.twitter_sentiment, 'mention_velocity',
                          return_value=_velocity(2.0)), \
             patch.object(alerter.twitter_sentiment, 'analyze',
                          return_value=self._analyze_result()):
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', _volume_spike_no_event_fixture())
        assert alerter.notifier.messages == []
        record = json.loads((tmp_path / 'radar.jsonl').read_text().strip())
        assert record['alert_sent'] is False and record['ratio'] == 2.0

    def test_ratio_just_below_threshold_records_without_alert(self, tmp_path):
        alerter = self._alerter(tmp_path)
        with patch.object(alerter.twitter_sentiment, 'mention_velocity',
                          return_value=_velocity(1.9999)), \
             patch.object(alerter.twitter_sentiment, 'analyze') as mock_analyze:
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', _volume_spike_no_event_fixture())
        mock_analyze.assert_not_called()
        assert alerter.notifier.messages == []
        record = json.loads((tmp_path / 'radar.jsonl').read_text().strip())
        assert record['alert_sent'] is False

    def test_ratio_none_records_and_dedups_without_alert(self, tmp_path):
        # Documenta el comportamiento actual: ratio None (baseline insuficiente) NO se
        # trata como fallo reintentable, sino como resultado ya procesado de la vela.
        alerter = self._alerter(tmp_path)
        velocity = {'current': 3.0, 'baseline': None, 'ratio': None, 'max_views': 0,
                    'tweets': [{'text': 'x'}]}
        ohlcv = _volume_spike_no_event_fixture()
        with patch.object(alerter.twitter_sentiment, 'mention_velocity',
                          return_value=velocity) as mock_velocity, \
             patch.object(alerter.twitter_sentiment, 'analyze') as mock_analyze:
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
        assert mock_velocity.call_count == 1
        mock_analyze.assert_not_called()
        assert alerter.notifier.messages == []
        record = json.loads((tmp_path / 'radar.jsonl').read_text().strip())
        assert record['alert_sent'] is False and record['ratio'] is None

    def test_open_zero_candle_does_not_crash(self, tmp_path):
        closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
        closes += [100.5]
        lows += [99.5]
        highs += [100.8]
        volumes += [1000.0]
        ohlcv = _to_ohlcv_list(closes, lows, highs, volumes)
        ohlcv[-1][1] = 0.0  # open == 0
        alerter = self._alerter(tmp_path)
        with patch.object(alerter.twitter_sentiment, 'mention_velocity',
                          return_value=_velocity(3.0)), \
             patch.object(alerter.twitter_sentiment, 'analyze',
                          return_value=self._analyze_result()):
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', ohlcv)
        assert alerter.notifier.messages == []
        assert json.loads((tmp_path / 'radar.jsonl').read_text().strip())['candle_change_pct'] == 0.0

    def test_record_failure_does_not_raise(self, tmp_path):
        blocker = tmp_path / 'blocker'
        blocker.write_text('x')  # archivo, no directorio: makedirs va a fallar
        alerter = WyckoffAlerter(RecordingNotifier(), enabled=True,
                                 twitter_sentiment_enabled=True, rumor_radar_enabled=True,
                                 record_path=str(blocker / 'nested' / 'radar.jsonl'))
        with patch.object(alerter.twitter_sentiment, 'mention_velocity',
                          return_value=_velocity(3.0)), \
             patch.object(alerter.twitter_sentiment, 'analyze',
                          return_value=self._analyze_result()):
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', _volume_spike_no_event_fixture())
        assert alerter.notifier.messages == []


class FailingNotifier:
    """Notifier cuyo Telegram falla las primeras `fail_times` veces (send_direct_text devuelve False)."""
    def __init__(self, fail_times):
        self.fail_times = fail_times
        self.calls = 0
        self.messages = []

    def send_direct_text(self, message):
        self.calls += 1
        if self.calls <= self.fail_times:
            return False
        self.messages.append(message)
        return True


class TestTelegramFailureIsRetried:
    def test_undelivered_alert_is_retried_next_cycle_and_not_recorded_until_sent(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = FailingNotifier(fail_times=2)
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path))
        data = {'BTC/USDT': _liquid(_spring_fixture())}

        alerter.check_cycle('binance', data)   # falla
        assert not path.exists() or path.read_text().strip() == ''
        alerter.check_cycle('binance', data)   # falla
        alerter.check_cycle('binance', data)   # llega
        alerter.check_cycle('binance', data)   # ya enviada: no se repite

        assert len(notifier.messages) == 1
        assert notifier.calls == 3
        assert len(path.read_text().strip().splitlines()) == 1

    def test_gives_up_after_the_limit_instead_of_retrying_forever(self):
        from analysis.wyckoff_alerts import SEND_MAX_FAILURES
        notifier = FailingNotifier(fail_times=10_000)
        alerter = WyckoffAlerter(notifier, enabled=True)
        data = {'BTC/USDT': _liquid(_spring_fixture())}

        for _ in range(SEND_MAX_FAILURES + 5):
            alerter.check_cycle('binance', data)

        assert notifier.calls == SEND_MAX_FAILURES



class TestClockAndCandleLabel:
    def test_when_shows_utc_and_operator_local_time(self):
        from analysis.alert_text import when
        # vie 2026-01-09 20:00 UTC = 17:00 Santiago (verano, UTC-3)
        assert when(pd.Timestamp('2026-01-09T20:00:00Z'), 'America/Santiago') == 'vie 20:00 UTC (17:00 Santiago)'

    def test_when_shows_the_local_weekday_only_when_it_changes(self):
        from analysis.alert_text import when
        # sab 00:00 UTC = vie 20:00 Santiago (invierno, UTC-4)
        assert when(pd.Timestamp('2026-07-11T00:00:00Z'), 'America/Santiago') == 'sáb 00:00 UTC (vie 20:00 Santiago)'

    def test_when_utc_only_without_timezone_and_accepts_naive(self):
        from analysis.alert_text import when
        assert when(pd.Timestamp('2026-01-09T20:00:00Z'), 'UTC') == 'vie 20:00 UTC'
        assert when(pd.Timestamp('2026-01-09T20:00:00'), 'UTC') == 'vie 20:00 UTC'

    def test_alert_message_includes_the_closing_time(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, timezone_str='America/Santiago')
        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())
        assert 'La vela de 4 h cerró el' in notifier.messages[0]
        assert 'Santiago' in notifier.messages[0]

    def test_clock_offset_from_exchange_is_applied_to_now(self):
        alerter = WyckoffAlerter(RecordingNotifier(), enabled=True, clock_offset_fn=lambda ex: 3600.0)
        alerter._current_exchange = 'binance'
        delta = (alerter._now_utc() - datetime.now(timezone.utc)).total_seconds()
        assert 3595 < delta < 3605

    def test_no_correction_without_exchange_or_when_offset_fails(self):
        def boom(exchange):
            raise RuntimeError('sin red')
        for alerter in (WyckoffAlerter(RecordingNotifier(), enabled=True, clock_offset_fn=lambda ex: 3600.0),
                        WyckoffAlerter(RecordingNotifier(), enabled=True, clock_offset_fn=boom)):
            alerter._current_exchange = None if alerter._clock_offset_fn is not boom else 'binance'
            assert abs((alerter._now_utc() - datetime.now(timezone.utc)).total_seconds()) < 5


class TestLiquidityNotice:
    def test_low_liquidity_shows_a_warning_and_high_liquidity_does_not(self):
        from analysis.alert_text import AlertItem, liquidity_note
        def item(v):
            return AlertItem(pair='X/USDT', direction='hot', price=1.0, volume_x=3.0, candle_open=pd.Timestamp('2026-01-09T16:00:00Z'), dvol24h=v)
        assert 'Moneda poco líquida' in liquidity_note([item(5_000_000)])
        assert '5.0 millones' in liquidity_note([item(5_000_000)])
        assert liquidity_note([item(20_000_000)]) == ''
        assert liquidity_note([item(500_000_000)]) == ''
        assert liquidity_note([item(None)]) == ''

    def test_dollar_volume_is_the_sum_of_the_last_six_candles(self):
        df = pd.DataFrame({'volume': [1.0] * 4 + [10.0] * 6, 'close': [1.0] * 4 + [2.0] * 6})
        assert WyckoffAlerter._dollar_volume_24h(df) == pytest.approx(120.0)

    def test_dollar_volume_needs_six_candles(self):
        assert WyckoffAlerter._dollar_volume_24h(pd.DataFrame({'volume': [1.0] * 5, 'close': [1.0] * 5})) is None

    def test_alert_message_and_record_carry_the_liquidity(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path))
        alerter.check_and_alert('binance', 'BTC/USDT', '4h', _spring_fixture())  # volumenes de juguete: liquidez muy baja
        assert 'Moneda poco líquida' in notifier.messages[0]
        assert json.loads(path.read_text().strip())['dvol24h_usd'] is not None


class TestWideClusterFraction:
    def test_threshold_is_twenty_percent_of_the_watched_pairs(self):
        from analysis.alert_text import strength_block
        wide = strength_block(6, 30)     # 20%
        narrow = strength_block(5, 30)   # 16.7%
        assert 'pánico generalizado' in wide.lower() and '6 de 30 monedas (20%)' in wide
        assert 'Caso poco extendido' in narrow and 'pánico generalizado' not in narrow.lower()

    def test_same_count_means_different_things_for_different_universes(self):
        from analysis.alert_text import strength_block
        assert 'pánico generalizado' in strength_block(6, 20).lower()
        assert 'Caso poco extendido' in strength_block(6, 49)

    def test_unknown_universe_or_count_gives_no_strength_block(self):
        from analysis.alert_text import strength_block
        assert strength_block(None, 30) == '' and strength_block(6, None) == ''

    def test_watched_pairs_are_recorded(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        alerter = WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=str(path))
        pairs = {'BTC/USDT': _liquid(_spring_fixture()), 'Q/USDT': _liquid(_no_event_fixture())}
        alerter.check_cycle('binance', pairs)
        assert json.loads(path.read_text().strip())['watched_pairs'] == 2


class TestHonestWideClusterMessage:
    def test_wide_cluster_states_the_daily_distribution_not_a_sure_return(self):
        from analysis.alert_text import strength_block
        text = strength_block(8, 30)
        assert '+0.6%' in text and '4 a 5 de cada 10 días terminaron en pérdida' in text
        assert '−9.5% a +12%' in text and 'no es seguro' in text

    def test_narrow_cluster_message_has_no_daily_distribution(self):
        from analysis.alert_text import strength_block
        text = strength_block(2, 30)
        assert 'Caso poco extendido' in text and '+0.6%' not in text


class TestGroupedDelivery:
    """Las señales de una misma vela salen juntas en UN mensaje; el registro y la deduplicación siguen siendo por moneda."""

    def _pairs(self, n=4, quiet=6):
        pairs = {f'C{i}/USDT': _liquid(_spring_fixture()) for i in range(n)}
        pairs.update({f'Q{i}/USDT': _liquid(_no_event_fixture()) for i in range(quiet)})
        return pairs

    def test_one_message_and_one_record_per_coin(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path))
        alerter.check_cycle('binance', self._pairs())

        assert len(notifier.messages) == 1
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert sorted(r['pair'] for r in records) == ['C0/USDT', 'C1/USDT', 'C2/USDT', 'C3/USDT']
        assert all(r['concurrent_pairs'] == 4 and r['watched_pairs'] == 10 for r in records)

    def test_group_is_not_repeated_on_the_next_cycle(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        pairs = self._pairs()
        alerter.check_cycle('binance', pairs)
        alerter.check_cycle('binance', pairs)
        assert len(notifier.messages) == 1

    def test_failed_group_is_retried_whole_and_recorded_only_when_delivered(self, tmp_path):
        path = tmp_path / 'record.jsonl'
        notifier = FailingNotifier(fail_times=1)
        alerter = WyckoffAlerter(notifier, enabled=True, record_path=str(path))
        pairs = self._pairs()

        alerter.check_cycle('binance', pairs)     # falla: nada se marca como enviado
        assert not path.exists() or path.read_text().strip() == ''
        alerter.check_cycle('binance', pairs)     # llega el grupo completo
        alerter.check_cycle('binance', pairs)     # no se repite

        assert notifier.calls == 2 and len(notifier.messages) == 1
        assert len(path.read_text().strip().splitlines()) == 4

    def test_twitter_is_only_queried_for_single_alerts(self):
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True, twitter_sentiment_enabled=True)
        with patch.object(alerter.twitter_sentiment, 'analyze', return_value=None) as analyze:
            alerter.check_cycle('binance', self._pairs(n=3))
            assert analyze.call_count == 0
            alerter2 = WyckoffAlerter(RecordingNotifier(), enabled=True, twitter_sentiment_enabled=True)
        with patch.object(alerter2.twitter_sentiment, 'analyze', return_value=None) as analyze2:
            alerter2.check_cycle('binance', self._pairs(n=1, quiet=0))
            assert analyze2.call_count == 1

    def test_a_group_can_mix_directions_as_separate_messages(self):
        closes, lows, highs, volumes = _flat_range_df(n_flat=FIXTURE_FLAT_CANDLES)
        closes += [103.0, 100.0]
        lows += [102.0, 99.0]
        highs += [105.0, 102.0]
        volumes += [1000.0, 100.0]
        upthrust = _to_ohlcv_list(closes, lows, highs, volumes)
        notifier = RecordingNotifier()
        alerter = WyckoffAlerter(notifier, enabled=True)
        alerter.check_cycle('binance', {'A/USDT': _liquid(_spring_fixture()), 'B/USDT': _liquid(upthrust)})
        assert len(notifier.messages) == 1
        assert notifier.messages[0].startswith('🟢')


class TestRecordClock:
    def test_records_carry_exchange_time_and_clock_skew(self, tmp_path):
        import json
        path = tmp_path / 'r.jsonl'
        alerter = WyckoffAlerter(RecordingNotifier(), enabled=True, record_path=str(path))
        alerter._record({'type': 'radar'})
        row = json.loads(path.read_text().splitlines()[0])
        assert 'exchange_time' in row and 'clock_skew_s' in row and abs(row['clock_skew_s']) < 5


class FlakyNotifier:
    def __init__(self, results):
        self.results, self.calls = list(results), 0

    def send_direct_text(self, message):
        self.calls += 1
        return self.results.pop(0) if self.results else True


class TestRadarDelivery:
    def _alerter(self, tmp_path, notifier):
        return WyckoffAlerter(notifier, enabled=True, twitter_sentiment_enabled=True, rumor_radar_enabled=True,
                              record_path=str(tmp_path / 'radar.jsonl'))

    def _run(self, alerter):
        with patch.object(alerter.twitter_sentiment, 'mention_velocity', return_value=_velocity(3.0)),              patch.object(alerter.twitter_sentiment, 'analyze', return_value={
                 'current': 9.0, 'baseline': 3.0, 'ratio': 3.0, 'max_views': 0, 'sentiment_extreme': 'euphoria',
                 'social_spike_confirmed': False, 'catalyst_present': True, 'summary': 'x'}):
            alerter.check_and_alert('binance', 'SOL/USDT', '4h', _volume_spike_no_event_fixture())

    def test_radar_never_calls_telegram_and_is_recorded_once(self, tmp_path):
        notifier = FlakyNotifier([False, True])
        alerter = self._alerter(tmp_path, notifier)
        self._run(alerter)
        self._run(alerter)
        assert notifier.calls == 0
        lines = (tmp_path / 'radar.jsonl').read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])['alert_sent'] is False

    def test_radar_error_does_not_break_the_pair(self, tmp_path):
        alerter = self._alerter(tmp_path, RecordingNotifier())
        with patch.object(alerter, '_check_rumor_radar', side_effect=RuntimeError('boom')):
            assert alerter._collect_pair('binance', 'SOL/USDT', '4h', _volume_spike_no_event_fixture()) == []
