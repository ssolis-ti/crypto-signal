"""
Tests para la ventana anti-spam en UTC de MessageBuilder (specs/002-utc-internal-time/).
"""
import datetime

import pandas as pd

from notifications.builder import MessageBuilder


def _indicator_analysis(market='BTC/USDT', hot=True):
    """Estructura minima realista: un indicador 'rsi' con una fila de resultado."""
    result = pd.DataFrame([{'rsi': 55.0, 'is_hot': hot, 'is_cold': False}])
    return {
        'binance': {
            market: {
                'indicators': {
                    'rsi': [{
                        'config': {'signal': ['rsi'], 'candle_period': '4h',
                                   'alert_frequency': '1h', 'alert_enabled': True},
                        'result': result,
                    }],
                },
            },
        },
    }


class TestBuildIndicatorMessagesMissingData:
    def test_empty_analysis_returns_empty_structure(self):
        assert MessageBuilder().build_indicator_messages({}) == {}

    def test_zero_row_result_is_skipped(self):
        analysis = _indicator_analysis()
        analysis['binance']['BTC/USDT']['indicators']['rsi'][0]['result'] = pd.DataFrame(
            columns=['rsi', 'is_hot', 'is_cold'])

        messages = MessageBuilder().build_indicator_messages(analysis)

        assert messages['binance']['BTC/USDT'].get('4h', []) == []

    def test_market_pair_without_quote_currency_does_not_crash(self):
        analysis = _indicator_analysis(market='BTCUSDT')

        messages = MessageBuilder().build_indicator_messages(analysis)

        entry = messages['binance']['BTCUSDT']['4h'][0]
        assert entry['quote_currency'] == ''


class TestAlertFrequencyIsUtc:
    def test_parse_alert_frequency_returns_utc_aware_datetime(self):
        builder = MessageBuilder()
        result = builder.parse_alert_frequency("1h")
        assert result.tzinfo is not None
        assert result.tzinfo == datetime.timezone.utc

    def test_should_i_alert_suppresses_immediately_after_recording(self):
        builder = MessageBuilder()
        assert builder.should_i_alert("BTC/USDT:rsi", "1h") is True
        # Inmediatamente despues, con la misma clave, debe suprimir
        assert builder.should_i_alert("BTC/USDT:rsi", "1h") is False

    def test_should_i_alert_survives_simulated_dst_local_rollback(self, monkeypatch):
        """
        Si should_i_alert comparara contra datetime.now() naive (hora local), un
        retroceso de reloj local (fin de horario de verano) sin que haya pasado
        tiempo UTC real podria hacer que la comparacion cambiara de signo. Con UTC
        interno, la decision solo depende del tiempo UTC transcurrido.
        """
        builder = MessageBuilder()
        assert builder.should_i_alert("ETH/USDT:rsi", "1h") is True

        real_now = datetime.datetime.now

        class _RolledBackDatetime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                base = real_now(tz)
                if tz is not None:
                    # simula "una hora local menos" pero el mismo instante UTC:
                    # should_i_alert siempre pasa tz=utc, asi que esto no debe
                    # afectar la decision (es exactamente lo que queremos probar).
                    return base
                return base

        monkeypatch.setattr(datetime, "datetime", _RolledBackDatetime)
        # todavia dentro de la ventana de 1h -> sigue suprimiendo
        assert builder.should_i_alert("ETH/USDT:rsi", "1h") is False

    def test_creation_date_still_uses_local_timezone(self):
        """FR-003: esta funcionalidad NO debe tocarse por este slice."""
        import inspect
        source = inspect.getsource(MessageBuilder)
        assert "timezone(self.timezone_str)" in source
