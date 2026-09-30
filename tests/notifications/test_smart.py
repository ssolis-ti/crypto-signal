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

        assert 'Radar RSI/MACD' in message
        assert 'no predijeron el precio' in message
        assert 'baja 3.2%' in message and 'mercado a la baja' in message
        assert '⭐' not in message, 'sin estrellas: el puntaje no predice nada'

    def test_actionable_signal_uses_operable_header(self):
        manager = SmartNotificationManager(_zero_delay_config())
        manager.set_market_context('bullish', 2.0, 'risk_on')
        manager.add_signal(_signal(market='SUI/USDT', quality='A', score=80))
        manager.add_signal(_signal(market='ENA/USDT', quality='C', score=20))

        message = manager.build_summary_message()

        assert 'Radar RSI/MACD' in message
        assert 'SUI/USDT' in message and 'ENA/USDT' in message
        assert 'OPORTUNIDAD DE COMPRA' in message  # remite a la señal principal
        assert 'operable' not in message.lower() and 'sólida' not in message and 'fuerte' not in message

    def test_empty_signals_returns_empty_string(self):
        manager = SmartNotificationManager(_zero_delay_config())

        assert manager.build_summary_message() == ""


class TestSummaryPlainLanguage:
    def test_groups_by_direction_and_describes_rsi_in_words(self):
        manager = SmartNotificationManager(_zero_delay_config())
        manager.add_signal({'market': 'SUI/USDT', 'quality': 'A', 'score': 80, 'status': 'hot', 'indicator': 'rsi', 'values': {'rsi': '25.4'}})
        manager.add_signal({'market': 'DOGE/USDT', 'quality': 'B', 'score': 60, 'status': 'cold', 'indicator': 'rsi', 'values': {'rsi': '72'}})

        message = manager.build_summary_message()

        assert '🟢 <b>Alcistas</b>' in message and 'SUI/USDT — RSI 25 (muy bajo)' in message
        assert '🔴 <b>Bajistas</b>' in message and 'DOGE/USDT — RSI 72 (muy alto)' in message


class TestMaxCSignalsTruncation:
    def test_c_signals_beyond_max_are_truncated(self):
        manager = SmartNotificationManager(_zero_delay_config(max_c_signals=2))
        for i in range(5):
            manager.add_signal(_signal(market=f'PAIR{i}/USDT', quality='C', score=i))

        message = manager.build_summary_message()

        assert 'y 3 más que no se muestran' in message


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


class TestMissingDataDefaults:
    """Datos faltantes no deben romper el resumen ni ocultar señales."""

    def test_signal_with_no_fields_still_appears_as_unknown(self):
        manager = SmartNotificationManager(_zero_delay_config())
        manager.add_signal({})

        message = manager.build_summary_message()

        assert 'UNKNOWN' in message

    def test_non_dict_values_does_not_crash(self):
        manager = SmartNotificationManager(_zero_delay_config())
        manager.add_signal({'market': 'BTC/USDT', 'quality': 'C', 'score': 10,
                            'status': 'hot', 'indicator': 'rsi', 'values': 'no-dict'})

        assert 'BTC/USDT' in manager.build_summary_message()

    def test_non_numeric_rsi_falls_back_to_indicator_name(self):
        manager = SmartNotificationManager(_zero_delay_config())
        manager.add_signal({'market': 'BTC/USDT', 'quality': 'C', 'score': 10,
                            'status': 'hot', 'indicator': 'rsi', 'values': {'rsi': 'abc'}})

        message = manager.build_summary_message()
        assert 'RSI 0' not in message
        assert 'rsi' in message

    def test_get_cycle_stats_with_no_summaries(self):
        manager = SmartNotificationManager(_zero_delay_config())
        assert manager.get_cycle_stats() == {'count': 0}
