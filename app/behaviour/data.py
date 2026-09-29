"""
Módulo de Recolección de Datos (DataCollector)
Encargado de interactuar con la interfaz de exchanges para obtener datos históricos (OHLCV).
"""

import time
import traceback
from datetime import datetime, timedelta, timezone

import structlog
from ccxt import ExchangeError
from tenacity import RetryError

from data.manager import drop_unclosed_candle

CLOCK_REFRESH_SECONDS = 600
CLOCK_WARN_SECONDS = 30


class DataCollector:
    """
    Clase responsable de la obtención de datos de mercado.
    Optimiza las llamadas a la API basándose en la configuración de indicadores.
    """

    def __init__(self, exchange_interface, indicator_conf, informant_conf, strategy_analyzer,
                 required_periods=()):
        self.logger = structlog.get_logger()
        self.exchange_interface = exchange_interface
        self.indicator_conf = indicator_conf
        self.informant_conf = informant_conf
        self.strategy_analyzer = strategy_analyzer
        # Periodos que otros modulos (p. ej. WyckoffAlerter: '4h') necesitan aunque ningun
        # indicador/informante habilitado los use.
        self.required_periods = tuple(required_periods)
        self._clock_offsets = {}

    def get_all_historical_data(self, market_data):
        """
        Recolecta datos históricos para todos los indicadores habilitados.
        """
        indicator_dispatcher = self.strategy_analyzer.indicator_dispatcher()
        informant_dispatcher = self.strategy_analyzer.informant_dispatcher()

        data = dict()

        for exchange in market_data:
            self.logger.info("Getting data for %s", list(market_data[exchange].keys()))
            if exchange not in data:
                data[exchange] = dict()

            for market_pair in market_data[exchange]:
                if market_pair not in data[exchange]:
                    data[exchange][market_pair] = dict()

                # Datos para Indicadores
                for indicator in self.indicator_conf:
                    if indicator not in indicator_dispatcher:
                        self.logger.warn("No such indicator %s, skipping.", indicator)
                        continue

                    for indicator_conf in self.indicator_conf[indicator]:
                        if indicator_conf['enabled']:
                            candle_period = indicator_conf['candle_period']
                            if candle_period not in data[exchange][market_pair]:
                                data[exchange][market_pair][candle_period] = self._get_historical_data(
                                    market_pair, exchange, candle_period
                                )

                # Datos para Informantes
                for informant in self.informant_conf:
                    if informant not in informant_dispatcher:
                        self.logger.warn("No such informant %s, skipping.", informant)
                        continue

                    for informant_conf in self.informant_conf[informant]:
                        if informant_conf['enabled']:
                            candle_period = informant_conf['candle_period']
                            if candle_period not in data[exchange][market_pair]:
                                data[exchange][market_pair][candle_period] = self._get_historical_data(
                                    market_pair, exchange, candle_period
                                )

                for candle_period in self.required_periods:
                    if candle_period not in data[exchange][market_pair]:
                        data[exchange][market_pair][candle_period] = self._get_historical_data(
                            market_pair, exchange, candle_period
                        )
        return data

    def _clock_offset(self, exchange):
        """
        Segundos que hay que SUMAR al reloj local para obtener la hora del exchange. Se mide cada
        CLOCK_REFRESH_SECONDS. Un reloj local desfasado (tipico tras suspender/reanudar Windows con
        Docker) haria tratar una vela en formacion como cerrada (repintado) o esconder una cerrada
        (alerta tarde). Si no se puede medir, se usa el ultimo valor conocido o el reloj local.
        """
        entry = self._clock_offsets.get(exchange)
        if entry and time.monotonic() - entry[1] < CLOCK_REFRESH_SECONDS:
            return entry[0]
        offset = entry[0] if entry else 0.0
        try:
            before = time.time()
            server_ms = self.exchange_interface.get_server_time_ms(exchange)
            after = time.time()
            if not isinstance(server_ms, (int, float)) or isinstance(server_ms, bool):
                raise TypeError("hora del exchange no numerica")
            offset = server_ms / 1000.0 - (before + after) / 2.0
            if abs(offset) > CLOCK_WARN_SECONDS:
                self.logger.warning(
                    "[RELOJ] El reloj local difiere %.0f s del de %s; se usa la hora del exchange "
                    "para decidir que velas cerraron", offset, exchange)
        except Exception as e:
            self.logger.warning("[RELOJ] No se pudo medir el desfase con %s (%s); se usa el ultimo valor conocido", exchange, e)
        self._clock_offsets[exchange] = (offset, time.monotonic())
        return offset

    def _now_utc(self, exchange):
        return datetime.now(timezone.utc) + timedelta(seconds=self._clock_offset(exchange))

    def _get_historical_data(self, market_pair, exchange, candle_period):
        """
        Obtiene lista OHLCV para un par/periodo específico.
        """
        historical_data = list()
        try:
            historical_data = self.exchange_interface.get_historical_data(
                market_pair, exchange, candle_period
            )
            # No repaint (Principio II): este es el camino principal del pipeline y no pasa
            # por DataManager.get_ohlcv, asi que la vela en formacion se descarta aca.
            historical_data = drop_unclosed_candle(historical_data, candle_period,
                                                   now_utc=self._now_utc(exchange))
        except RetryError:
            self.logger.error('Too many retries fetching information for pair %s, skipping', market_pair)
        except ExchangeError:
            self.logger.error('Exchange supplied bad data for pair %s, skipping', market_pair)
        except ValueError as e:
            self.logger.error(e)
            self.logger.error('Invalid data encountered while processing pair %s, skipping', market_pair)
            self.logger.debug(traceback.format_exc())
        except AttributeError:
            self.logger.error('Something went wrong fetching data for %s, skipping', market_pair)
            self.logger.debug(traceback.format_exc())
        except Exception as e:
            self.logger.error('Unexpected error fetching data for pair %s: %s, skipping', market_pair, e)
            self.logger.debug(traceback.format_exc())
            
        return historical_data

