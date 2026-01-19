"""
Módulo Core de Notificaciones
Orquesta los diferentes clientes de mensajería (Telegram, Webhook, Stdout)
y utiliza el MessageBuilder para preparar los contenidos.
"""

import os
import structlog
from jinja2 import Template

from rendering.core import ChartRenderer
from notifications.builder import MessageBuilder
from notifications.validator import ConfigValidator
from notifications.queue import NotificationQueue

# Clientes de notificación activos
from notifiers.stdout_client import StdoutNotifier
from notifiers.telegram_client import TelegramNotifier
from notifiers.webhook_client import WebhookNotifier


class Notifier():
    """
    Controlador central de notificaciones (Refactorizado).
    Limpieza: Solo soporta Telegram, Webhook y Stdout.
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
        self.telegram_clients = {}
        self.webhook_clients = {}
        self.stdout_clients = {}

        self._initialize_notifiers()

    def _initialize_notifiers(self):
        """Inicializa los clientes configurados usando ConfigValidator."""
        enabled_notifiers = []
        
        for notifier in self.notifier_config.keys():

            if notifier.startswith('telegram'):
                if ConfigValidator.validate_required_config(notifier, self.notifier_config):
                    self.telegram_clients[notifier] = TelegramNotifier(
                        token=self.notifier_config[notifier]['required']['token'],
                        chat_id=self.notifier_config[notifier]['required']['chat_id'],
                        parse_mode=self.notifier_config[notifier]['optional']['parse_mode']
                    )
                    enabled_notifiers.append(notifier)
                    self.telegram_configured = True

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
        Usa cola prioritaria para ordenar y controlar rate limits.
        """
        # Notificaciones Estructuradas (Telegram, Webhook)
        messages_by_pair = self.builder.build_indicator_messages(new_analysis, self.conditional_config)
        
        # Crear Gráficos
        if self.enable_charts and self.all_historical_data:
            self.create_charts(messages_by_pair)

        # Enviar Telegram con Cola Prioritaria
        if hasattr(self, 'telegram_configured') and self.telegram_configured:
            queue = NotificationQueue(min_quality='C')
            
            # Recolectar todas las notificaciones
            for exchange in messages_by_pair:
                for market in messages_by_pair[exchange]:
                    for period, msgs in messages_by_pair[exchange][market].items():
                        if not msgs: 
                            continue
                        
                        # Determinar chart file
                        market_safe = market.replace('/', '_').lower()
                        potential_chart = './charts/{}_{}_{}.png'.format(exchange, market_safe, period)
                        chart_file = potential_chart if self.enable_charts and os.path.exists(potential_chart) else None
                        
                        if chart_file:
                            self.logger.info(f"[QUEUE] Chart found: {potential_chart}")
                        
                        # Agregar cada mensaje a la cola
                        for msg in msgs:
                            queue.add(msg, chart_file)
            
            # Log summary antes de procesar
            summary = queue.get_summary()
            if summary['count'] > 0:
                self.logger.info(
                    f"[QUEUE] {summary['count']} señales | "
                    f"Top: {summary['top']} | Updates: {summary['updates']}"
                )
            
            # Procesar cola con delays
            queue.process_all(
                send_func=lambda msg, chart, is_update: self._send_telegram_queued(msg, chart, is_update),
                delay_msg=0.5,
                delay_photo=1.5
            )

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
            tpl = Template(self.notifier_config[notifier]['optional']['template'])
            formatted = [tpl.render(m) for m in messages]
            
            if chart_file:
                try:
                    self.telegram_clients[notifier].send_chart_messages(chart_file, formatted)
                except Exception as e:
                    self.logger.error(f"Error sending telegram chart: {e}")
                    self.telegram_clients[notifier].send_messages(formatted)
            else:
                 self.telegram_clients[notifier].send_messages(formatted)
    
    def _send_telegram_queued(self, message: dict, chart_file: str, is_update: bool):
        """
        Envía una notificación individual desde la cola.
        
        Args:
            message: Dict con datos del mensaje
            chart_file: Path al gráfico o None
            is_update: Si es señal repetida, agrega prefijo UPDATE
        """
        for notifier in self.telegram_clients:
            tpl = Template(self.notifier_config[notifier]['optional']['template'])
            formatted = tpl.render(message)
            
            # Agregar prefijo UPDATE si es señal repetida
            if is_update:
                formatted = "🔄 UPDATE\n" + formatted
            
            try:
                if chart_file:
                    self.telegram_clients[notifier].send_chart_messages(chart_file, [formatted])
                else:
                    self.telegram_clients[notifier].send_messages([formatted])
            except Exception as e:
                self.logger.error(f"Error sending queued telegram: {e}")

    def notify_webhook(self, messages, chart_file):
        for notifier in self.webhook_clients:
            for message in messages:
                self.webhook_clients[notifier].notify(message)

    def notify_stdout(self, messages):
        for notifier in self.stdout_clients:
            for message in messages:
                self.stdout_clients[notifier].notify(message)

