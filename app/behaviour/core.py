"""
Módulo Core de Comportamiento
==============================
Orquesta el ciclo principal: Recolectar Datos → Analizar → Enriquecer → Notificar.

Flujo:
    1. DataCollector obtiene OHLCV
    2. StrategyExecutor ejecuta indicadores
    3. MarketContext analiza contexto global
    4. SignalEnhancer clasifica señales (A+/A/B/C)
    5. Notifier envía alertas filtradas

Flujo visual:
    app.py → Behaviour.run() → DataCollector
                             → StrategyExecutor
                             → MarketContext → SignalEnhancer
                             → Notifier
"""

import structlog
from analysis import StrategyAnalyzer
from analysis.market_context import MarketContext
from analysis.signal_enhancer import SignalEnhancer

from behaviour.data import DataCollector
from behaviour.strategies import StrategyExecutor


class Behaviour():
    """
    Controlador principal.
    Delega la complejidad a submódulos especializados.
    
    Componentes:
        - DataCollector: Obtiene datos OHLCV
        - StrategyExecutor: Ejecuta indicadores
        - MarketContext: Analiza contexto de mercado
        - SignalEnhancer: Clasifica señales
        - Notifier: Envía alertas
    """

    def __init__(self, config, exchange_interface, notifier, data_manager=None):
        """
        Inicializa el comportamiento con la configuración global.
        
        Args:
            config: Objeto Configuration
            exchange_interface: CCXTDriver
            notifier: Notifier
            data_manager: DataManager (opcional, para MarketContext)
        """
        self.logger = structlog.get_logger()
        self.config = config
        
        # ─────────────────────────────────────────
        # Componentes Core
        # ─────────────────────────────────────────
        self.strategy_analyzer = StrategyAnalyzer()
        self.data_collector = DataCollector(
            exchange_interface, 
            config.indicators, 
            config.informants, 
            self.strategy_analyzer
        )
        self.strategy_executor = StrategyExecutor(config, self.strategy_analyzer)
        
        # ─────────────────────────────────────────
        # Componentes de Correlación (Fase 4)
        # ─────────────────────────────────────────
        self.market_context = None
        self.signal_enhancer = None
        
        correlation_config = config.settings.get('correlation', {})
        correlation_enabled = correlation_config.get('enabled', False)
        print(f"DEBUG: correlation_config = {correlation_config}")
        print(f"DEBUG: correlation_enabled = {correlation_enabled}, data_manager = {data_manager is not None}")
        
        if correlation_enabled and data_manager:
            self.logger.info("Correlation analysis ENABLED")
            self.market_context = MarketContext(data_manager, config.settings)
            self.signal_enhancer = SignalEnhancer(self.market_context, config.settings)
        else:
            self.logger.info("Correlation analysis DISABLED")
        
        # ─────────────────────────────────────────
        # Dependencias Externas
        # ─────────────────────────────────────────
        self.notifier = notifier
        
        # ─────────────────────────────────────────
        # Configuración
        # ─────────────────────────────────────────
        self.enable_charts = config.settings['enable_charts']
        self.timezone = config.settings['timezone']
        self.all_historical_data = dict()
        
        # Cache para control de repetición de señales (Anti-Spam)
        self.last_notifications = {}

    def run(self, market_data, output_mode):
        """
        Punto de entrada para un ciclo de análisis.
        
        Flujo:
            1. Recolectar datos OHLCV
            2. Ejecutar estrategias
            3. Enriquecer señales con contexto
            4. Notificar
        """
        self.logger.info("Starting default analyzer...")
        self.logger.info("Using the following exchange(s): %s", list(market_data.keys()))

        # 1. Recolección de Datos
        self.all_historical_data = self.data_collector.get_all_historical_data(market_data)

        # 2. Ejecución de Estrategias
        new_result = self.strategy_executor.test_strategies(
            market_data, 
            self.all_historical_data, 
            output_mode
        )

        # 3. Enriquecer señales con contexto (si habilitado)
        if self.signal_enhancer:
            new_result = self._enhance_signals(new_result, market_data)

        # 4. Notificación
        self.notifier.set_timezone(self.timezone)

        if self.enable_charts:
            self.notifier.set_enable_charts(True)
            self.notifier.set_all_historical_data(self.all_historical_data)

        self.notifier.notify_all(new_result)

    def _enhance_signals(self, results: dict, market_data: dict) -> dict:
        """
        Enriquece señales con contexto de mercado.
        
        Para cada señal HOT/COLD:
            1. MarketContext.get_context() → Contexto global
            2. SignalEnhancer.enhance() → Señal clasificada
        """
        if not self.signal_enhancer:
            return results
        
        for exchange in market_data:
            if exchange not in results:
                continue

            context = self.market_context.get_context(exchange)
            self.logger.info(
                f"Market Context: BTC {context.btc_trend} ({context.btc_change_24h}%)"
            )
            
            for market_pair in market_data[exchange]:
                if market_pair not in results[exchange]:
                    continue
                
                self._enhance_pair_signals(results[exchange][market_pair], market_pair, exchange)
        
        return results
    
    def _enhance_pair_signals(self, pair_results: dict, symbol: str, exchange: str):
        """
        Enriquece señales de un par específico con visión holística.
        
        Pasos:
        1. Recolectar 'indicator_context' (últimos valores de RSI, MACD, Precio, EMA).
        2. Iterar sobre señales crudas.
        3. Pasar contexto completo al enhancer para filtros cruzados.
        """
        self.logger.debug(f"[ENHANCE] Processing pair: {symbol}")
        
        # 1. Recolectar Contexto del Par (Snapshot)
        indicator_context = {}
        
        # Extraer datos de 'informants' (Precio, EMA)
        if 'informants' in pair_results:
            for ind_name, analyses in pair_results['informants'].items():
                for analysis in analyses:
                    result = analysis.get('result')
                    if result is not None and not isinstance(result, str) and not result.empty:
                        last_row = result.iloc[-1]
                        
                        if ind_name == 'ohlcv':
                            indicator_context['close'] = float(last_row['close'])
                        elif ind_name == 'ema':
                            indicator_context['ema_99'] = float(last_row['ema']) # Asumiendo EMA 99 configurada
        
        # Extraer datos de 'indicators' (RSI, MACD)
        if 'indicators' in pair_results:
            for ind_name, analyses in pair_results['indicators'].items():
                for analysis in analyses:
                    result = analysis.get('result')
                    if result is not None and not isinstance(result, str) and not result.empty:
                        last_row = result.iloc[-1]
                        
                        if ind_name == 'rsi':
                            indicator_context['rsi'] = float(last_row['rsi'])
                        elif ind_name == 'macd_cross':
                            # MACD Cross suele tener hist o macd/signal
                            if 'histogram' in last_row:
                                indicator_context['macd_hist'] = float(last_row['histogram'])
                            elif 'macd' in last_row:
                                indicator_context['macd_val'] = float(last_row['macd'])

        # 2. Procesar Señales con Contexto Completo
        for indicator_type in pair_results:
            if indicator_type not in ['indicators', 'crossovers']:
                continue
            
            for indicator in pair_results[indicator_type]:
                for analysis in pair_results[indicator_type][indicator]:
                    if isinstance(analysis.get('result'), str):
                        continue
                    
                    result = analysis.get('result')
                    if result is None or result.shape[0] == 0:
                        continue
                    
                    last_row = result.iloc[-1]
                    
                    # Detectar Flags
                    is_hot = last_row.get('is_hot', False) if hasattr(last_row, 'get') else getattr(last_row, 'is_hot', False)
                    is_cold = last_row.get('is_cold', False) if hasattr(last_row, 'get') else getattr(last_row, 'is_cold', False)
                    
                    # Determinar tipo de señal base
                    signal_type = 'neutral'
                    if is_hot:
                        signal_type = 'hot'
                    elif is_cold:
                        signal_type = 'cold'
                    
                    if signal_type == 'neutral':
                        continue
                    
                    # Paquete de señal
                    signal = {
                        'symbol': symbol,
                        'type': signal_type,
                        'indicator': indicator,
                        'values': {}
                    }
                    
                    # RSI específico de ESTA señal (para consistencia)
                    rsi_val = indicator_context.get('rsi')
                    
                    # Enhancer con visión completa
                    enhanced = self.signal_enhancer.enhance(
                        signal, 
                        exchange, 
                        rsi_value=rsi_val,
                        indicator_data=indicator_context 
                    )
                    
                    # ─────────────────────────────────────────
                    # Filtro de Repetición / Anti-Spam
                    # ─────────────────────────────────────────
                    cache_key = f"{symbol}_{signal_type}"
                    last_state = self.last_notifications.get(cache_key)
                    
                    should_notify = True
                    if last_state:
                         # Regla: Notificar solo si Score varía significativamente (>10) o Calidad mejora
                        score_diff = abs(enhanced.score - last_state['score'])
                        
                        # Calidad orden: A+ > A > B > C. Usamos orden explicito.
                        q_rank = {'A+': 4, 'A': 3, 'B': 2, 'C': 1}
                        current_rank = q_rank.get(enhanced.quality, 0)
                        last_rank = q_rank.get(last_state['quality'], 0)
                        
                        if score_diff < 10 and current_rank <= last_rank:
                            should_notify = False
                    
                    if should_notify:
                        import time
                        self.last_notifications[cache_key] = {
                            'timestamp': time.time(),
                            'score': enhanced.score,
                            'quality': enhanced.quality
                        }
                        
                    # Agregar al análisis
                    analysis['enhanced'] = enhanced.to_dict()
                    analysis['quality'] = enhanced.quality
                    analysis['context_note'] = enhanced.context_note
                    analysis['should_notify'] = should_notify
