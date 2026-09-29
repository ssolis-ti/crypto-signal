"""
TelegramNotifier: RetryAfter (flood control) y HTML invalido no deben perder la alerta.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.error import BadRequest, RetryAfter

from notifiers.telegram_client import TelegramNotifier


def _notifier_with_bot(send_side_effect):
    bot = MagicMock()
    bot.send_message = AsyncMock(side_effect=send_side_effect)
    notifier = TelegramNotifier(token='t', chat_id='c', parse_mode='HTML')
    return notifier, bot


def test_retry_after_waits_and_resends():
    notifier, bot = _notifier_with_bot([RetryAfter(2), None])
    with patch('notifiers.telegram_client.Bot', return_value=bot), \
         patch('notifiers.telegram_client.asyncio.sleep', new=AsyncMock()) as sleep:
        notifier.notify('hola')

    assert bot.send_message.await_count == 2
    sleep.assert_awaited_once()
    assert sleep.await_args.args[0] >= 2


def test_invalid_html_is_resent_as_plain_text():
    notifier, bot = _notifier_with_bot([BadRequest("Can't parse entities: unsupported start tag"), None])
    with patch('notifiers.telegram_client.Bot', return_value=bot):
        notifier.notify('<b>roto')

    assert bot.send_message.await_count == 2
    assert bot.send_message.await_args_list[0].kwargs['parse_mode'] == 'HTML'
    assert bot.send_message.await_args_list[1].kwargs['parse_mode'] is None


def test_other_bad_request_still_raises():
    notifier, bot = _notifier_with_bot([BadRequest('chat not found')])
    with patch('notifiers.telegram_client.Bot', return_value=bot):
        with pytest.raises(BadRequest):
            notifier.notify('hola')


# ─────────────────────────────────────────────────────────────────────────────
# QA adversarial: troceo de mensajes > 4096 sin perder contenido ni dejar
# chunks vacios (una alerta perdida es peor que una fea).
# ─────────────────────────────────────────────────────────────────────────────

class TestChunkMessage:
    def _notifier(self):
        return TelegramNotifier(token='t', chat_id='c', parse_mode='HTML')

    def test_short_message_is_a_single_chunk(self):
        assert self._notifier().chunk_message('hola', 4096) == ['hola']

    def test_message_exactly_at_limit_is_a_single_chunk(self):
        message = 'a' * 4096
        assert self._notifier().chunk_message(message, 4096) == [message]

    def test_multiline_over_limit_loses_no_content(self):
        message = '\n'.join(f'linea-{i:04d}' for i in range(1000))
        chunks = self._notifier().chunk_message(message, 4096)

        assert ''.join(chunks) == message
        assert len(chunks) > 1
        assert all(0 < len(chunk) <= 4096 for chunk in chunks)

    def test_single_long_line_is_split_not_dropped(self):
        message = 'A' * 10000
        chunks = self._notifier().chunk_message(message, 4096)

        assert ''.join(chunks) == message
        assert all(len(chunk) <= 4096 for chunk in chunks)
        assert all(chunk for chunk in chunks)

    def test_no_empty_chunk_when_a_line_exceeds_the_limit(self):
        message = 'intro\n' + 'B' * 9000 + '\nfin'
        chunks = self._notifier().chunk_message(message, 4096)

        assert ''.join(chunks) == message
        assert all(chunk for chunk in chunks)

    def test_lines_are_not_cut_across_chunks(self):
        lines = [f'<b>fila {i}</b>' for i in range(400)]
        message = '\n'.join(lines)
        chunks = self._notifier().chunk_message(message, 500)

        for line in lines:
            assert any(line in chunk for chunk in chunks)

    def test_notify_sends_all_chunks_without_loss(self):
        bot = MagicMock()
        bot.send_message = AsyncMock(return_value=None)
        notifier = TelegramNotifier(token='t', chat_id='c', parse_mode='HTML')
        message = '\n'.join(f'linea-{i:04d}' for i in range(1000))

        with patch('notifiers.telegram_client.Bot', return_value=bot):
            notifier.notify(message)

        sent = [call.kwargs['text'] for call in bot.send_message.await_args_list]
        assert ''.join(sent) == message
        assert all(0 < len(text) <= 4096 for text in sent)
