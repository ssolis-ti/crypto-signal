"""
MarketContext - Análisis de Contexto de Mercado
================================================
Analiza el contexto global: BTC trend, sentiment, correlación ALT/BTC.

Flujo:
    DataManager.get_tickers() → MarketContext.get_context() → Dict estructurado

IMPORTANTE: Todos los métodos tienen fallbacks para evitar crashes por datos faltantes.
"""

import structlog
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class MarketContextData:
    """Estructura de datos para contexto de mercado."""
    btc_trend: str = 'neutral'           # bullish/bearish/neutral
    btc_change_24h: float = 0.0          # % cambio 24h
    btc_change_1h: float = 0.0           # % cambio 1h (si disponible)
    market_sentiment: str = 'neutral'    # risk_on/risk_off/neutral
    total_gainers: int = 0               # Pares subiendo
    total_losers: int = 0                # Pares bajando
    dominance_ratio: float = 1.0         # gainers/losers
    top_gainers: List[Tuple[str, float]] = None  # [(symbol, %), ...]
    top_losers: List[Tuple[str, float]] = None
    
    def __post_init__(self):
        if self.top_gainers is None:
            self.top_gainers = []
        if self.top_losers is None:
            self.top_losers = []
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para uso en templates."""
        return {
            'btc_trend': self.btc_trend,
            'btc_change_24h': round(self.btc_change_24h, 2),
            'btc_change_1h': round(self.btc_change_1h, 2),
            'market_sentiment': self.market_sentiment,
            'total_gainers': self.total_gainers,
            'total_losers': self.total_losers,
            'dominance_ratio': round(self.dominance_ratio, 2),
            'top_gainers': self.top_gainers[:5],
            'top_losers': self.top_losers[:5]
        }


@dataclass
class AltStrengthData:
    """Fuerza relativa de una ALT vs BTC."""
    symbol: str = ''
    alt_change_24h: float = 0.0
    btc_change_24h: float = 0.0
    relative_strength: float = 1.0       # ALT/BTC ratio
    outperforming: bool = False          # ALT > BTC
    divergence: str = 'neutral'          # positive/negative/neutral
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'alt_change_24h': round(self.alt_change_24h, 2),
            'btc_change_24h': round(self.btc_change_24h, 2),
            'relative_strength': round(self.relative_strength, 2),
            'outperforming': self.outperforming,
            'divergence': self.divergence
        }


class MarketContext:
    """
    Analiza el contexto global del mercado.
    
    Uso:
        mc = MarketContext(data_manager, settings)
        context = mc.get_context('binance')
        alt_strength = mc.get_alt_strength('SOL/USDT', 'binance')
    """
    
    # Umbrales por defecto (pueden ser overrideados por config)
    DEFAULT_BULLISH_THRESHOLD = 2.0   # % para considerar bullish
    DEFAULT_BEARISH_THRESHOLD = -2.0  # % para considerar bearish
    DEFAULT_OUTPERFORM_RATIO = 1.2    # Ratio para outperforming
    
    def __init__(self, data_manager, settings: Dict = None):
        """
        Args:
            data_manager: Instancia de DataManager
            settings: Configuración opcional (settings.correlation)
        """
        self.dm = data_manager
        self.logger = structlog.get_logger()
        
        # Cargar umbrales de config o usar defaults
        self.config = settings.get('correlation', {}) if settings else {}
        thresholds = self.config.get('thresholds', {})
        
        self.bullish_threshold = thresholds.get('btc_bullish', self.DEFAULT_BULLISH_THRESHOLD)
        self.bearish_threshold = thresholds.get('btc_bearish', self.DEFAULT_BEARISH_THRESHOLD)
        self.outperform_ratio = thresholds.get('outperform_ratio', self.DEFAULT_OUTPERFORM_RATIO)
        
        # Par de referencia (BTC por defecto)
        self.reference_pair = self.config.get('reference_pair', 'BTC/USDT')
        
        # Cache interno
        self._context_cache: Dict[str, MarketContextData] = {}
    
    def get_context(self, exchange: str) -> MarketContextData:
        """
        Obtiene contexto de mercado con validación robusta.
        
        Returns:
            MarketContextData con todos los campos (nunca None)
        """
        try:
            tickers = self.dm.get_tickers(exchange)
            
            if not tickers:
                self.logger.warning("No tickers disponibles para contexto")
                return MarketContextData()
            
            # Extraer datos de BTC
            btc_data = self._get_btc_data(tickers)
            
            # Calcular gainers/losers
            gainers, losers = self._calculate_gainers_losers(tickers)
            
            # Determinar sentiment
            sentiment = self._calculate_sentiment(gainers, losers, btc_data['change_24h'])
            
            context = MarketContextData(
                btc_trend=self._determine_trend(btc_data['change_24h']),
                btc_change_24h=btc_data['change_24h'],
                btc_change_1h=btc_data.get('change_1h', 0.0),
                market_sentiment=sentiment,
                total_gainers=len(gainers),
                total_losers=len(losers),
                dominance_ratio=len(gainers) / max(len(losers), 1),
                top_gainers=gainers[:5],
                top_losers=losers[-5:][::-1]  # Últimos 5 invertidos
            )
            
            self.logger.info(
                f"Contexto: BTC {context.btc_trend} ({context.btc_change_24h}%), "
                f"Sentiment {context.market_sentiment}, "
                f"Gainers/Losers: {context.total_gainers}/{context.total_losers}"
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error obteniendo contexto de mercado: {e}")
            return MarketContextData()
    
    def get_alt_strength(self, symbol: str, exchange: str) -> AltStrengthData:
        """
        Compara rendimiento de una ALT vs BTC.
        
        Args:
            symbol: Par a analizar (ej: 'SOL/USDT')
            exchange: Nombre del exchange
            
        Returns:
            AltStrengthData con fuerza relativa (nunca None)
        """
        try:
            tickers = self.dm.get_tickers(exchange)
            
            if not tickers:
                return AltStrengthData(symbol=symbol)
            
            # Obtener cambios
            btc_change = self._safe_get_change(tickers, self.reference_pair)
            alt_change = self._safe_get_change(tickers, symbol)
            
            # Calcular fuerza relativa (evitar división por cero)
            if abs(btc_change) < 0.01:
                relative_strength = 1.0 if abs(alt_change) < 0.01 else (2.0 if alt_change > 0 else 0.5)
            else:
                relative_strength = (1 + alt_change/100) / (1 + btc_change/100)
            
            # Determinar divergencia
            outperforming = relative_strength >= self.outperform_ratio
            divergence = self._calculate_divergence(btc_change, alt_change)
            
            return AltStrengthData(
                symbol=symbol,
                alt_change_24h=alt_change,
                btc_change_24h=btc_change,
                relative_strength=relative_strength,
                outperforming=outperforming,
                divergence=divergence
            )
            
        except Exception as e:
            self.logger.error(f"Error calculando alt strength para {symbol}: {e}")
            return AltStrengthData(symbol=symbol)
    
    # ─────────────────────────────────────────
    # MÉTODOS PRIVADOS
    # ─────────────────────────────────────────
    
    def _get_btc_data(self, tickers: Dict) -> Dict:
        """Extrae datos de BTC con fallbacks."""
        btc_ticker = tickers.get(self.reference_pair, {})
        return {
            'change_24h': self._safe_float(btc_ticker.get('percentage', 0)),
            'change_1h': self._safe_float(btc_ticker.get('change', 0)),
            'last': self._safe_float(btc_ticker.get('last', 0))
        }
    
    def _calculate_gainers_losers(self, tickers: Dict) -> Tuple[List, List]:
        """Separa pares en gainers y losers."""
        pairs_data = []
        
        for symbol, ticker in tickers.items():
            if not symbol.endswith('/USDT'):
                continue
            
            change = self._safe_float(ticker.get('percentage', 0))
            pairs_data.append((symbol, change))
        
        # Ordenar por cambio
        pairs_data.sort(key=lambda x: x[1], reverse=True)
        
        gainers = [(s, c) for s, c in pairs_data if c > 0]
        losers = [(s, c) for s, c in pairs_data if c <= 0]
        
        return gainers, losers
    
    def _calculate_sentiment(self, gainers: List, losers: List, btc_change: float) -> str:
        """Determina sentiment del mercado."""
        ratio = len(gainers) / max(len(losers), 1)
        
        if ratio > 1.5 and btc_change > 1:
            return 'risk_on'
        elif ratio < 0.7 and btc_change < -1:
            return 'risk_off'
        else:
            return 'neutral'
    
    def _determine_trend(self, change_24h: float) -> str:
        """Determina tendencia basada en cambio %."""
        if change_24h >= self.bullish_threshold:
            return 'bullish'
        elif change_24h <= self.bearish_threshold:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_divergence(self, btc_change: float, alt_change: float) -> str:
        """Calcula divergencia entre BTC y ALT."""
        # Ambos suben o ambos bajan = neutral
        if (btc_change > 0 and alt_change > 0) or (btc_change < 0 and alt_change < 0):
            return 'neutral'
        
        # BTC baja, ALT sube = positivo para ALT
        if btc_change < 0 and alt_change > 0:
            return 'positive'
        
        # BTC sube, ALT baja = negativo para ALT
        if btc_change > 0 and alt_change < 0:
            return 'negative'
        
        return 'neutral'
    
    def _safe_get_change(self, tickers: Dict, symbol: str) -> float:
        """Obtiene cambio % de forma segura."""
        ticker = tickers.get(symbol, {})
        return self._safe_float(ticker.get('percentage', 0))
    
    def _safe_float(self, value) -> float:
        """Convierte a float de forma segura."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
