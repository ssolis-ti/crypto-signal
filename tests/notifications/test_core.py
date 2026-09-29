"""
Tests para Notifier (specs/005-notifier-core-coverage/).

Los clientes reales (TelegramNotifier/WebhookNotifier/StdoutNotifier) se construyen de verdad
(sus __init__ no hacen I/O), y solo se reemplazan sus metodos de envio por stubs que registran
las llamadas, para no depender de red/Telegram/webhook reales.
"""
import pytest

from notifications.core import Notifier
from notifiers.telegram_client import TelegramNotifier
from notifiers.webhook_client import WebhookNotifier


TEMPLATE = "{{ market }} {{ status }}"


def _notifier_config(telegram=False, webhook=False, stdout=False, telegram_complete=True):
    config = {}
    if telegram:
        config['telegram'] = {
            'required': {
                'token': 'fake-token' if telegram_complete else '',
                'chat_id': '12345',
            },
            'optional': {'parse_mode': 'HTML', 'template': TEMPLATE},
        }
    if webhook:
        config['webhook'] = {
            'required': {'url': 'http://example.invalid/hook'},
            'optional': {'username': '', 'password': ''},
        }
    if stdout:
        config['stdout'] = {}
    return config


def _make_notifier(notifier_config):
    return Notifier(
        notifier_config=notifier_config,
        indicator_config={},
        conditional_config=False,
        market_data={},
    )


class RecordingClient:
    """Stub generico que registra cada llamada a sus metodos."""

    def __init__(self):
        self.calls = []

    def notify(self, *args, **kwargs):
        self.calls.append(('notify', args, kwargs))

    def send_messages(self, messages):
        self.calls.append(('send_messages', messages))

    def send_chart_messages(self, chart_file, messages):
        self.calls.append(('send_chart_messages', chart_file, messages))


class TestInitializeNotifiers:
    def test_telegram_only_valid_config_creates_client(self):
        notifier = _make_notifier(_notifier_config(telegram=True))

        assert len(notifier.telegram_clients) == 1
        assert notifier.telegram_configured is True
        assert notifier.webhook_clients == {}
        assert notifier.stdout_clients == {}

    def test_telegram_missing_required_field_skips_client(self):
        notifier = _make_notifier(_notifier_config(telegram=True, telegram_complete=False))

        assert notifier.telegram_clients == {}
        assert not hasattr(notifier, 'telegram_configured')

    def test_all_three_channels_configured(self):
        notifier = _make_notifier(_notifier_config(telegram=True, webhook=True, stdout=True))

        assert len(notifier.telegram_clients) == 1
        assert len(notifier.webhook_clients) == 1
        assert len(notifier.stdout_clients) == 1
        assert notifier.telegram_configured is True
        assert notifier.webhook_configured is True
        assert notifier.stdout_configured is True

    def test_empty_config_creates_no_clients(self):
        notifier = _make_notifier({})

        assert notifier.telegram_clients == {}
        assert notifier.webhook_clients == {}
        assert notifier.stdout_clients == {}
        assert not hasattr(notifier, 'telegram_configured')
        assert not hasattr(notifier, 'webhook_configured')
        assert not hasattr(notifier, 'stdout_configured')


class TestNotifyWebhook:
    def test_forwards_none_chart_file(self):
        notifier = _make_notifier(_notifier_config(webhook=True))
        stub = RecordingClient()
        notifier.webhook_clients['webhook'] = stub

        notifier.notify_webhook(['msg1', 'msg2'], None)

        assert stub.calls == [
            ('notify', ('msg1', None), {}),
            ('notify', ('msg2', None), {}),
        ]

    def test_forwards_real_chart_file_path(self):
        notifier = _make_notifier(_notifier_config(webhook=True))
        stub = RecordingClient()
        notifier.webhook_clients['webhook'] = stub

        notifier.notify_webhook(['msg1'], './charts/btc_usdt_4h.png')

        assert stub.calls == [('notify', ('msg1', './charts/btc_usdt_4h.png'), {})]

    def test_matches_real_webhooknotifier_signature(self):
        """Regression guard: WebhookNotifier.notify requires (messages, chart_file)."""
        notifier = _make_notifier(_notifier_config(webhook=True))
        real_client = notifier.webhook_clients['webhook']
        assert isinstance(real_client, WebhookNotifier)
        calls = []
        real_client.notify = lambda messages, chart_file: calls.append((messages, chart_file))

        notifier.notify_webhook(['msg1'], None)

        assert calls == [('msg1', None)]


class TestNotifyTelegram:
    def test_chart_send_failure_falls_back_to_text(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()

        def failing_chart(chart_file, messages):
            raise RuntimeError('network down')

        stub.send_chart_messages = failing_chart
        notifier.telegram_clients['telegram'] = stub

        notifier.notify_telegram([{'market': 'BTC/USDT', 'status': 'hot'}], 'chart.png')

        assert stub.calls == [('send_messages', ['BTC/USDT hot'])]


class TestSendTelegramQueued:
    def test_update_prefix_added_when_is_update_true(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()
        notifier.telegram_clients['telegram'] = stub

        notifier._send_telegram_queued({'market': 'BTC/USDT', 'status': 'hot'}, None, True)

        assert stub.calls == [('send_messages', ['🔄 UPDATE\nBTC/USDT hot'])]

    def test_no_prefix_when_is_update_false(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()
        notifier.telegram_clients['telegram'] = stub

        notifier._send_telegram_queued({'market': 'BTC/USDT', 'status': 'hot'}, None, False)

        assert stub.calls == [('send_messages', ['BTC/USDT hot'])]

    def test_chart_file_present_uses_send_chart_messages(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()
        notifier.telegram_clients['telegram'] = stub

        notifier._send_telegram_queued({'market': 'BTC/USDT', 'status': 'hot'}, 'c.png', False)

        assert stub.calls == [('send_chart_messages', 'c.png', ['BTC/USDT hot'])]


class TestSendSmartText:
    def test_string_message_sent_without_template_rendering(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()
        notifier.telegram_clients['telegram'] = stub

        notifier._send_smart_text("preformatted summary")

        assert stub.calls == [('send_messages', ['preformatted summary'])]

    def test_dict_message_is_rendered_via_template(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()
        notifier.telegram_clients['telegram'] = stub

        notifier._send_smart_text({'market': 'ETH/USDT', 'status': 'cold'})

        assert stub.calls == [('send_messages', ['ETH/USDT cold'])]


class TestSendSmartChart:
    def test_chart_and_message_sent_together(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()
        notifier.telegram_clients['telegram'] = stub

        notifier._send_smart_chart('chart.png', {'market': 'BTC/USDT', 'status': 'hot'})

        assert stub.calls == [('send_chart_messages', 'chart.png', ['BTC/USDT hot'])]

    def test_chart_failure_falls_back_to_text(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()

        def failing_chart(chart_file, messages):
            raise RuntimeError('bad file')

        stub.send_chart_messages = failing_chart
        notifier.telegram_clients['telegram'] = stub

        notifier._send_smart_chart('chart.png', {'market': 'BTC/USDT', 'status': 'hot'})

        assert stub.calls == [('send_messages', ['BTC/USDT hot'])]

    def test_chart_and_text_fallback_both_fail_is_contained(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        stub = RecordingClient()

        def failing(*args, **kwargs):
            raise RuntimeError('down')

        stub.send_chart_messages = failing
        stub.send_messages = failing
        notifier.telegram_clients['telegram'] = stub

        # Must not raise -- both failures are caught and logged.
        notifier._send_smart_chart('chart.png', {'market': 'BTC/USDT', 'status': 'hot'})


class TestSendDirectText:
    """
    La alerta directa (Wyckoff/radar, specs/023) se manda a cada cliente Telegram
    configurado; el fallo de uno no debe impedir la entrega a los demas.
    """

    def _two_telegram_notifier(self):
        config = {}
        for name in ('telegram_a', 'telegram_b'):
            config[name] = {
                'required': {'token': 'fake-token', 'chat_id': '12345'},
                'optional': {'parse_mode': 'HTML', 'template': TEMPLATE},
            }
        return _make_notifier(config)

    def test_no_clients_is_a_no_op(self):
        notifier = _make_notifier({})
        notifier.send_direct_text('ALERTA')  # no debe lanzar

    def test_failing_first_client_does_not_block_the_second(self):
        notifier = self._two_telegram_notifier()
        received = []

        def boom(messages):
            raise RuntimeError('network down')

        notifier.telegram_clients['telegram_a'].send_messages = boom
        notifier.telegram_clients['telegram_b'].send_messages = (
            lambda messages: received.append(messages))

        notifier.send_direct_text('ALERTA')

        assert received == [['ALERTA']]

    def test_all_clients_failing_is_contained(self):
        notifier = self._two_telegram_notifier()

        def boom(messages):
            raise RuntimeError('network down')

        for client in notifier.telegram_clients.values():
            client.send_messages = boom

        notifier.send_direct_text('ALERTA')  # no debe propagar la excepcion


class TestNotifyAll:
    def _messages_by_pair(self, msgs):
        return {'binance': {'BTC/USDT': {'4h': msgs}}}

    def test_stdout_only_routes_to_stdout(self):
        notifier = _make_notifier(_notifier_config(stdout=True))
        notifier.builder.build_indicator_messages = lambda *a, **kw: self._messages_by_pair(
            [{'market': 'BTC/USDT', 'status': 'hot'}]
        )
        stub = RecordingClient()
        notifier.stdout_clients['stdout'] = stub

        notifier.notify_all(new_analysis={})

        assert stub.calls == [('notify', ({'market': 'BTC/USDT', 'status': 'hot'},), {})]

    def test_telegram_only_routes_through_smart_manager(self):
        notifier = _make_notifier(_notifier_config(telegram=True))
        notifier.builder.build_indicator_messages = lambda *a, **kw: self._messages_by_pair(
            [{'market': 'BTC/USDT', 'status': 'hot', 'quality': 'A', 'score': 90}]
        )
        stub = RecordingClient()
        notifier.telegram_clients['telegram'] = stub

        notifier.notify_all(new_analysis={})

        # summary + detail (quality A) both go through _send_smart_text -> stub.send_messages
        sent_kinds = [call[0] for call in stub.calls]
        assert 'send_messages' in sent_kinds

    def test_enable_charts_false_skips_create_charts(self):
        notifier = _make_notifier(_notifier_config(stdout=True))
        notifier.builder.build_indicator_messages = lambda *a, **kw: self._messages_by_pair([])
        notifier.enable_charts = False
        called = []
        notifier.create_charts = lambda messages: called.append(messages)

        notifier.notify_all(new_analysis={})

        assert called == []
