""" 
Punto de Entrada Principal (Main Entry Point)
Este módulo inicializa la configuración, los logs y despliega los hilos (workers)
que realizarán el análisis técnico de forma paralela.
"""

import concurrent.futures
import sys
import time
from threading import Thread

import structlog

import conf
import logs
from behaviour.core import Behaviour
from conf import Configuration
from exchanges import ExchangeInterface
from notifications.core import Notifier


def main():
    """
    Función principal que arranca el bot.
    1. Carga la configuración (YAML).
    2. Configura el logger.
    3. Inicializa la interfaz de exchange.
    4. Divide los mercados en 'chunks' y asigna un Worker a cada uno.
    """
    # Load settings and create the config object
    config = Configuration()
    settings = config.settings

    # Set up logger
    logs.configure_logging(settings['log_level'], settings['log_mode'])
    logger = structlog.get_logger()

    # Configure and run configured behaviour.
    exchange_interface = ExchangeInterface(config.exchanges)

    if settings['market_pairs']:
        market_pairs = settings['market_pairs']
        logger.info("Found configured markets: %s", market_pairs)
        market_data = exchange_interface.get_exchange_markets(
            markets=market_pairs)
    else:
        logger.info("No configured markets, using all available on exchange.")
        market_data = exchange_interface.get_exchange_markets()

    thread_list = []

    for exchange in market_data:
        num = 1
        for chunk in split_market_data(market_data[exchange], settings['market_data_chunk_size']):
            market_data_chunk = dict()
            market_data_chunk[exchange] = {
                key: market_data[exchange][key] for key in chunk}

            notifier = Notifier(
                config.notifiers, config.indicators, config.conditionals, market_data_chunk)
            behaviour = Behaviour(config, exchange_interface, notifier)

            workerName = "Worker-{}".format(num)
            worker = AnalysisWorker(
                workerName, behaviour, notifier, market_data_chunk, settings, logger)
            thread_list.append(worker)
            worker.daemon = True
            worker.start()

            time.sleep(settings['start_worker_interval'])
            num += 1

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
            self.logger.info('Starting %s', self.threadName)
            self.behaviour.run(self.market_data, self.settings['output_mode'])
            self.logger.info("%s sleeping for %s seconds",
                             self.threadName, self.settings['update_interval'])
            time.sleep(self.settings['update_interval'])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
