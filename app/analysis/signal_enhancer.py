"""
SignalEnhancer - Clasificación y Potenciación de Señales
=========================================================
Evalúa señales según contexto de mercado y asigna calidad (A+/A/B/C).

Flujo:
    Señal cruda → SignalEnhancer.enhance() → Señal clasificada

IMPORTANTE: Todos los métodos retornan valores por defecto si hay errores.
"""

import structlog
from typing import Dict, Optional
from dataclasses import dataclass

from analysis.market_context import MarketContext, MarketContextData, AltStrengthData


@dataclass
class EnhancedSignal:
    """Señal enriquecida con contexto y clasificación."""
    # Datos originales
    symbol: str = ''
    signal_type: str = 'neutral'        # hot/cold/neutral
    indicator: str = ''
    values: Dict = None
    
    # Clasificación
    quality: str = 'B'                   # A+/A/B/C
    confidence: int = 50                 # 0-100
    recommendation: str = 'hold'         # strong_buy/buy/hold/avoid/sell/strong_sell
    
    # Contexto
    context_note: str = ''
    btc_trend: str = 'neutral'
    btc_change_24h: float = 0.0
    relative_strength: float = 1.0
    divergence: str = 'neutral'
    market_sentiment: str = 'neutral'
    
    def __post_init__(self):
        if self.values is None:
            self.values = {}
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para uso en templates."""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'indicator': self.indicator,
            'values': self.values,
            'quality': self.quality,
            'confidence': self.confidence,
            'recommendation': self.recommendation,
            'context_note': self.context_note,
            'btc_trend': self.btc_trend,
            'btc_change_24h': self.btc_change_24h,
            'relative_strength': self.relative_strength,
            'divergence': self.divergence,
            'market_sentiment': self.market_sentiment
        }
    
    def should_notify(self, min_quality: str = 'C') -> bool:
        """Determina si la señal debe ser notificada."""
        quality_order = {'A+': 4, 'A': 3, 'B': 2, 'C': 1}
        return quality_order.get(self.quality, 0) >= quality_order.get(min_quality, 0)


class SignalEnhancer:
    """
    Potencia o degrada señales según contexto de mercado.
    
    Uso:
        enhancer = SignalEnhancer(market_context, settings)
        enhanced = enhancer.enhance(signal, exchange)
    """
    
    def __init__(self, market_context: MarketContext, settings: Dict = None):
        """
        Args:
            market_context: Instancia de MarketContext
            settings: Configuración opcional (settings.correlation)
        """
        self.mc = market_context
        self.logger = structlog.get_logger()
        
        # Configuración
        self.config = settings.get('correlation', {}) if settings else {}
        self.enabled = self.config.get('enabled', False)
        
        quality_filter = self.config.get('quality_filter', {})
        self.filter_enabled = quality_filter.get('enabled', False)
        self.min_quality = quality_filter.get('min_quality', 'C')
    
    def enhance(
        self, 
        signal: Dict, 
        exchange: str,
        rsi_value: float = None
    ) -> EnhancedSignal:
        """
        Evalúa y clasifica una señal.
        
        Args:
            signal: {
                'symbol': 'SOL/USDT',
                'type': 'hot',
                'indicator': 'macd_cross',
                'values': {...}
            }
            exchange: Nombre del exchange
            rsi_value: Valor RSI actual (opcional, mejora clasificación)
        
        Returns:
            EnhancedSignal con calidad y contexto
        """
        # Crear señal base
        enhanced = EnhancedSignal(
            symbol=signal.get('symbol', ''),
            signal_type=signal.get('type', 'neutral'),
            indicator=signal.get('indicator', ''),
            values=signal.get('values', {})
        )
        
        # Si correlación no está habilitada, retornar con clasificación neutral
        if not self.enabled:
            enhanced.quality = 'B'
            enhanced.confidence = 50
            enhanced.context_note = 'Correlación deshabilitada'
            return enhanced
        
        try:
            # Obtener contexto
            context = self.mc.get_context(exchange)
            alt_strength = self.mc.get_alt_strength(enhanced.symbol, exchange)
            
            # Agregar contexto a la señal
            enhanced.btc_trend = context.btc_trend
            enhanced.btc_change_24h = context.btc_change_24h
            enhanced.market_sentiment = context.market_sentiment
            enhanced.relative_strength = alt_strength.relative_strength
            enhanced.divergence = alt_strength.divergence
            
            # Calcular calidad
            quality, confidence, note = self._calculate_quality(
                signal_type=enhanced.signal_type,
                btc_trend=context.btc_trend,
                alt_strength=alt_strength,
                sentiment=context.market_sentiment,
                rsi_value=rsi_value
            )
            
            enhanced.quality = quality
            enhanced.confidence = confidence
            enhanced.context_note = note
            enhanced.recommendation = self._get_recommendation(quality, enhanced.signal_type)
            
            self.logger.info(
                f"Señal {enhanced.symbol}: {enhanced.quality} "
                f"(BTC {enhanced.btc_trend}, RS {enhanced.relative_strength:.2f})"
            )
            
        except Exception as e:
            self.logger.error(f"Error clasificando señal {enhanced.symbol}: {e}")
            enhanced.quality = 'B'
            enhanced.confidence = 50
            enhanced.context_note = 'Error en clasificación'
        
        return enhanced
    
    def should_notify(self, enhanced: EnhancedSignal) -> bool:
        """Determina si la señal debe ser notificada según filtros."""
        if not self.filter_enabled:
            return True
        return enhanced.should_notify(self.min_quality)
    
    # ─────────────────────────────────────────
    # MÉTODOS PRIVADOS
    # ─────────────────────────────────────────
    
    def _calculate_quality(
        self,
        signal_type: str,
        btc_trend: str,
        alt_strength: AltStrengthData,
        sentiment: str,
        rsi_value: float = None
    ) -> tuple:
        """
        Calcula calidad de la señal.
        
        Returns:
            (quality, confidence, note)
        """
        if signal_type == 'hot':
            return self._quality_for_hot(btc_trend, alt_strength, sentiment, rsi_value)
        elif signal_type == 'cold':
            return self._quality_for_cold(btc_trend, alt_strength, sentiment)
        else:
            return 'B', 50, 'Señal neutral'
    
    def _quality_for_hot(
        self, 
        btc_trend: str, 
        alt: AltStrengthData, 
        sentiment: str,
        rsi: float = None
    ) -> tuple:
        """Clasifica señales HOT (compra)."""
        
        # MEJOR: BTC bullish + ALT outperforming + RSI bajo
        if btc_trend == 'bullish' and alt.outperforming:
            if rsi and rsi < 40:
                return 'A+', 90, f'BTC alcista, ALT supera ({alt.relative_strength:.1f}x), RSI bajo'
            return 'A', 80, f'BTC alcista, ALT supera ({alt.relative_strength:.1f}x)'
        
        # BUENO: BTC bullish + ALT neutral
        if btc_trend == 'bullish' and not alt.outperforming:
            return 'A', 75, 'BTC alcista, ALT alineada'
        
        # NEUTRAL: BTC neutral
        if btc_trend == 'neutral':
            if alt.outperforming:
                return 'A', 70, f'BTC lateral, ALT muestra fuerza ({alt.relative_strength:.1f}x)'
            if alt.divergence == 'negative':
                return 'C', 30, 'BTC lateral, ALT débil (divergencia negativa)'
            return 'B', 50, 'BTC lateral, sin confirmación'
        
        # MALO: BTC bearish (compra contra tendencia)
        if btc_trend == 'bearish':
            if alt.divergence == 'positive':
                return 'B', 45, 'BTC bajista, pero ALT resiste (riesgo)'
            return 'C', 25, 'BTC bajista, evitar compra contra tendencia'
        
        return 'B', 50, 'Clasificación por defecto'
    
    def _quality_for_cold(
        self, 
        btc_trend: str, 
        alt: AltStrengthData, 
        sentiment: str
    ) -> tuple:
        """Clasifica señales COLD (venta)."""
        
        # MEJOR venta: BTC bearish + ALT underperforming
        if btc_trend == 'bearish' and not alt.outperforming:
            return 'A+', 90, 'BTC bajista, ALT débil - venta confirmada'
        
        # BUENO: BTC bearish
        if btc_trend == 'bearish':
            return 'A', 80, 'BTC bajista, venta válida'
        
        # NEUTRAL: BTC neutral + ALT débil
        if btc_trend == 'neutral' and not alt.outperforming:
            return 'A', 70, 'BTC lateral, ALT débil'
        
        if btc_trend == 'neutral':
            return 'B', 50, 'BTC lateral, venta con precaución'
        
        # MALO: Venta en mercado alcista
        if btc_trend == 'bullish':
            return 'C', 25, 'BTC alcista, evitar venta contra tendencia'
        
        return 'B', 50, 'Clasificación por defecto'
    
    def _get_recommendation(self, quality: str, signal_type: str) -> str:
        """Genera recomendación basada en calidad y tipo."""
        if signal_type == 'hot':
            return {
                'A+': 'strong_buy',
                'A': 'buy',
                'B': 'hold',
                'C': 'avoid'
            }.get(quality, 'hold')
        elif signal_type == 'cold':
            return {
                'A+': 'strong_sell',
                'A': 'sell',
                'B': 'hold',
                'C': 'avoid'
            }.get(quality, 'hold')
        return 'hold'
