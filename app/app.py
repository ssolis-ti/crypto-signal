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
import uvicorn

import conf
import logs
from api.server import create_app
from api.store import AgentStateStore
from behaviour.core import Behaviour
from conf import Configuration
from exchanges import ExchangeInterface
from notifications.core import Notifier
from data import DataManager, PairResolver

AGENT_API_DB_PATH = 'agent_state/agent_state.db'
AGENT_API_PORT = 8090


def _start_agent_api(state_store, config, logger):
    """
    Arranca uvicorn en un hilo daemon dentro del mismo proceso (specs/009-agent-api/research.md:
    comparten el mismo AgentStateStore sin IPC). Bind a 0.0.0.0 dentro del contenedor -- el
    aislamiento a "solo localhost del host" se aplica en docker-compose.yml publicando el
    puerto como 127.0.0.1:8090, no aqui.
    """
    app_api = create_app(state_store, config.to_sanitized_dict)
    uvicorn_config = uvicorn.Config(
        app_api, host='0.0.0.0', port=AGENT_API_PORT, log_level='warning'
    )
    server = uvicorn.Server(uvicorn_config)

    thread = Thread(target=server.run, daemon=True, name='AgentAPI')
    thread.start()
    logger.info(f"Agent API listening on :{AGENT_API_PORT} (published as 127.0.0.1 by docker-compose)")


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

    # 2b. Iniciar API de agentes (specs/009-agent-api/): solo lectura, en un hilo daemon,
    # publicada por docker-compose.yml como 127.0.0.1:8090 (no accesible fuera del host).
    state_store = AgentStateStore(AGENT_API_DB_PATH)
    _start_agent_api(state_store, config, logger)

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
        logger.debug(f"Resolver returned {len(pairs) if pairs else 0} pairs for {exchange_name}")
        
        if pairs:
            logger.info("Found configured markets: %s", pairs)
            exchange_markets = exchange_interface.get_exchange_markets(
                markets=pairs
            )
            market_data.update(exchange_markets)
        else:
            logger.error(
                "No configured markets for %s. Not loading every market on the exchange.",
                exchange_name,
            )

    thread_list = []

    for exchange in market_data:
        num = 1
        chunk_size = effective_chunk_size(settings, len(market_data[exchange]))
        for chunk in split_market_data(market_data[exchange], chunk_size):
            market_data_chunk = dict()
            market_data_chunk[exchange] = {
                key: market_data[exchange][key] for key in chunk}

            notifier = Notifier(
                config.notifiers, config.indicators, config.conditionals, market_data_chunk)

            workerName = "Worker-{}".format(num)

            # Pasar data_manager para habilitar MarketContext y SignalEnhancer; pasar
            # state_store para que la API de agentes vea el estado de este worker.
            behaviour = Behaviour(
                config, exchange_interface, notifier, data_manager,
                state_store=state_store, worker_name=workerName
            )

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


def effective_chunk_size(settings, pair_count):
    """
    Tamano de chunk por worker. Con las alertas Wyckoff activas TODOS los pares deben ir en el mismo
    worker: el dato "pares simultaneos con evento en la misma vela" (la clave del edge) se cuenta por
    worker, y con varios workers quedaba partido (p. ej. 30 pares con chunk 20 = dos conteos de 20 y 10).
    """
    chunk_size = settings['market_data_chunk_size']
    wyckoff = settings.get('wyckoff_alerts') or {}
    if wyckoff.get('enabled') and pair_count > chunk_size:
        structlog.get_logger().warning(
            "wyckoff_alerts activo: un solo worker con los %d pares (market_data_chunk_size=%s "
            "partiria el conteo de pares simultaneos)" % (pair_count, chunk_size))
        return pair_count
    return chunk_size


def seconds_until_next_cycle(update_interval, now=None, slack=20.0):
    """
    Segundos hasta el proximo ciclo, alineado al reloj de pared: un poco despues de cada multiplo de
    `update_interval` (las velas de 4h cierran en multiplos de 5 min). Antes dormia `update_interval` despues
    de CADA vuelta, asi que el ciclo derivaba y el aviso llegaba entre 5 y 9 min despues del cierre.
    """
    if update_interval < 60:  # intervalos cortos (pruebas): dormir tal cual, alinear no tiene sentido
        return update_interval
    now = time.time() if now is None else now
    candidate = (now // update_interval) * update_interval + slack
    if candidate <= now + 5:
        candidate += update_interval
    return candidate - now


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
                output_mode = self.settings.get('output_mode', 'cli')
                self.behaviour.run(self.market_data, output_mode)

                raw_interval = self.settings.get('update_interval', 300)
                try:
                    update_interval = float(raw_interval)
                    if update_interval <= 0:
                        update_interval = 300.0
                except (ValueError, TypeError):
                    update_interval = 300.0

                wait_seconds = seconds_until_next_cycle(update_interval)
                self.logger.info("%s sleeping for %.0f seconds (next cycle aligned to the clock)",
                                 self.threadName, wait_seconds)
                time.sleep(wait_seconds)
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
