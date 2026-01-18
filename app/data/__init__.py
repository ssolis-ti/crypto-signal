"""
Data Package - Gestión centralizada de datos de mercado
========================================================

Módulos:
    manager.py      - DataManager (punto único de acceso a datos)
    pair_resolver.py - PairResolver (selección de pares manual/dinámica)

Flujo:
    app.py → PairResolver.resolve() → Lista de pares
    app.py → DataManager → CCXTDriver → Exchange API

Uso:
    from data import DataManager, PairResolver
    
    dm = DataManager(exchange_driver)
    resolver = PairResolver(settings, dm)
    pairs = resolver.resolve('binance')
"""

from data.manager import DataManager, DataCache
from data.pair_resolver import PairResolver

__all__ = ['DataManager', 'DataCache', 'PairResolver']
