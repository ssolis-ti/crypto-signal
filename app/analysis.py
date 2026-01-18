"""Executes the trading strategies and analyzes the results.
"""

import math
from datetime import datetime

import pandas
import structlog
from talib import abstract

from analyzers import *
from analyzers.indicators import *
from analyzers.informants import *


class StrategyAnalyzer():
    """
    Capa de Análisis Técnico.
    Esta clase actúa como un orquestador (dispatcher) para todos los indicadores
    técnicos, informantes y cruces disponibles en el sistema.
    """

    def __init__(self):
        """Inicializa StrategyAnalyzer configurando el logger estructurado."""
        self.logger = structlog.get_logger()

    def indicator_dispatcher(self):
        """
        Mapea nombres clace de indicadores a sus métodos de análisis correspondientes.
        
        Returns:
            dict: Diccionario donde las llaves son strings (ej. 'rsi') y los valores
                  son las funciones (.analyze) de las clases de indicadores.
        """

        dispatcher = {
            'candle_recognition': candle_recognition.Candle_recognition().analyze,
            'aroon_oscillator': aroon_oscillator.Aroon_oscillator().analyze,
            'klinger_oscillator': klinger_oscillator.Klinger_oscillator().analyze,
            'adx': adx.Adx().analyze,
            'ichimoku': ichimoku.Ichimoku().analyze,
            'macd': macd.MACD().analyze,
            'rsi': rsi.RSI().analyze,
            'momentum': momentum.Momentum().analyze,
            'mfi': mfi.MFI().analyze,
            'stoch_rsi': stoch_rsi.StochasticRSI().analyze,
            'obv': obv.OBV().analyze,
            'iiv': iiv.IIV().analyze,
            'ma_ribbon': ma_ribbon.MARibbon().analyze,
            'ma_crossover': ma_crossover.MACrossover().analyze,
            'bollinger': bollinger.Bollinger().analyze,
            'bbp': bbp.BBP().analyze,
            'macd_cross': macd_cross.MACDCross().analyze,
            'stochrsi_cross': stochrsi_cross.StochRSICross().analyze,
            'sqzmom': sqzmom.SQZMOM().analyze
        }

        return dispatcher

    def informant_dispatcher(self):
        """
        Mapea nombres clave de informantes a sus métodos de análisis correspondientes.
        Los informantes suelen ser datos base como precios OHLCV o promedios simples.

        Returns:
            dict: Diccionario de funciones de análisis de informantes.
        """

        dispatcher = {
            'sma': sma.SMA().analyze,
            'ema': ema.EMA().analyze,
            'vwap': vwap.VWAP().analyze,
            'bollinger_bands': bollinger_bands.Bollinger().analyze,
            'ohlcv': ohlcv.OHLCV().analyze,
            'lrsi': lrsi.LRSI().analyze
        }

        return dispatcher

    def crossover_dispatcher(self):
        """
        Mapea lógicas de cruce (ej. cruce de medias) a sus métodos correspondientes.
        
        Returns:
            dict: Diccionario de funciones para análisis de cruces.
        """

        dispatcher = {
            'std_crossover': crossover.CrossOver().analyze
        }

        return dispatcher
