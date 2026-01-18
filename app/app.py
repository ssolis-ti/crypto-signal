""" 
Punto de Entrada Principal (Main Entry Point)
Este módulo inicializa la configuración, los logs y despliega los hilos (workers)
que realizarán el análisis técnico de forma paralela.

Flujo:
    1. Cargar configuración (YAML)
    2. Inicializar DataManager y PairResolver
    3. Resolver pares (manual o dinámico)
    4. Crear workers para cada chunk de pares
"""

import concurrent.futures
import sys
import time
import traceback
from threading import Thread

import structlog

import conf
import logs
from behaviour.core import Behaviour
from conf import Configuration
from exchanges import ExchangeInterface
from notifications.core import Notifier
from data import DataManager, PairResolver


def main():
    """
    Función principal que arranca el bot.
    
    Flujo:
        1. Carga configuración → 2. Inicializa exchanges
        3. Resuelve pares (manual/dinámico) → 4. Lanza workers
    """
    # 1. Cargar configuración
    config = Configuration()
    settings = config.settings

    # 2. Configurar logger
    logs.configure_logging(settings['log_level'], settings['log_mode'])
    logger = structlog.get_logger()

    # 3. Inicializar interfaz de exchange
    exchange_interface = ExchangeInterface(config.exchanges)

    # 4. Inicializar DataManager y PairResolver
    # Flujo: PairResolver → DataManager → CCXTDriver → Exchange API
    data_manager = DataManager(exchange_interface)
    pair_resolver = PairResolver(settings, data_manager)

    # 5. Resolver pares para cada exchange
    market_data = {}
    for exchange_name in exchange_interface.get_exchanges():
        pairs = pair_resolver.resolve(exchange_name)
        logger.info(f"DEBUG: Resolver returned {len(pairs) if pairs else 0} pairs for {exchange_name}")
        
        if pairs:
            logger.info("Found configured markets: %s", pairs)
            exchange_markets = exchange_interface.get_exchange_markets(
                markets=pairs
            )
            market_data.update(exchange_markets)
        else:
            logger.info("No configured markets, using all available on exchange.")
            market_data.update(exchange_interface.get_exchange_markets())

    thread_list = []

    for exchange in market_data:
        num = 1
        for chunk in split_market_data(market_data[exchange], settings['market_data_chunk_size']):
            market_data_chunk = dict()
            market_data_chunk[exchange] = {
                key: market_data[exchange][key] for key in chunk}

            notifier = Notifier(
                config.notifiers, config.indicators, config.conditionals, market_data_chunk)
            
            # Pasar data_manager para habilitar MarketContext y SignalEnhancer
            behaviour = Behaviour(config, exchange_interface, notifier, data_manager)

            workerName = "Worker-{}".format(num)
            worker = AnalysisWorker(
                workerName, behaviour, notifier, market_data_chunk, settings, logger)
            thread_list.append(worker)
            worker.daemon = True
            worker.start()

            time.sleep(settings['start_worker_interval'])
            num += 1

    if not market_data or not thread_list:
        logger.error("No market pairs found to analyze! Check your configuration (market_pairs or dynamic_pairs).")
        logger.error("Bot will sleep for 5 minutes and retry (restart container to force retry now).")
        time.sleep(300)
        return

    logger.info('All workers are running!')

    for worker in thread_list:
        worker.join()


def split_market_data(market_data, chunk_size):
    if len(market_data.keys()) > chunk_size:
        return list(chunks(list(market_data.keys()), chunk_size))
    else:
        return [list(market_data.keys())]


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class AnalysisWorker(Thread):
    """
    Hilo de ejecución individual (Worker).
    Cada worker procesa un subconjunto de pares de mercado en su propio loop.
    
    > [!IMPORTANT]
    > Escalabilidad: Si se configuran demasiados mercados, aumentar el tamaño de 
    > los 'chunks' o el número de hilos puede saturar la CPU o las APIs.
    """

    def __init__(self, threadName, behaviour, notifier, market_data, settings, logger):
        Thread.__init__(self)

        self.threadName = threadName
        self.behaviour = behaviour
        self.notifier = notifier
        self.market_data = market_data
        self.settings = settings
        self.logger = logger

    def run(self):
        """
        Ciclo de vida del hilo: Ejecutar análisis -> Dormir -> Repetir.
        """
        while True:
            try:
                self.logger.info('Starting %s', self.threadName)
                self.behaviour.run(self.market_data, self.settings['output_mode'])
                self.logger.info("%s sleeping for %s seconds",
                                 self.threadName, self.settings['update_interval'])
                time.sleep(self.settings['update_interval'])
            except Exception as e:
                self.logger.error(f"CRITICAL ERROR in {self.threadName}: {e}")
                self.logger.error(traceback.format_exc())
                # Dormir un poco para evitar loop infinito de logs si el error es persistente
                time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
