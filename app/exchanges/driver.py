"""
Driver CCXT para Exchanges
Implementación concreta usando la librería CCXT.
"""

import re
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import ccxt
import numpy as np
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from exchanges.base import BaseExchange


class CCXTDriver(BaseExchange):
    """
    Driver que utiliza CCXT para conectar con exchanges.
    Soporta múltiples exchanges de forma unificada.
    """

    def __init__(self, exchange_config: Dict):
        """
        Inicializa el driver cargando los exchanges configurados.
        
        Args:
            exchange_config: Configuración de exchanges del YAML.
        """
        super().__init__()
        self.exchanges: Dict = {}
        self.base_markets: Dict = {}
        self.top_pairs: Optional[int] = None
        self.exclude: List[str] = []

        self._load_exchanges(exchange_config)

    def _load_exchanges(self, exchange_config: Dict):
        """Carga los exchanges habilitados usando CCXT."""
        for exchange_name in exchange_config:
            config = exchange_config[exchange_name]
            
            if not config.get('required', {}).get('enabled', False):
                continue
                
            parameters = {'enableRateLimit': True}
            
            # Soporte para futuros
            if config.get('future', False):
                parameters['options'] = {'defaultType': 'future'}

            try:
                new_exchange = getattr(ccxt, exchange_name)(parameters)
                self.exchanges[new_exchange.id] = new_exchange
                
                # Configuración de mercados base
                all_pairs = config.get('all_pairs', [])
                self.base_markets[new_exchange.id] = all_pairs if all_pairs else []
                
                # Top pairs limit
                if 'top_pairs' in config:
                    self.top_pairs = config['top_pairs']
                    
                # Exclusiones
                if 'exclude' in config:
                    self.exclude = config['exclude']
                    
                self.logger.info(f"Exchange {exchange_name} cargado exitosamente")
                
            except Exception as e:
                self.logger.error(f"Error cargando exchange {exchange_name}: {e}")

    @retry(retry=retry_if_exception_type(ccxt.NetworkError), stop=stop_after_attempt(3))
    def get_historical_data(
        self, 
        market_pair: str, 
        time_unit: str,
        exchange: str,
        start_date: Optional[int] = None,
        max_periods: int = 240
    ) -> List[List]:
        """Obtiene datos históricos OHLCV con retry automático."""
        
        # Validar timeframe
        if time_unit not in self.exchanges[exchange].timeframes:
            valid = list(self.exchanges[exchange].timeframes)
            raise ValueError(f"{exchange} no soporta {time_unit}. Válidos: {valid}")

        # Calcular fecha de inicio si no se proporciona
        if not start_date:
            start_date = self._calculate_start_date(time_unit, max_periods)

        historical_data = self.exchanges[exchange].fetch_ohlcv(
            market_pair,
            timeframe=time_unit,
            since=start_date
        )

        if not historical_data:
            raise ValueError('No se obtuvieron datos históricos del exchange.')

        # Ordenar por timestamp ascendente
        historical_data.sort(key=lambda d: d[0])

        # Respetar rate limit
        time.sleep(self.exchanges[exchange].rateLimit / 1000)

        return historical_data

    def _calculate_start_date(self, time_unit: str, max_periods: int) -> int:
        """Calcula el timestamp de inicio basado en el timeframe."""
        timeframe_regex = re.compile(r'(\d+)([a-zA-Z])')
        match = timeframe_regex.match(time_unit)
        
        if not match:
            raise ValueError(f"Formato de timeframe inválido: {time_unit}")
            
        quantity = int(match.group(1))
        period = match.group(2)

        period_map = {
            'm': 'minutes', 'h': 'hours', 'd': 'days',
            'w': 'weeks', 'M': 'days', 'y': 'days'
        }
        
        # Ajustar para meses y años
        if period == 'M':
            quantity *= 30
        elif period == 'y':
            quantity *= 365

        delta_args = {period_map.get(period, 'hours'): quantity}
        start_date_delta = timedelta(**delta_args)
        max_days_date = datetime.now() - (max_periods * start_date_delta)
        
        return int(max_days_date.replace(tzinfo=timezone.utc).timestamp() * 1000)

    @retry(retry=retry_if_exception_type(ccxt.NetworkError), stop=stop_after_attempt(3))
    def get_markets(self, exchange: str, markets: List[str] = None) -> Dict:
        """Obtiene mercados filtrados de un exchange."""
        all_markets = self.exchanges[exchange].load_markets()
        active_markets = {k: v for k, v in all_markets.items() if v.get('active')}

        if markets:
            return {k: v for k, v in active_markets.items() if k in markets}
        
        return active_markets

    def load_markets(self, exchange: str) -> Dict:
        """Carga mercados de un exchange específico."""
        return self.exchanges[exchange].load_markets()

    @retry(retry=retry_if_exception_type(ccxt.NetworkError), stop=stop_after_attempt(3))
    def get_top_markets(self, exchange: str, base_markets: List[str]) -> List[str]:
        """Obtiene los pares con mayor volumen."""
        top_markets = []

        if not self.exchanges[exchange].has.get('fetchTickers'):
            return top_markets

        tickers = self.exchanges[exchange].fetch_tickers()

        for base_market in base_markets:
            # Excluir pares no deseados
            for pair in self.exclude:
                tickers.pop(f'{pair}/{base_market}', None)

            # Filtrar y ordenar por volumen
            values = [
                (k, int(v.get('quoteVolume', 0) or 0))
                for k, v in tickers.items()
                if k.endswith(base_market)
            ]

            values = np.array(values, dtype=[('market', 'U20'), ('volume', int)])
            values = np.sort(values, order='volume')

            if self.top_pairs and len(values) > self.top_pairs:
                values = values[-self.top_pairs:]['market'].tolist()
            else:
                values = values[:]['market'].tolist()

            top_markets.extend(values)

        return top_markets

    @retry(retry=retry_if_exception_type(ccxt.NetworkError), stop=stop_after_attempt(3))
    def get_exchange_markets(self, exchanges=None, markets=None):
        """Get market data for all symbol pairs listed on all configured exchanges.

        Args:
            markets (list, optional): A list of markets to get from the exchanges.
            exchanges (list, optional): A list of exchanges to collect market data from.

        Returns:
            dict: A dictionary containing market data for all symbol pairs.
        """
        if exchanges is None:
            exchanges = list(self.exchanges.keys())
        if markets is None:
            markets = []

        exchange_markets = dict()
        for exchange in exchanges:
            exchange_markets[exchange] = self.exchanges[exchange].load_markets()
            curr_markets = {
                k: v for k, v in exchange_markets[exchange].items() if v.get('active', True)
            }

            if markets:
                # Only retrieve markets the users specified
                exchange_markets[exchange] = {
                    key: curr_markets[key] for key in curr_markets if key in markets
                }

                for market in markets:
                    if market not in exchange_markets[exchange]:
                        self.logger.info(f'{exchange} has no market {market}, ignoring.')
            else:
                if self.base_markets.get(exchange):
                    if self.top_pairs and self.top_pairs > 0:
                        self.logger.info(
                            f'Getting top {self.top_pairs} pairs from {self.base_markets[exchange]} in {exchange}'
                        )
                        all_markets = {
                            key: curr_markets[key] for key in curr_markets
                            if curr_markets[key].get('quote') in self.base_markets[exchange]
                        }

                        top_markets = self.get_top_markets(exchange, self.base_markets[exchange])

                        exchange_markets[exchange] = {
                            k: v for k, v in all_markets.items() if k in top_markets
                        }
                    else:
                        self.logger.info(
                            f'Getting all {self.base_markets[exchange]} market pairs for {exchange}'
                        )
                        exchange_markets[exchange] = {
                            key: curr_markets[key] for key in curr_markets
                            if curr_markets[key].get('quote') in self.base_markets[exchange]
                        }

                        if isinstance(self.exclude, list) and len(self.exclude) > 0:
                            for base_market in self.base_markets[exchange]:
                                for pair_to_exclude in self.exclude:
                                    exchange_markets[exchange].pop(pair_to_exclude, None)
                                    exchange_markets[exchange].pop(
                                        f'{pair_to_exclude}/{base_market}', None
                                    )

            time.sleep(self.exchanges[exchange].rateLimit / 1000)

        return exchange_markets
