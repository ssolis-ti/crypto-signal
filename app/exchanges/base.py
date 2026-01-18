"""
Clase Base Abstracta para Exchanges
Define la interfaz que deben implementar todos los drivers de exchange.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import structlog


class BaseExchange(ABC):
    """
    Interfaz abstracta para interacción con exchanges.
    Cada exchange concreto debe heredar de esta clase.
    """

    def __init__(self):
        self.logger = structlog.get_logger()

    @abstractmethod
    def get_historical_data(
        self, 
        market_pair: str, 
        time_unit: str, 
        start_date: Optional[int] = None,
        max_periods: int = 240
    ) -> List[List]:
        """
        Obtiene datos históricos OHLCV.
        
        Args:
            market_pair: Par de mercado (ej: BTC/USDT).
            time_unit: Temporalidad (ej: 1h, 5m).
            start_date: Timestamp de inicio en ms.
            max_periods: Número máximo de velas.
            
        Returns:
            Lista de [timestamp, open, high, low, close, volume].
        """
        pass

    @abstractmethod
    def get_markets(self, markets: List[str] = None) -> Dict:
        """
        Obtiene información de mercados disponibles.
        
        Args:
            markets: Lista opcional de mercados específicos.
            
        Returns:
            Diccionario con información de mercados.
        """
        pass

    @abstractmethod
    def load_markets(self) -> Dict:
        """Carga y cachea la información de mercados."""
        pass
