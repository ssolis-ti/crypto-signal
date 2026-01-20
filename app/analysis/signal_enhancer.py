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
import pandas as pd

from analysis.market_context import MarketContext, MarketContextData, AltStrengthData

# Fase 2: Indicadores Derivados
try:
    from analyzers.indicators.derived import DerivedIndicators
    DERIVED_AVAILABLE = True
except ImportError:
    DERIVED_AVAILABLE = False


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
    score: float = 50.0                  # Score continuo 0-100 (Fase 1)
    recommendation: str = 'hold'         # strong_buy/buy/hold/avoid/sell/strong_sell
    
    # Contexto
    context_note: str = ''
    btc_trend: str = 'neutral'
    btc_change_24h: float = 0.0
    relative_strength: float = 1.0
    divergence: str = 'neutral'
    market_sentiment: str = 'neutral'
    
    # Indicadores Derivados (Fase 2)
    rsi_slope: float = 0.0
    macd_acceleration: float = 0.0
    vwap_distance: float = 0.0
    momentum_divergence: str = 'none'
    
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
            'score': self.score,
            'recommendation': self.recommendation,
            'context_note': self.context_note,
            'btc_trend': self.btc_trend,
            'btc_change_24h': self.btc_change_24h,
            'relative_strength': self.relative_strength,
            'divergence': self.divergence,
            'market_sentiment': self.market_sentiment,
            # Fase 2: Derivados
            'rsi_slope': self.rsi_slope,
            'macd_acceleration': self.macd_acceleration,
            'vwap_distance': self.vwap_distance,
            'momentum_divergence': self.momentum_divergence
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
        
        # Configuración base
        self.config = settings.get('correlation', {}) if settings else {}
        self.enabled = self.config.get('enabled', False)
        self.logger.info(f"[SignalEnhancer] enabled={self.enabled}, config keys: {list(self.config.keys()) if self.config else 'None'}")
        
        quality_filter = self.config.get('quality_filter', {})
        self.filter_enabled = quality_filter.get('enabled', False)
        self.min_quality = quality_filter.get('min_quality', 'C')
        
        # ─────────────────────────────────────────
        # Parámetros de Scoring (desde config.yml)
        # ─────────────────────────────────────────
        scoring_cfg = self.config.get('scoring', {})
        self.btc_weight = scoring_cfg.get('btc_weight', 15)
        self.structure_weight = scoring_cfg.get('structure_weight', 10)
        self.rsi_weight = scoring_cfg.get('rsi_weight', 5)
        self.rsi_weight_bearish = scoring_cfg.get('rsi_weight_bearish', 3)  # [B] RSI reducido
        self.sentiment_weight = scoring_cfg.get('sentiment_weight', 5)
        
        # Umbrales RSI
        self.rsi_extreme_low = scoring_cfg.get('rsi_extreme_low', 25)
        self.rsi_oversold = scoring_cfg.get('rsi_oversold', 40)
        self.rsi_overbought = scoring_cfg.get('rsi_overbought', 60)
        self.rsi_extreme_high = scoring_cfg.get('rsi_extreme_high', 75)
        
        # Debug
        self.verbose_scoring = scoring_cfg.get('verbose_scoring', False)
        
        # ─────────────────────────────────────────
        # Output Control (desde config.yml)
        # ─────────────────────────────────────────
        output_cfg = self.config.get('output', {})
        self.market_scan_mode = output_cfg.get('market_scan_mode', True)  # [A]
        self.max_c_signals = output_cfg.get('max_c_signals', 5)           # [C]
        self.sort_by_score = output_cfg.get('sort_by_score', True)
        
        if scoring_cfg:
            self.logger.info(
                f"[SignalEnhancer] Scoring: BTC={self.btc_weight}, Struct={self.structure_weight}, "
                f"RSI={self.rsi_weight}/{self.rsi_weight_bearish}(bearish), "
                f"Output: max_c={self.max_c_signals}, scan_mode={self.market_scan_mode}"
            )
    
    def enhance(
        self, 
        signal: Dict, 
        exchange: str,
        rsi_value: float = None,
        indicator_data: Dict = None
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
            indicator_data: Datos adicionales para indicadores derivados (Fase 2)
                {
                    'rsi_series': pd.Series,
                    'macd_histogram': pd.Series,
                    'close': float,
                    'vwap': float
                }
        
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
            self.logger.debug(f"[ENHANCE] Calling get_context for {exchange}, symbol {enhanced.symbol}")
            context = self.mc.get_context(exchange)
            alt_strength = self.mc.get_alt_strength(enhanced.symbol, exchange)
            
            # Agregar contexto a la señal
            enhanced.btc_trend = context.btc_trend
            enhanced.btc_change_24h = context.btc_change_24h
            enhanced.market_sentiment = context.market_sentiment
            enhanced.relative_strength = alt_strength.relative_strength
            enhanced.divergence = alt_strength.divergence
            
            # Calcular calidad (scoring continuo - Fase 1)
            quality, confidence, note, score = self._calculate_quality(
                signal_type=enhanced.signal_type,
                btc_trend=context.btc_trend,
                alt_strength=alt_strength,
                sentiment=context.market_sentiment,
                rsi_value=rsi_value,
                context_data=indicator_data  # <- CRÍTICO: Pasar contexto para EMA filter
            )
            
            enhanced.quality = quality
            enhanced.confidence = confidence
            enhanced.score = score
            enhanced.context_note = note
            enhanced.recommendation = self._get_recommendation(quality, enhanced.signal_type)
            
            # Fase 2: Calcular y aplicar indicadores derivados
            if DERIVED_AVAILABLE and indicator_data:
                derived_adjustment = self._apply_derived_indicators(enhanced, indicator_data)
                if derived_adjustment != 0:
                    enhanced.score = max(0, min(100, enhanced.score + derived_adjustment))
                    # Recalcular quality si el score cambió significativamente
                    enhanced.quality = self._score_to_quality(enhanced.score)
                    enhanced.confidence = int(enhanced.score)
            
            self.logger.info(
                f"Señal {enhanced.symbol}: {enhanced.quality} (Score {enhanced.score:.0f}) "
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
    
    def _apply_derived_indicators(
        self, 
        enhanced: EnhancedSignal, 
        indicator_data: Dict
    ) -> float:
        """
        Calcula indicadores derivados y retorna ajuste de score (Fase 2).
        
        Args:
            enhanced: Señal a enriquecer
            indicator_data: Dict con series de datos
            
        Returns:
            Ajuste de score (-15 a +15)
        """
        adjustment = 0.0
        
        try:
            # RSI Slope
            if 'rsi_series' in indicator_data and indicator_data['rsi_series'] is not None:
                rsi_series = indicator_data['rsi_series']
                if isinstance(rsi_series, pd.Series) and len(rsi_series) > 3:
                    enhanced.rsi_slope = DerivedIndicators.rsi_slope(rsi_series)
                    # Bonus si RSI slope confirma dirección de señal
                    if enhanced.signal_type == 'hot' and enhanced.rsi_slope > 0.1:
                        adjustment += 5  # RSI subiendo confirma compra
                    elif enhanced.signal_type == 'cold' and enhanced.rsi_slope < -0.1:
                        adjustment += 5  # RSI bajando confirma venta
            
            # MACD Acceleration
            if 'macd_histogram' in indicator_data and indicator_data['macd_histogram'] is not None:
                macd_hist = indicator_data['macd_histogram']
                if isinstance(macd_hist, pd.Series) and len(macd_hist) > 3:
                    enhanced.macd_acceleration = DerivedIndicators.macd_acceleration(macd_hist)
                    # Bonus por aceleración favorable
                    if enhanced.signal_type == 'hot' and enhanced.macd_acceleration > 0:
                        adjustment += 3
                    elif enhanced.signal_type == 'cold' and enhanced.macd_acceleration < 0:
                        adjustment += 3
            
            # VWAP Distance
            close = indicator_data.get('close', 0)
            vwap = indicator_data.get('vwap', 0)
            if close > 0 and vwap > 0:
                enhanced.vwap_distance = DerivedIndicators.vwap_distance(close, vwap)
                # Bonus si precio está en zona favorable
                if enhanced.signal_type == 'hot' and enhanced.vwap_distance < -1:
                    adjustment += 3  # Precio bajo VWAP = bueno para compra
                elif enhanced.signal_type == 'cold' and enhanced.vwap_distance > 1:
                    adjustment += 3  # Precio alto VWAP = bueno para venta
            
            # Momentum Divergence
            if 'price_series' in indicator_data and 'rsi_series' in indicator_data:
                prices = indicator_data.get('price_series')
                rsi = indicator_data.get('rsi_series')
                if prices is not None and rsi is not None:
                    if len(prices) > 14 and len(rsi) > 14:
                        enhanced.momentum_divergence = DerivedIndicators.momentum_divergence(prices, rsi)
                        # Divergencia alcista ayuda a compras
                        if enhanced.signal_type == 'hot' and enhanced.momentum_divergence == 'bullish_divergence':
                            adjustment += 7
                        # Divergencia bajista ayuda a ventas
                        elif enhanced.signal_type == 'cold' and enhanced.momentum_divergence == 'bearish_divergence':
                            adjustment += 7
        
        except Exception as e:
            self.logger.debug(f"Error calculando indicadores derivados: {e}")
        
        return adjustment
    
    def _calculate_quality(
        self,
        signal_type: str,
        btc_trend: str,
        alt_strength: AltStrengthData,
        sentiment: str,
        rsi_value: float = None,
        context_data: Dict = None  # <- NUEVO: Contexto para filtros cruzados
    ) -> tuple:
        """
        Calcula calidad usando scoring continuo (Fase 1).
        
        Returns:
            (quality, confidence, note, score)
        """
        score = self._calculate_score(signal_type, btc_trend, alt_strength, sentiment, rsi_value, context_data)
        quality = self._score_to_quality(score)
        confidence = int(score)
        note = self._generate_score_note(btc_trend, alt_strength, score, signal_type)
        return quality, confidence, note, score
    
    def _calculate_score(
        self,
        signal_type: str,
        btc_trend: str,
        alt: AltStrengthData,
        sentiment: str,
        rsi: float = None,
        context_data: Dict = None
    ) -> float:
        """
        Calcula score continuo 0-100 con reglas heurísticas configurables.
        Los pesos se leen desde config.yml → correlation.scoring
        """
        score = 50.0  # Base neutral
        context_data = context_data or {}
        
        # Para debug detallado
        score_breakdown = {'base': 50}
        
        # ─────────────────────────────────────────
        # 1. Filtros de Estructura (EMA 99)
        # ─────────────────────────────────────────
        price = context_data.get('close', 0)
        ema_99 = context_data.get('ema_99', 0)
        
        structure_bullish = price > ema_99 if price > 0 and ema_99 > 0 else True
        structure_label = 'Bullish' if structure_bullish else 'Bearish'
        
        if signal_type == 'hot' and not structure_bullish:
            score -= self.structure_weight
            score_breakdown['structure'] = -self.structure_weight
            self.logger.debug(f"Penalización: Estructura bajista (Precio {price:.2f} < EMA {ema_99:.2f})")

        # ─────────────────────────────────────────
        # 2. Factores de Mercado (desde config)
        # ─────────────────────────────────────────
        btc_factors = {'bullish': self.btc_weight, 'neutral': 0, 'bearish': -self.btc_weight}
        btc_adjustment = btc_factors.get(btc_trend, 0)
        score_breakdown['btc'] = btc_adjustment
        
        # Penalizar compras si BTC no ayuda
        hot_btc_penalty = 0
        if signal_type == 'hot' and btc_trend != 'bullish':
            hot_btc_penalty = -5
            score += hot_btc_penalty
            score_breakdown['hot_btc_penalty'] = hot_btc_penalty
            
        # ALT Strength
        alt_adjustment = (alt.relative_strength - 1.0) * 25
        alt_adjustment = max(-25, min(25, alt_adjustment))
        score_breakdown['alt'] = round(alt_adjustment, 1)
        
        # Sentiment (desde config)
        sent_factors = {'risk_on': self.sentiment_weight, 'neutral': 0, 'risk_off': -self.sentiment_weight}
        sent_adjustment = sent_factors.get(sentiment, 0)
        score_breakdown['sentiment'] = sent_adjustment
        
        # Aplicar Factores Base
        if signal_type == 'hot':
            score += btc_adjustment + alt_adjustment + sent_adjustment
        elif signal_type == 'cold':
            score -= (btc_adjustment + alt_adjustment + sent_adjustment)

        # ─────────────────────────────────────────
        # 3. Validación RSI (desde config)
        # [B] Si estructura bearish, usar peso reducido
        # ─────────────────────────────────────────
        rsi_bonus = 0
        rsi_label = 'N/A'
        
        # Seleccionar peso RSI según estructura
        effective_rsi_weight = self.rsi_weight_bearish if not structure_bullish else self.rsi_weight
        
        if rsi is not None:
            macd_hist = context_data.get('macd_hist', 0)
            
            if signal_type == 'hot':
                if rsi < self.rsi_extreme_low:  # Extreme oversold
                    rsi_label = 'Extreme'
                    if macd_hist > 0:
                        rsi_bonus = effective_rsi_weight * 2  # Double bonus si MACD confirma
                    else:
                        rsi_bonus = effective_rsi_weight
                elif rsi < self.rsi_oversold:  # Oversold
                    rsi_label = 'Oversold'
                    rsi_bonus = effective_rsi_weight
                elif rsi > self.rsi_extreme_high:  # Extreme overbought en compra = malo
                    rsi_label = 'Overbought'
                    rsi_bonus = -self.rsi_weight * 3
                    
            elif signal_type == 'cold':
                if rsi > self.rsi_extreme_high:
                    rsi_label = 'Extreme'
                    rsi_bonus = self.rsi_weight * 2
                elif rsi > self.rsi_overbought:
                    rsi_label = 'Overbought'
                    rsi_bonus = self.rsi_weight
                elif rsi < self.rsi_extreme_low:
                    rsi_label = 'Oversold'
                    rsi_bonus = -self.rsi_weight * 2
        
        score += rsi_bonus
        score_breakdown['rsi'] = rsi_bonus
        
        # Clamp final
        final_score = max(0, min(100, score))
        
        # Logging según config
        if self.verbose_scoring:
            self.logger.info(
                f"[SCORE] {signal_type.upper()} | Struct:{structure_label} | "
                f"BTC:{btc_adjustment:+d} | ALT:{alt_adjustment:+.1f} | "
                f"RSI:{rsi_bonus:+d} ({rsi_label}) | TOTAL:{final_score:.0f}"
            )
        else:
            self.logger.debug(
                f"[CALIB] SCORE: Base=50 + Struct({structure_label}) "
                f"+ BTC({btc_adjustment}) + ALT({alt_adjustment:.1f}) + RSI({rsi_bonus}) = {final_score:.0f}"
            )
        
        return final_score
    
    def _generate_score_note(
        self, 
        btc_trend: str, 
        alt: AltStrengthData, 
        score: float,
        signal_type: str
    ) -> str:
        """Genera nota explicativa basada en score."""
        parts = []
        
        # BTC
        btc_labels = {'bullish': 'BTC alcista', 'bearish': 'BTC bajista', 'neutral': 'BTC lateral'}
        parts.append(btc_labels.get(btc_trend, 'BTC neutral'))
        
        # ALT
        if alt.outperforming:
            parts.append(f'ALT fuerte ({alt.relative_strength:.1f}x)')
        elif alt.relative_strength < 0.8:
            parts.append('ALT débil')
        
        # Score
        if score >= 75:
            parts.append('Score excelente')
        elif score >= 60:
            parts.append('Score sólido')
        elif score < 40:
            parts.append('Score bajo - precaución')
        
        return ', '.join(parts)

    def _score_to_quality(self, score: float) -> str:
        """Mapea score a calidad con umbrales estrictos."""
        if score >= 80:      # Antes 75
            return 'A+'
        elif score >= 65:    # Antes 60
            return 'A'
        elif score >= 50:    # Antes 40
            return 'B'
        else:
            return 'C'

    def _quality_for_hot(self, score: float, context_data: Dict) -> tuple:
        """Clasificación heurística para HOT."""
        # Esta función ahora delega al score, pero puede imponer techos
        price = context_data.get('close', 0)
        ema_99 = context_data.get('ema_99', 0)
        
        # REGLA: Si Precio < EMA 99, Calidad MÁXIMA = B
        if price > 0 and ema_99 > 0 and price < ema_99:
            valid_quality = self._score_to_quality(score)
            if valid_quality in ['A+', 'A']:
                return 'B', score, 'Rebote Técnico (Contra-tendencia)'
        
        return self._score_to_quality(score), score, 'Tendencia Alineada' if score >= 65 else 'Confirmar'

    def _quality_for_cold(self, score: float, context_data: Dict) -> tuple:
        # Similar logic for cold if needed
        return self._score_to_quality(score), score, ''
    
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
