"""
Analysis Package - Análisis de Mercado y Correlación
=====================================================

Módulos:
    market_context.py  - Contexto global de mercado (BTC trend, sentiment)
    signal_enhancer.py - Clasificación de señales (A+/A/B/C)

Flujo:
    DataManager → MarketContext → SignalEnhancer → Notifier
"""

from analysis.market_context import MarketContext
from analysis.signal_enhancer import SignalEnhancer

__all__ = ['MarketContext', 'SignalEnhancer']
