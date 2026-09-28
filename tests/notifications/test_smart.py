"""
Tests para SmartNotificationManager (specs/004-core-pipeline-test-coverage/).
"""
import pytest

from notifications.smart import SmartNotificationManager


def _zero_delay_config(**overrides):
    config = {'delay_after_summary': 0, 'delay_between_details': 0}
    config.update(overrides)
    return config


def _signal(market='BTC/USDT', quality='C', score=50.0, status='hot', indicator='rsi'):
    return {'market': market, 'quality': quality, 'score': score,
            'status': status, 'indicator': indicator, 'values': {}}


class TestBuildSummaryMessageHeader:
    def test_all_c_and_bearish_btc_uses_market_scan_header(self):
        manager = SmartNotificationManager(_zero_delay_config())
        manager.set_market_context('bearish', -3.2, 'risk_off')
        manager.add_signal(_signal(quality='C'))

        message = manager.build_summary_message()

        assert 'MARKET SCAN' in message
        assert 'Sin señales operables' in message

    def test_actionable_signal_uses_operable_header(self):
        manager = SmartNotificationManager(_zero_delay_config())
        manager.set_market_context('bullish', 2.0, 'risk_on')
        manager.add_signal(_signal(market='SUI/USDT', quality='A', score=80))
        manager.add_signal(_signal(market='ENA/USDT', quality='C', score=20))

        message = manager.build_summary_message()

        assert 'SEÑALES OPERABLES' in message
        assert 'watchlist' in message

    def test_empty_signals_returns_empty_string(self):
        manager = SmartNotificationManager(_zero_delay_config())

        assert manager.build_summary_message() == ""


class TestMaxCSignalsTruncation:
    def test_c_signals_beyond_max_are_truncated(self):
        manager = SmartNotificationManager(_zero_delay_config(max_c_signals=2))
        for i in range(5):
            manager.add_signal(_signal(market=f'PAIR{i}/USDT', quality='C', score=i))

        message = manager.build_summary_message()

        assert 'más en watchlist' in message


class TestFinalizeCycleGating:
    def test_only_high_quality_signals_get_detail_and_chart(self):
        config = _zero_delay_config(detail_min_quality='A', chart_min_quality='A')
        manager = SmartNotificationManager(config)
        manager.add_signal(_signal(market='LOW/USDT', quality='C', score=10))
        manager.add_signal(_signal(market='HIGH/USDT', quality='A', score=90), chart_file='chart.png')

        sent_texts = []
        sent_charts = []

        stats = manager.finalize_cycle(
            send_func=lambda payload: sent_texts.append(payload),
            send_chart_func=lambda chart_file, payload: sent_charts.append((chart_file, payload)),
        )

        assert stats['details'] == 1
        assert stats['charts'] == 1
        assert len(sent_charts) == 1
        assert sent_charts[0][1]['market'] == 'HIGH/USDT'

    def test_high_quality_without_chart_file_sends_text_only(self):
        config = _zero_delay_config(detail_min_quality='A', chart_min_quality='A')
        manager = SmartNotificationManager(config)
        manager.add_signal(_signal(market='HIGH/USDT', quality='A', score=90), chart_file=None)

        sent_texts = []

        stats = manager.finalize_cycle(
            send_func=lambda payload: sent_texts.append(payload),
            send_chart_func=lambda chart_file, payload: pytest.fail('should not send chart'),
        )

        assert stats['details'] == 1
        assert stats['charts'] == 0
        assert len(sent_texts) == 2  # summary text + detail text

    def test_finalize_cycle_resets_state(self):
        config = _zero_delay_config()
        manager = SmartNotificationManager(config)
        manager.set_market_context('bullish', 1.0, 'risk_on')
        manager.add_signal(_signal())

        manager.finalize_cycle(send_func=lambda payload: None, send_chart_func=lambda c, p: None)

        assert manager.summaries == []
        assert manager.current_cycle == []
        assert manager.btc_context == {}
