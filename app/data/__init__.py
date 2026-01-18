"""
Data Package - Gestión centralizada de datos de mercado
========================================================

Módulos:
    manager.py - DataManager (punto único de acceso)

Flujo:
    app.py → DataManager → CCXTDriver → Exchange API

Uso:
    from data import DataManager
    dm = DataManager(exchange_driver)
    top_pairs = dm.get_top_pairs('binance', top_n=50)
"""

from data.manager import DataManager, DataCache

__all__ = ['DataManager', 'DataCache']
