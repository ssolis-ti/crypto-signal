"""
Cliente Telegram Modernizado (v21+ Async)
Compatible con Python 3.12+
"""

import asyncio
import structlog
from telegram import Bot
from telegram.error import BadRequest, NetworkError, RetryAfter, TimedOut
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential
)

from notifiers.utils import NotifierUtils

# Configuración
__connect_timeout__ = 40
__read_timeout__ = 40
__stop_after_attempt__ = 3
__max_message_size__ = 4096


class TelegramNotifier(NotifierUtils):
    """
    Cliente Telegram moderno usando API v21+ (async).
    """

    def __init__(self, token: str, chat_id: str, parse_mode: str = "HTML"):
        """
        Inicializa el notificador de Telegram.

        Args:
            token: Token del bot de Telegram.
            chat_id: ID del chat destino.
            parse_mode: Modo de parseo (HTML, Markdown, MarkdownV2).
        """
        self.logger = structlog.get_logger()
        self.token = token
        self.chat_id = chat_id
        self.parse_mode = parse_mode

    def notify(self, message: str):
        """
        Envía un mensaje de texto (wrapper síncrono para compatibilidad).
        """
        asyncio.run(self._async_notify(message))

    @retry(
        # BadRequest hereda de NetworkError en python-telegram-bot, pero reintentarlo no sirve:
        # el mensaje sera rechazado igual. Se maneja aparte dentro de _async_notify.
        retry=retry_if_exception(lambda e: isinstance(e, (TimedOut, NetworkError))
                                 and not isinstance(e, BadRequest)),
        stop=stop_after_attempt(__stop_after_attempt__),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _async_notify(self, message: str):
        """
        Envía un mensaje de texto de forma asíncrona.
        """
        bot = Bot(token=self.token)
        message_chunks = self.chunk_message(
            message=message, max_message_size=__max_message_size__
        )
        for message_chunk in message_chunks:
            try:
                await self._send_chunk(bot, message_chunk, self.parse_mode)
            except RetryAfter as e:
                # Flood control de Telegram: esperar lo que pide y reintentar una vez.
                self.logger.warning('Telegram RetryAfter', seconds=e.retry_after)
                await asyncio.sleep(float(e.retry_after) + 1)
                await self._send_chunk(bot, message_chunk, self.parse_mode)
            except BadRequest as e:
                if 'parse entities' not in str(e).lower():
                    self.logger.error('Error enviando mensaje Telegram', error=str(e))
                    raise
                # HTML invalido (p. ej. texto de terceros con '<'): mejor llegar sin formato que perderse.
                self.logger.warning('Telegram rechazo el HTML, reenviando como texto plano')
                await self._send_chunk(bot, message_chunk, None)
            except Exception as e:
                self.logger.error('Error enviando mensaje Telegram', error=str(e))
                raise

    async def _send_chunk(self, bot, text: str, parse_mode):
        await bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode=parse_mode,
            read_timeout=__read_timeout__,
            connect_timeout=__connect_timeout__
        )

    def send_chart_messages(self, photo_url: str, messages: list = None):
        """
        Envía un gráfico con mensajes (wrapper síncrono).
        """
        messages = messages or []
        asyncio.run(self._async_send_chart(photo_url, messages))

    @retry(
        retry=retry_if_exception_type((TimedOut, NetworkError)),
        stop=stop_after_attempt(__stop_after_attempt__),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _async_send_chart(self, photo_url: str, messages: list):
        """
        Envía una imagen y mensajes de forma asíncrona.
        """
        bot = Bot(token=self.token)
        try:
            self.logger.debug(f"[TELEGRAM] Attempting to send chart: {photo_url}")
            with open(photo_url, 'rb') as f:
                await bot.send_photo(
                    chat_id=self.chat_id,
                    photo=f,
                    read_timeout=__read_timeout__,
                    connect_timeout=__connect_timeout__
                )
            self.logger.debug(f"[TELEGRAM] Chart sent successfully: {photo_url}")
        except FileNotFoundError:
            self.logger.error(f'[TELEGRAM] Chart file not found: {photo_url}')
        except Exception as e:
            self.logger.error(f'[TELEGRAM] Error sending chart {photo_url}: {type(e).__name__}: {e}')

        # Enviar mensajes asociados
        for message in messages:
            await self._async_notify(message)

    def send_messages(self, messages: list = None):
        """
        Envía múltiples mensajes.
        """
        messages = messages or []
        for message in messages:
            self.notify(message)
