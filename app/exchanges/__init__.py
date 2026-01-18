"""
Paquete de Exchanges
Proporciona una capa de abstracción para interactuar con múltiples exchanges.
"""

from exchanges.base import BaseExchange
from exchanges.driver import CCXTDriver

# Alias de compatibilidad con el código legacy
ExchangeInterface = CCXTDriver

__all__ = ['BaseExchange', 'CCXTDriver', 'ExchangeInterface']
