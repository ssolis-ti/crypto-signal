"""
Módulo Core de Notificaciones
Orquesta los diferentes clientes de mensajería (Telegram, Discord, etc.)
y utiliza el MessageBuilder para preparar los contenidos.
"""

import copy
import sys
import traceback
from time import sleep

import structlog
from jinja2 import Template

from analyzers.utils import IndicatorUtils
from rendering.core import ChartRenderer
from notifications.builder import MessageBuilder
from notifications.validator import ConfigValidator

# Clientes de notificación
from notifiers.discord_client import DiscordNotifier
from notifiers.email_client import EmailNotifier
from notifiers.slack_client import SlackNotifier
from notifiers.stdout_client import StdoutNotifier
from notifiers.telegram_client import TelegramNotifier
from notifiers.twilio_client import TwilioNotifier
from notifiers.webhook_client import WebhookNotifier


class Notifier(IndicatorUtils):
    """
    Controlador central de notificaciones (Refactorizado).
    """

    def __init__(self, notifier_config, indicator_config, conditional_config, market_data):
        self.logger = structlog.get_logger()
        self.notifier_config = notifier_config
        self.indicator_config = indicator_config
        self.conditional_config = conditional_config
        self.market_data = market_data
        
        # Componentes delegados
        self.chart_renderer = ChartRenderer(indicator_config)
        self.builder = MessageBuilder(self.logger, self.market_data)
        
        self.enable_charts = False
        self.all_historical_data = False
        self.timezone = None
        
        # Inicialización de clientes
        self.twilio_clients = {}
        self.discord_clients = {}
        self.slack_clients = {}
        self.email_clients = {}
        self.telegram_clients = {}
        self.webhook_clients = {}
        self.stdout_clients = {}

        self._initialize_notifiers()

    def _initialize_notifiers(self):
        """Inicializa los clientes configurados usando ConfigValidator."""
        enabled_notifiers = []
        
        for notifier in self.notifier_config.keys():
            if notifier.startswith('twilio'):
                if ConfigValidator.validate_required_config(notifier, self.notifier_config):
                    self.twilio_clients[notifier] = TwilioNotifier(
                        twilio_key=self.notifier_config[notifier]['required']['key'],
                        twilio_secret=self.notifier_config[notifier]['required']['secret'],
                        twilio_sender_number=self.notifier_config[notifier]['required']['sender_number'],
                        twilio_receiver_number=self.notifier_config[notifier]['required']['receiver_number']
                    )
                    enabled_notifiers.append(notifier)
                    self.twilio_configured = True

            if notifier.startswith('discord'):
                if ConfigValidator.validate_required_config(notifier, self.notifier_config):
                    self.discord_clients[notifier] = DiscordNotifier(
                        webhook=self.notifier_config[notifier]['required']['webhook'],
                        username=self.notifier_config[notifier]['required']['username'],
                        avatar=self.notifier_config[notifier]['optional']['avatar']
                    )
                    enabled_notifiers.append(notifier)
                    self.discord_configured = True

            if notifier.startswith('slack'):
                if ConfigValidator.validate_required_config(notifier, self.notifier_config):
                    self.slack_client = SlackNotifier(
                        slack_webhook=self.notifier_config[notifier]['required']['webhook']
                    )
                    enabled_notifiers.append(notifier)
                    self.slack_configured = True

            if notifier.startswith('telegram'):
                if ConfigValidator.validate_required_config(notifier, self.notifier_config):
                    self.telegram_clients[notifier] = TelegramNotifier(
                        token=self.notifier_config[notifier]['required']['token'],
                        chat_id=self.notifier_config[notifier]['required']['chat_id'],
                        parse_mode=self.notifier_config[notifier]['optional']['parse_mode']
                    )
                    enabled_notifiers.append(notifier)
                    self.telegram_configured = True

            if notifier.startswith('email'):
                if ConfigValidator.validate_required_config(notifier, self.notifier_config):
                    self.email_clients[notifier] = EmailNotifier(
                        smtp_address=self.notifier_config[notifier]['required']['smtp'],
                        username=self.notifier_config[notifier]['required']['username'],
                        password=self.notifier_config[notifier]['required']['password'],
                        to=self.notifier_config[notifier]['required']['to_addresses']
                    )
                    enabled_notifiers.append(notifier)
                    self.email_configured = True

            if notifier.startswith('webhook'):
                if ConfigValidator.validate_required_config(notifier, self.notifier_config):
                    self.webhook_clients[notifier] = WebhookNotifier(
                        url=self.notifier_config[notifier]['required']['url'],
                        username=self.notifier_config[notifier]['optional']['username'],
                        password=self.notifier_config[notifier]['optional']['password']
                    )
                    enabled_notifiers.append(notifier)
                    self.webhook_configured = True

            if notifier.startswith('stdout'):
                if ConfigValidator.validate_required_config(notifier, self.notifier_config):
                    self.stdout_clients[notifier] = StdoutNotifier()
                    enabled_notifiers.append(notifier)
                    self.stdout_configured = True

        self.logger.info('enabled notifers: %s', enabled_notifiers)

    def set_timezone(self, timezone):
        self.timezone = timezone
        self.chart_renderer.timezone_str = timezone

    def set_enable_charts(self, enable_charts):
        self.enable_charts = enable_charts

    def set_all_historical_data(self, all_historical_data):
        self.all_historical_data = all_historical_data

    def notify_all(self, new_analysis):
        """
        Punto de entrada principal para notificaciones.
        """
        # 1. Notificaciones Simples (Slack, Twilio)
        if hasattr(self, 'slack_configured') and self.slack_configured:
            msg = self.builder.indicator_message_templater(
                new_analysis, 
                self.notifier_config['slack']['optional']['template']
            )
            if msg.strip():
                self.slack_client.notify(msg)

        if hasattr(self, 'twilio_configured') and self.twilio_configured:
            msg = self.builder.indicator_message_templater(
                new_analysis,
                self.notifier_config['twilio']['optional']['template']
            )
            if msg.strip():
                self.twilio_clients['twilio'].notify(msg)

        # 2. Notificaciones Estructuradas (Telegram, Discord, Webhook)
        messages_by_pair = self.builder.build_indicator_messages(new_analysis, self.conditional_config)
        
        # Crear Gráficos
        if self.enable_charts and self.all_historical_data:
            self.create_charts(messages_by_pair)

        # Enviar Telegram
        if hasattr(self, 'telegram_configured') and self.telegram_configured:
            for exchange in messages_by_pair:
                for market in messages_by_pair[exchange]:
                    for period, msgs in messages_by_pair[exchange][market].items():
                        if not msgs: continue
                        
                        chart_file = None
                        market_safe = market.replace('/', '_').lower()
                        potential_chart = './charts/{}_{}_{}.png'.format(exchange, market_safe, period)
                        
                        # Intentar usar gráfico si existe
                        self.notify_telegram(msgs, potential_chart if self.enable_charts else None)

        # Enviar Webhook
        if hasattr(self, 'webhook_configured') and self.webhook_configured:
            for exchange in messages_by_pair:
                for market in messages_by_pair[exchange]:
                    for period, msgs in messages_by_pair[exchange][market].items():
                        if not msgs: continue
                        self.notify_webhook(msgs, None)

        # Enviar Stdout
        if hasattr(self, 'stdout_configured') and self.stdout_configured:
             for exchange in messages_by_pair:
                for market in messages_by_pair[exchange]:
                    for period, msgs in messages_by_pair[exchange][market].items():
                        if not msgs: continue
                        self.notify_stdout(msgs)

    def create_charts(self, messages):
        """Create charts to be available for all notifiers"""
        for exchange in messages:
            for market_pair in messages[exchange]:
                _messages = messages[exchange][market_pair]
                for candle_period in _messages:
                    if len(_messages[candle_period]) == 0:
                        continue
                    try:
                        candles_data = self.all_historical_data[exchange][market_pair][candle_period]
                        self.chart_renderer.create_chart(exchange, market_pair, candle_period, candles_data)
                    except Exception as e:
                        self.logger.info('Error creating chart for %s %s', market_pair, candle_period)
                        self.logger.exception(e)

        
    def notify_telegram(self, messages, chart_file):
        for notifier in self.telegram_clients:
            # Renderizar mensajes finales
            tpl = Template(self.notifier_config[notifier]['optional']['template'])
            formatted = [tpl.render(m) for m in messages]
            
            if chart_file:
                # Aquí deberíamos verificar si el archivo existe
                try:
                    self.telegram_clients[notifier].send_chart_messages(chart_file, formatted)
                except Exception as e:
                    self.logger.error(f"Error sending telegram chart: {e}")
                    self.telegram_clients[notifier].send_messages(formatted)
            else:
                 self.telegram_clients[notifier].send_messages(formatted)

