"""
Módulo de Ejecución de Estrategias (Strategies)
Encargado de aplicar las reglas de análisis técnico sobre los datos históricos
para generar señales de trading.
"""

import traceback
from copy import deepcopy
import structlog
from outputs import Output

class StrategyExecutor:
    """
    Clase que aplica indicadores, informantes y cruces sobre los datos.
    """

    def __init__(self, config, strategy_analyzer):
        self.logger = structlog.get_logger()
        self.indicator_conf = config.indicators
        self.informant_conf = config.informants
        self.crossover_conf = config.crossovers
        self.strategy_analyzer = strategy_analyzer
        
        output_interface = Output()
        self.output = output_interface.dispatcher

    def test_strategies(self, market_data, all_historical_data, output_mode):
        """
        Ejecuta las estrategias y retorna los resultados (señales).
        """
        new_result = dict()
        for exchange in market_data:
            self.logger.info("Beginning analysis of %s", exchange)
            if exchange not in new_result:
                new_result[exchange] = dict()

            for market_pair in market_data[exchange]:
                self.logger.info("Beginning analysis of %s", market_pair)
                if market_pair not in new_result[exchange]:
                    new_result[exchange][market_pair] = dict()

                # Ejecutar Análisis
                new_result[exchange][market_pair]['indicators'] = self._get_indicator_results(
                    exchange, market_pair, all_historical_data
                )
                new_result[exchange][market_pair]['informants'] = self._get_informant_results(
                    exchange, market_pair, all_historical_data
                )
                new_result[exchange][market_pair]['crossovers'] = self._get_crossover_results(
                    new_result[exchange][market_pair]
                )

                # Salida por consola (si aplica)
                if output_mode in self.output:
                    output_data = deepcopy(new_result[exchange][market_pair])
                    print(self.output[output_mode](output_data, market_pair), end='')
                else:
                    self.logger.warn("Output mode %s not supported", output_mode)

        print() # Línea vacía final
        return new_result

    def _get_analysis_result(self, dispatcher, indicator, dispatcher_args, market_pair):
        try:
            results = dispatcher[indicator](**dispatcher_args)
        except TypeError:
            self.logger.info(
                'Invalid type encountered while processing pair %s for indicator %s, skipping',
                market_pair, indicator
            )
            self.logger.info(traceback.format_exc())
            results = str()
        return results

    def _get_indicator_results(self, exchange, market_pair, all_historical_data):
        indicator_dispatcher = self.strategy_analyzer.indicator_dispatcher()
        results = {indicator: list() for indicator in self.indicator_conf.keys()}
        historical_data_cache = all_historical_data[exchange][market_pair]

        for indicator in self.indicator_conf:
            if indicator not in indicator_dispatcher:
                self.logger.warn("No such indicator %s, skipping.", indicator)
                continue

            for indicator_conf in self.indicator_conf[indicator]:
                if not indicator_conf['enabled']: continue

                candle_period = indicator_conf['candle_period']
                if candle_period not in historical_data_cache: continue
                if historical_data_cache[candle_period]:
                    
                    # Preparación de argumentos (refactorizado para brevedad)
                    analysis_args = {
                        'historical_data': historical_data_cache[candle_period],
                        'signal': indicator_conf['signal'],
                        'hot_thresh': indicator_conf.get('hot', 0),
                        'cold_thresh': indicator_conf.get('cold', 0)
                    }
                    # ... mapeo de argumentos adicionales ...
                    self._map_indicator_args(indicator, indicator_conf, analysis_args)

                    results[indicator].append({
                        'result': self._get_analysis_result(
                            indicator_dispatcher, indicator, analysis_args, market_pair
                        ),
                        'config': indicator_conf
                    })
        return results

    def _map_indicator_args(self, indicator, indicator_conf, analysis_args):
        """Helper para mapear argumentos específicos por indicador."""
        if 'period_count' in indicator_conf:
            analysis_args['period_count'] = indicator_conf['period_count']
        
        if indicator == 'rsi' and 'lrsi_filter' in indicator_conf:
            analysis_args['lrsi_filter'] = indicator_conf['lrsi_filter']

        if indicator == 'ma_ribbon':
            analysis_args['pval_th'] = indicator_conf.get('pval_th', 20)
            if 'ma_series' in indicator_conf:
                series = indicator_conf['ma_series']
                analysis_args['ma_series'] = [int(i) for i in series.replace(' ', '').split(',')]
            else:
                analysis_args['ma_series'] = [5, 15, 25, 35, 45]

        if indicator == 'ma_crossover':
            analysis_args['exponential'] = indicator_conf.get('exponential', False)
            analysis_args['ma_fast'] = indicator_conf.get('ma_fast', 13)
            analysis_args['ma_slow'] = indicator_conf.get('ma_slow', 30)

        if indicator == 'stochrsi_cross':
            analysis_args['smooth_k'] = indicator_conf.get('smooth_k', 10)
            analysis_args['smooth_d'] = indicator_conf.get('smooth_d', 3)

        if indicator in ['bollinger', 'bbp']:
            analysis_args['std_dev'] = indicator_conf.get('std_dev', 2)

        if indicator == 'klinger_oscillator':
            analysis_args['ema_short_period'] = indicator_conf.get('vf_ema_short', 32)
            analysis_args['ema_long_period'] = indicator_conf.get('vf_ema_long', 55)
            analysis_args['signal_period'] = indicator_conf.get('kvo_signal', 13)

        if indicator == 'ichimoku':
            analysis_args['tenkansen_period'] = indicator_conf.get('tenkansen_period', 20)
            analysis_args['kijunsen_period'] = indicator_conf.get('kijunsen_period', 60)
            analysis_args['senkou_span_b_period'] = indicator_conf.get('senkou_span_b_period', 120)
            analysis_args['custom_strategy'] = indicator_conf.get('custom_strategy', None)

        if indicator == 'candle_recognition':
            analysis_args['candle_check'] = indicator_conf.get('candle_check', 1)
            analysis_args['notification'] = indicator_conf.get('notification', 'hot')

        if indicator == 'aroon_oscillator':
            analysis_args['sma_vol_period'] = indicator_conf.get('sma_vol_period', 50)

    def _get_informant_results(self, exchange, market_pair, all_historical_data):
        informant_dispatcher = self.strategy_analyzer.informant_dispatcher()
        results = {informant: list() for informant in self.informant_conf.keys()}
        historical_data_cache = all_historical_data[exchange][market_pair]

        for informant in self.informant_conf:
            if informant not in informant_dispatcher:
                self.logger.warn("No such informant %s, skipping.", informant)
                continue

            for informant_conf in self.informant_conf[informant]:
                if not informant_conf['enabled']: continue

                candle_period = informant_conf['candle_period']
                if candle_period not in historical_data_cache: continue
                if historical_data_cache[candle_period]:
                    analysis_args = {'historical_data': historical_data_cache[candle_period]}
                    if 'period_count' in informant_conf and informant != 'lrsi':
                        analysis_args['period_count'] = informant_conf['period_count']

                    results[informant].append({
                        'result': self._get_analysis_result(
                            informant_dispatcher, informant, analysis_args, market_pair
                        ),
                        'config': informant_conf
                    })
        return results

    def _get_crossover_results(self, new_result):
        crossover_dispatcher = self.strategy_analyzer.crossover_dispatcher()
        results = {crossover: list() for crossover in self.crossover_conf.keys()}

        for crossover in self.crossover_conf:
            if crossover not in crossover_dispatcher:
                self.logger.warn("No such crossover %s, skipping.", crossover)
                continue

            for crossover_conf in self.crossover_conf[crossover]:
                if not crossover_conf['enabled']: continue
                try:
                    # Extracción segura de datos para crossover
                    key_indicator = new_result[crossover_conf['key_indicator_type']][crossover_conf['key_indicator']][crossover_conf['key_indicator_index']]
                    crossed_indicator = new_result[crossover_conf['crossed_indicator_type']][crossover_conf['crossed_indicator']][crossover_conf['crossed_indicator_index']]

                    crossover_conf['candle_period'] = str(crossover_conf['key_indicator']) + str(crossover_conf['key_indicator_index'])

                    dispatcher_args = {
                        'key_indicator': key_indicator['result'],
                        'key_signal': crossover_conf['key_signal'],
                        'key_indicator_index': crossover_conf['key_indicator_index'],
                        'crossed_indicator': crossed_indicator['result'],
                        'crossed_signal': crossover_conf['crossed_signal'],
                        'crossed_indicator_index': crossover_conf['crossed_indicator_index']
                    }
                    results[crossover].append({
                        'result': crossover_dispatcher[crossover](**dispatcher_args),
                        'config': crossover_conf
                    })
                except Exception as e:
                    self.logger.warning(e)
                    self.logger.warning(traceback.format_exc())
                    continue
        return results
