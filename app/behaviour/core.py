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
        
        # DEBUG: Ver estructura de results vs market_data
        self.logger.debug(f"[ENHANCE] results keys: {list(results.keys())[:10]}")
        
        for exchange in market_data:
            self.logger.debug(f"[ENHANCE] market_data[{exchange}] keys: {list(market_data[exchange].keys())[:10]}")
            
            context = self.market_context.get_context(exchange)
            self.logger.info(
                f"Market Context: BTC {context.btc_trend} ({context.btc_change_24h}%)"
            )
            
            for market_pair in market_data[exchange]:
                if market_pair not in results:
                    self.logger.debug(f"[ENHANCE] SKIP: {market_pair} not in results")
                    continue
                self._enhance_pair_signals(results[market_pair], market_pair, exchange)
        
        return results
    
    def _enhance_pair_signals(self, pair_results: dict, symbol: str, exchange: str):
        """
        Enriquece señales de un par específico.
        
        Agrega a cada análisis:
            - quality: A+/A/B/C
            - context_note: Explicación
            - enhanced: Dict completo de contexto
        """
        self.logger.debug(f"[ENHANCE] Processing pair: {symbol}")
        
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
                    
                    # Determinar tipo de señal
                    signal_type = 'neutral'
                    if last_row.get('is_hot', False):
                        signal_type = 'hot'
                    elif last_row.get('is_cold', False):
                        signal_type = 'cold'
                    
                    if signal_type == 'neutral':
                        continue
                    
                    # Enriquecer
                    signal = {
                        'symbol': symbol,
                        'type': signal_type,
                        'indicator': indicator,
                        'values': {}
                    }
                    
                    enhanced = self.signal_enhancer.enhance(signal, exchange)
                    
                    # Agregar al análisis
                    analysis['enhanced'] = enhanced.to_dict()
                    analysis['quality'] = enhanced.quality
                    analysis['context_note'] = enhanced.context_note
