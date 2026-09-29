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
