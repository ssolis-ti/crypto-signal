"""
Módulo Core de Comportamiento
Orquesta el ciclo principal: Recolectar Datos -> Analizar -> Notificar.
"""

import structlog
from analysis import StrategyAnalyzer

from behaviour.data import DataCollector
from behaviour.strategies import StrategyExecutor


class Behaviour():
    """
    Controlador principal refactorizado. 
    Delega la complejidad a submódulos especializados.
    """

    def __init__(self, config, exchange_interface, notifier):
        """
        Inicializa el comportamiento con la configuración global.
        """
        self.logger = structlog.get_logger()
        
        # Componentes Core
        self.strategy_analyzer = StrategyAnalyzer()
        self.data_collector = DataCollector(
            exchange_interface, 
            config.indicators, 
            config.informants, 
            self.strategy_analyzer
        )
        self.strategy_executor = StrategyExecutor(config, self.strategy_analyzer)
        
        # Dependencias Externas
        self.notifier = notifier
        
        # Configuración
        self.enable_charts = config.settings['enable_charts']
        self.timezone = config.settings['timezone']
        self.all_historical_data = dict()

    def run(self, market_data, output_mode):
        """
        Punto de entrada para un ciclo de análisis.
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

        # 3. Notificación
        self.notifier.set_timezone(self.timezone)

        if self.enable_charts:
            self.notifier.set_enable_charts(True)
            self.notifier.set_all_historical_data(self.all_historical_data)

        self.notifier.notify_all(new_result)
