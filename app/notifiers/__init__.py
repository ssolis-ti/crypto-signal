"""
Notifiers Package - Canales de Notificación
============================================

Notificadores disponibles:
    - telegram_client.py  - Notificaciones a Telegram (principal)
    - webhook_client.py   - Webhook genérico (para integraciones futuras)
    - stdout_client.py    - Salida a consola (debug)

Eliminados (2026-01-18):
    - discord_client.py
    - email_client.py
    - slack_client.py
    - twilio_client.py
"""

from notifiers.telegram_client import TelegramNotifier
from notifiers.webhook_client import WebhookNotifier
from notifiers.stdout_client import StdoutNotifier

__all__ = ['TelegramNotifier', 'WebhookNotifier', 'StdoutNotifier']
