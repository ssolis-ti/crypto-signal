"""
Módulo de Construcción de Mensajes (Builder)
Se encarga de procesar los resultados del análisis, aplicar plantillas Jinja2
y gestionar la frecuencia de alertas.
"""

import datetime
import re
import structlog
from jinja2 import Template
from pytz import timezone

class MessageBuilder:
    """
    Clase encargada de transformar datos de análisis en mensajes de texto o estructuras de datos.
    Maneja el estado de las últimas alertas para control de frecuencia.
    """

    def __init__(self, logger=None, market_data=None, timezone_str='UTC'):
        self.logger = logger or structlog.get_logger()
        self.market_data = market_data
        self.timezone_str = timezone_str
        self.last_analysis = {}
        self.alert_frequencies = {}
        self.first_run = True

    def parse_alert_frequency(self, alert_frequency):
        """Parsea cadenas como '1h', '5m' a objetos datetime."""
        now = datetime.datetime.now()
        matches = re.findall(r'\d+[dhms]', alert_frequency)
        if not matches:
            return None

        for match in matches:
            try:
                value = int(match[:-1])
            except Exception as e:
                self.logger.info('Unable to parse alert_frequency "%s"', value)
                continue
            
            if match.endswith('m'):
                now += datetime.timedelta(minutes=value)
            elif match.endswith('h'):
                now += datetime.timedelta(hours=value)
            elif match.endswith('s'):
                now += datetime.timedelta(seconds=value)
            elif match.endswith('d'):
                now += datetime.timedelta(days=value)
        return now

    def should_i_alert(self, alert_frequency_key, alert_frequency):
        """Determina si se debe enviar una alerta basada en la frecuencia configurada."""
        if alert_frequency_key in self.alert_frequencies:
            if self.alert_frequencies[alert_frequency_key] > datetime.datetime.now():
                return False
        
        timedelta = self.parse_alert_frequency(alert_frequency)
        if timedelta:
            self.alert_frequencies[alert_frequency_key] = timedelta
        return True

    def indicator_message_templater(self, new_analysis, template):
        """
        Crea un mensaje único basado en una plantilla Jinja2.
        Utilizado principalmente por Slack y Twilio.
        """
        if not self.last_analysis:
            self.last_analysis = new_analysis

        message_template = Template(template)
        new_message = str()

        # Iteración compleja sobre exchanges/mercados/indicadores
        for exchange in new_analysis:
            for market in new_analysis[exchange]:
                for indicator_type in new_analysis[exchange][market]:
                    if indicator_type == 'informants':
                        continue
                    
                    for indicator in new_analysis[exchange][market][indicator_type]:
                        for index, analysis in enumerate(new_analysis[exchange][market][indicator_type][indicator]):
                            if analysis['result'].shape[0] == 0:
                                continue

                            values = dict()

                            # Extracción de valores según tipo
                            if indicator_type == 'indicators':
                                for signal in analysis['config']['signal']:
                                    values[signal] = analysis['result'].iloc[-1][signal]
                                    if isinstance(values[signal], float):
                                        values[signal] = format(values[signal], '.8f')
                            
                            elif indicator_type == 'crossovers':
                                key_signal = '{}_{}'.format(
                                    analysis['config']['key_signal'],
                                    analysis['config']['key_indicator_index']
                                )
                                crossed_signal = '{}_{}'.format(
                                    analysis['config']['crossed_signal'],
                                    analysis['config']['crossed_indicator_index']
                                )
                                
                                values[key_signal] = analysis['result'].iloc[-1][key_signal]
                                if isinstance(values[key_signal], float):
                                    values[key_signal] = format(values[key_signal], '.8f')

                                values[crossed_signal] = analysis['result'].iloc[-1][crossed_signal]
                                if isinstance(values[crossed_signal], float):
                                    values[crossed_signal] = format(values[crossed_signal], '.8f')

                            latest_result = analysis['result'].iloc[-1]
                            status = 'neutral'
                            if latest_result['is_hot']:
                                status = 'hot'
                            elif latest_result['is_cold']:
                                status = 'cold'

                            if 'indicator_label' in analysis['config']:
                                indicator_label = analysis['config']['indicator_label']
                            else:
                                indicator_label = '{} {}'.format(
                                    indicator, analysis['config']['candle_period'])

                            # Actualizar estado en new_analysis
                            new_analysis[exchange][market][indicator_type][indicator][index]['status'] = status

                            if latest_result['is_hot'] or latest_result['is_cold']:
                                hot_cold_label = ''
                                if latest_result['is_hot'] and 'hot_label' in analysis['config']:
                                    hot_cold_label = analysis['config']['hot_label']
                                if latest_result['is_cold'] and 'cold_label' in analysis['config']:
                                    hot_cold_label = analysis['config']['cold_label']

                                # Verificar estado anterior para alertas 'once'
                                try:
                                    last_status = self.last_analysis[exchange][market][
                                        indicator_type][indicator][index]['status']
                                except (KeyError, IndexError):
                                    last_status = str()

                                should_alert = True
                                if analysis['config']['alert_frequency'] == 'once':
                                    if last_status == status:
                                        should_alert = False

                                if not analysis['config']['alert_enabled']:
                                    should_alert = False

                                if should_alert:
                                    base_currency, quote_currency = market.split('/')
                                    new_message += message_template.render(
                                        values=values,
                                        exchange=exchange,
                                        market=market,
                                        base_currency=base_currency,
                                        quote_currency=quote_currency,
                                        indicator=indicator,
                                        indicator_number=index,
                                        analysis=analysis,
                                        status=status,
                                        last_status=last_status,
                                        hot_cold_label=hot_cold_label,
                                        indicator_label=indicator_label
                                    )

        self.last_analysis = {**self.last_analysis, **new_analysis}
        return new_message

    def build_indicator_messages(self, new_analysis, conditional_config=False):
        """
        Versión estructurada de la construcción de mensajes (antiguo get_indicator_messages).
        Retorna un diccionario estructurado 'new_messages' por exchange/market/period.
        """
        if not self.last_analysis:
            self.last_analysis = new_analysis
            self.first_run = True # Validar lógica de arranque

        now = datetime.datetime.now(timezone(self.timezone_str))
        creation_date = now.strftime("%Y-%m-%d %H:%M:%S")

        new_messages = dict()
        ohlcv_values = dict()
        lrsi_values = dict()

        for exchange in new_analysis:
            new_messages[exchange] = dict()
            ohlcv_values[exchange] = dict()
            lrsi_values[exchange] = dict()

            for market_pair in new_analysis[exchange]:
                new_messages[exchange][market_pair] = dict()
                ohlcv_values[exchange][market_pair] = dict()
                lrsi_values[exchange][market_pair] = dict()

                # 1. Recolectar datos informativos (OHLCV, LRSI)
                if 'informants' in new_analysis[exchange][market_pair]:
                    # Getting OHLC prices
                    if 'ohlcv' in new_analysis[exchange][market_pair]['informants']:
                        for index, analysis in enumerate(new_analysis[exchange][market_pair]['informants']['ohlcv']):
                            values = dict()
                            for signal in analysis['config']['signal']:
                                values[signal] = analysis['result'].iloc[-1][signal]
                                ohlcv_values[exchange][market_pair][analysis['config']['candle_period']] = values

                    # Getting LRSI values
                    if 'lrsi' in new_analysis[exchange][market_pair]['informants']:
                        for index, analysis in enumerate(new_analysis[exchange][market_pair]['informants']['lrsi']):
                            values = dict()
                            for signal in analysis['config']['signal']:
                                values[signal] = analysis['result'].iloc[-1][signal]
                            lrsi_values[exchange][market_pair][analysis['config']['candle_period']] = values

                # 2. Procesar Indicadores y Cruces
                for indicator_type in new_analysis[exchange][market_pair]:
                    if indicator_type == 'informants':
                        continue

                    for indicator in new_analysis[exchange][market_pair][indicator_type]:
                        for index, analysis in enumerate(new_analysis[exchange][market_pair][indicator_type][indicator]):
                            if analysis['result'].shape[0] == 0:
                                continue

                            values = dict()
                            if 'candle_period' in analysis['config']:
                                candle_period = analysis['config']['candle_period']
                                if candle_period not in new_messages[exchange][market_pair]:
                                    new_messages[exchange][market_pair][candle_period] = list()

                            # Extracción de valores
                            if indicator_type == 'indicators':
                                for signal in analysis['config']['signal']:
                                    values[signal] = analysis['result'].iloc[-1][signal]
                                    if isinstance(values[signal], float):
                                        values[signal] = format(values[signal], '.2f')

                            elif indicator_type == 'crossovers':
                                key_signal = '{}_{}'.format(analysis['config']['key_signal'], analysis['config']['key_indicator_index'])
                                crossed_signal = '{}_{}'.format(analysis['config']['crossed_signal'], analysis['config']['crossed_indicator_index'])
                                
                                values[key_signal] = analysis['result'].iloc[-1][key_signal]
                                if isinstance(values[key_signal], float):
                                    values[key_signal] = format(values[key_signal], '.2f')
                                    
                                values[crossed_signal] = analysis['result'].iloc[-1][crossed_signal]
                                if isinstance(values[crossed_signal], float):
                                    values[crossed_signal] = format(values[crossed_signal], '.2f')

                            # Determinar estado
                            latest_result = analysis['result'].iloc[-1]
                            status = 'neutral'
                            if latest_result['is_hot']: status = 'hot'
                            elif latest_result['is_cold']: status = 'cold'
                            
                            new_analysis[exchange][market_pair][indicator_type][indicator][index]['status'] = status

                            if latest_result['is_hot'] or latest_result['is_cold']:
                                hot_cold_label = ''
                                if latest_result['is_hot'] and 'hot_label' in analysis['config']:
                                    hot_cold_label = analysis['config']['hot_label']
                                if latest_result['is_cold'] and 'cold_label' in analysis['config']:
                                    hot_cold_label = analysis['config']['cold_label']

                                # Lógica de 'should_alert'
                                try:
                                    last_status = self.last_analysis[exchange][market_pair][indicator_type][indicator][index]['status']
                                except:
                                    last_status = str()

                                should_alert = True
                                if not self.first_run and not conditional_config:
                                    if analysis['config']['alert_frequency'] == 'once' and last_status == status:
                                        should_alert = False
                                    else:
                                        alert_key = ''.join([market_pair, indicator, candle_period])
                                        should_alert = self.should_i_alert(alert_key, analysis['config']['alert_frequency'])
                                
                                if not analysis['config']['alert_enabled']:
                                    should_alert = False

                                if 'mute_cold' in analysis['config'] and analysis['config']['mute_cold'] and latest_result['is_cold']:
                                    should_alert = False

                                if should_alert:
                                    base_currency = market_pair.split('/')
                                    quote_currency = ''
                                    if len(base_currency) == 2:
                                        base_currency, quote_currency = base_currency
                                    
                                    # Formateo de precios (requiere self.market_data)
                                    prices = ''
                                    price_value = {}
                                    decimal_format = '.8f' # Default backup
                                    
                                    if self.market_data and exchange in self.market_data and market_pair in self.market_data[exchange]:
                                        precision = self.market_data[exchange][market_pair].get('precision', {})
                                        price_precision = precision.get('price', 8)
                                        # Manejar diferentes formatos de precisión de CCXT
                                        # Puede ser: int (2), float (0.01), o None
                                        try:
                                            if price_precision is None:
                                                price_precision = 8
                                            elif isinstance(price_precision, float) and price_precision < 1:
                                                # Caso: 0.01 significa 2 decimales, 0.001 significa 3
                                                import math
                                                price_precision = abs(int(math.log10(price_precision)))
                                            else:
                                                price_precision = int(price_precision)
                                            # Validar rango razonable
                                            if price_precision < 0 or price_precision > 18:
                                                price_precision = 8
                                        except (ValueError, TypeError):
                                            price_precision = 8
                                        decimal_format = '.{}f'.format(price_precision)

                                    candle_period = analysis['config']['candle_period']
                                    candle_values = ohlcv_values[exchange][market_pair]

                                    if candle_period in candle_values:
                                        for key, value in candle_values[candle_period].items():
                                            price_value[key] = value
                                            value = format(value, decimal_format)
                                            prices = '{} {}: {}'.format(prices, key.title(), value)

                                    decimal_format = '%' + decimal_format
                                    
                                    lrsi = ''
                                    if candle_period in lrsi_values[exchange][market_pair]:
                                        lrsi = lrsi_values[exchange][market_pair][candle_period].get('lrsi', '')
                                        if isinstance(lrsi, (int, float)):
                                            lrsi = format(lrsi, '.2f')

                                    indicator_label = analysis['config'].get('indicator_label', '')

                                    # Limpiar memoria
                                    if 'result' in analysis:
                                        del analysis['result']
                                    
                                    # Extraer datos de correlación y contexto si existen
                                    quality = analysis.get('quality', 'B')
                                    context_note = analysis.get('context_note', '')
                                    confidence = 0
                                    enhanced_data = analysis.get('enhanced', {})
                                    
                                    if enhanced_data:
                                        confidence = enhanced_data.get('confidence', 0)
                                        score = enhanced_data.get('score', 50.0)  # Fase 1
                                        btc_trend = enhanced_data.get('btc_trend', 'neutral')
                                        btc_change_24h = enhanced_data.get('btc_change_24h', 0)
                                        relative_strength = enhanced_data.get('relative_strength', 1.0)
                                        market_sentiment = enhanced_data.get('market_sentiment', 'neutral')
                                    else:
                                        btc_trend = 'neutral'
                                        btc_change_24h = 0
                                        relative_strength = 0
                                        market_sentiment = 'neutral'
                                        score = 50.0

                                    new_message = dict(
                                        values=values, exchange=exchange, market=market_pair, base_currency=base_currency,
                                        quote_currency=quote_currency, indicator=indicator, indicator_number=index,
                                        analysis=analysis, status=status, last_status=last_status,
                                        prices=prices, lrsi=lrsi, creation_date=creation_date, hot_cold_label=hot_cold_label,
                                        indicator_label=indicator_label, price_value=price_value, decimal_format=decimal_format,
                                        # Campos de Correlación (Fase 4) + Score (Fase 1)
                                        quality=quality, context_note=context_note, confidence=confidence, score=score,
                                        btc_trend=btc_trend, btc_change_24h=btc_change_24h, 
                                        relative_strength=relative_strength, market_sentiment=market_sentiment
                                    )

                                    new_messages[exchange][market_pair][candle_period].append(new_message)

        # Merge final
        self.last_analysis = {**self.last_analysis, **new_analysis}
        self.first_run = False
        return new_messages
