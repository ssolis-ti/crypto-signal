"""
Indicadores Derivados (Fase 2)
==============================
Indicadores de segundo orden calculados a partir de indicadores base.
Estos NO generan señales directamente, sino que enriquecen el análisis.

Uso:
    from analyzers.indicators.derived import DerivedIndicators
    
    rsi_slope = DerivedIndicators.rsi_slope(rsi_series)
    macd_accel = DerivedIndicators.macd_acceleration(macd_hist)
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


class DerivedIndicators:
    """
    Indicadores derivados (de segundo orden).
    
    Todos los métodos son estáticos para facilitar uso sin instanciar.
    """
    
    @staticmethod
    def rsi_slope(rsi_series: pd.Series, period: int = 3) -> float:
        """
        Calcula la pendiente del RSI (momentum del momentum).
        
        Args:
            rsi_series: Serie de valores RSI
            period: Número de períodos para calcular pendiente
            
        Returns:
            Pendiente normalizada (-1 a +1 aproximadamente)
            Positivo = RSI subiendo, Negativo = RSI bajando
        """
        if len(rsi_series) < period + 1:
            return 0.0
        
        # Diferencia entre valor actual y valor hace N períodos
        diff = rsi_series.iloc[-1] - rsi_series.iloc[-period-1]
        # Normalizar por período
        slope = diff / period
        # Escalar a rango razonable (RSI va de 0-100, slope típico -5 a +5)
        return slope / 10.0
    
    @staticmethod
    def macd_acceleration(macd_histogram: pd.Series, period: int = 3) -> float:
        """
        Calcula la aceleración del histograma MACD.
        
        Args:
            macd_histogram: Serie del histograma MACD
            period: Número de períodos
            
        Returns:
            Aceleración (segunda derivada)
            Positivo = histograma acelerando hacia arriba
            Negativo = histograma acelerando hacia abajo
        """
        if len(macd_histogram) < period + 2:
            return 0.0
        
        # Primera derivada (velocidad)
        velocity = macd_histogram.diff()
        
        if velocity.iloc[-1] is None or velocity.iloc[-period] is None:
            return 0.0
        
        # Segunda derivada (aceleración)
        acceleration = velocity.iloc[-1] - velocity.iloc[-period]
        
        return acceleration
    
    @staticmethod
    def bollinger_width(upper: float, lower: float, middle: float) -> float:
        """
        Calcula el ancho de Bollinger Bands como % del precio medio.
        
        Args:
            upper: Banda superior
            lower: Banda inferior
            middle: Banda media (SMA)
            
        Returns:
            Ancho como porcentaje (ej: 5.0 = 5%)
        """
        if middle == 0:
            return 0.0
        
        width = upper - lower
        return (width / middle) * 100.0
    
    @staticmethod
    def volatility_squeeze(
        bb_width: float, 
        bb_width_avg: float,
        threshold: float = 0.5
    ) -> Tuple[bool, float]:
        """
        Detecta squeeze de volatilidad (compresión de Bollinger).
        
        Args:
            bb_width: Ancho actual de BB
            bb_width_avg: Ancho promedio de BB (últimos 20 períodos típico)
            threshold: Ratio bajo el cual se considera squeeze
            
        Returns:
            Tuple (is_squeeze, squeeze_intensity)
        """
        if bb_width_avg == 0:
            return False, 0.0
        
        ratio = bb_width / bb_width_avg
        is_squeeze = ratio < threshold
        squeeze_intensity = 1.0 - ratio if is_squeeze else 0.0
        
        return is_squeeze, squeeze_intensity
    
    @staticmethod
    def vwap_distance(close: float, vwap: float) -> float:
        """
        Calcula distancia del precio al VWAP como porcentaje.
        
        Args:
            close: Precio de cierre actual
            vwap: Volume Weighted Average Price
            
        Returns:
            Distancia como % (positivo = arriba de VWAP, negativo = abajo)
        """
        if vwap == 0:
            return 0.0
        
        return ((close - vwap) / vwap) * 100.0
    
    @staticmethod
    def relative_volume(
        current_volume: float, 
        avg_volume: float
    ) -> float:
        """
        Calcula volumen relativo vs promedio.
        
        Args:
            current_volume: Volumen actual
            avg_volume: Volumen promedio (típico 20 períodos)
            
        Returns:
            Ratio (1.0 = normal, 2.0 = doble del promedio)
        """
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    @staticmethod
    def momentum_divergence(
        price_series: pd.Series,
        indicator_series: pd.Series,
        lookback: int = 14
    ) -> str:
        """
        Detecta divergencia entre precio e indicador.
        
        Args:
            price_series: Serie de precios
            indicator_series: Serie del indicador (RSI, MACD, etc)
            lookback: Períodos a analizar
            
        Returns:
            'bullish_divergence' | 'bearish_divergence' | 'none'
        """
        if len(price_series) < lookback or len(indicator_series) < lookback:
            return 'none'
        
        # Últimos N períodos
        prices = price_series.iloc[-lookback:]
        indicator = indicator_series.iloc[-lookback:]
        
        # Encontrar mínimos/máximos
        price_min_idx = prices.idxmin()
        price_max_idx = prices.idxmax()
        ind_min_idx = indicator.idxmin()
        ind_max_idx = indicator.idxmax()
        
        # Divergencia alcista: precio hace nuevo mínimo, indicador no
        if prices.iloc[-1] < prices.min() * 1.02:  # Cerca del mínimo
            if indicator.iloc[-1] > indicator.min() * 1.05:  # Indicador más alto
                return 'bullish_divergence'
        
        # Divergencia bajista: precio hace nuevo máximo, indicador no
        if prices.iloc[-1] > prices.max() * 0.98:  # Cerca del máximo
            if indicator.iloc[-1] < indicator.max() * 0.95:  # Indicador más bajo
                return 'bearish_divergence'
        
        return 'none'
