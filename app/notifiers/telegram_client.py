"""
Cliente Telegram Modernizado (v21+ Async)
Compatible con Python 3.12+
"""

import asyncio
import structlog
from telegram import Bot
from telegram.error import TimedOut, NetworkError
from tenacity import (
    retry, 
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
        self.bot = Bot(token=token)
        self.chat_id = chat_id
        self.parse_mode = parse_mode

    def notify(self, message: str):
        """
        Envía un mensaje de texto (wrapper síncrono para compatibilidad).
        """
        asyncio.run(self._async_notify(message))

    @retry(
        retry=retry_if_exception_type((TimedOut, NetworkError)),
        stop=stop_after_attempt(__stop_after_attempt__),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _async_notify(self, message: str):
        """
        Envía un mensaje de texto de forma asíncrona.
        """
        message_chunks = self.chunk_message(
            message=message, max_message_size=__max_message_size__
        )
        for message_chunk in message_chunks:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message_chunk,
                    parse_mode=self.parse_mode,
                    read_timeout=__read_timeout__,
                    connect_timeout=__connect_timeout__
                )
            except Exception as e:
                self.logger.error('Error enviando mensaje Telegram', error=str(e))
                raise

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
        try:
            with open(photo_url, 'rb') as f:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=f,
                    read_timeout=__read_timeout__,
                    connect_timeout=__connect_timeout__
                )
        except Exception as e:
            self.logger.error('Error enviando gráfico Telegram', error=str(e))

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
