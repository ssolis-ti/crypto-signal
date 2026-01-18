"""
DataManager - Gestor Centralizado de Datos
==========================================
Punto único de acceso a datos de mercado.
Gestiona caché, rate limits y abstrae la fuente (CCXT, APIs externas).

Flujo:
    app.py → DataManager → CCXTDriver → Exchange API
    
Uso:
    data_manager = DataManager(config)
    top_pairs = data_manager.get_top_pairs(exchange='binance', top_n=50)
    ohlcv = data_manager.get_ohlcv(exchange, pair, timeframe)
"""

import time
import structlog
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """Entrada de caché con TTL."""
    data: Any
    timestamp: float
    ttl: int  # segundos


class DataCache:
    """
    Caché en memoria con TTL configurable.
    
    Uso:
        cache = DataCache()
        cache.set('key', data, ttl=300)
        data = cache.get('key')  # None si expiró
    """
    
    def __init__(self):
        self._store: Dict[str, CacheEntry] = {}
        self.logger = structlog.get_logger()
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene dato del caché si no expiró."""
        if key not in self._store:
            return None
        
        entry = self._store[key]
        if time.time() - entry.timestamp > entry.ttl:
            del self._store[key]
            return None
        
        return entry.data
    
    def set(self, key: str, data: Any, ttl: int = 300) -> None:
        """Guarda dato en caché con TTL."""
        self._store[key] = CacheEntry(data=data, timestamp=time.time(), ttl=ttl)
    
    def clear(self) -> None:
        """Limpia todo el caché."""
        self._store.clear()
    
    def invalidate(self, key: str) -> None:
        """Invalida una entrada específica."""
        if key in self._store:
            del self._store[key]


class DataManager:
    """
    Gestor centralizado de datos de mercado.
    
    Responsabilidades:
        - Punto único de acceso a datos
        - Gestión de caché
        - Control de rate limits
        - Abstracción de fuentes de datos
    
    Flujo:
        1. Verifica caché
        2. Si expiró, llama a CCXTDriver
        3. Aplica rate limit
        4. Actualiza caché
        5. Retorna datos
    """
    
    # TTLs por tipo de dato (segundos)
    TTL_TICKERS = 60          # Precios cambian rápido
    TTL_TOP_PAIRS = 3600      # Ranking cambia lento (1 hora)
    TTL_OHLCV = 300           # Velas cada 5 min mínimo
    TTL_MARKETS = 86400       # Lista de pares casi nunca cambia (24h)
    
    def __init__(self, exchange_driver):
        """
        Args:
            exchange_driver: Instancia de CCXTDriver
        """
        self.driver = exchange_driver
        self.cache = DataCache()
        self.logger = structlog.get_logger()
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms entre requests
    
    # ─────────────────────────────────────────
    # MÉTODOS PÚBLICOS (API del módulo)
    # ─────────────────────────────────────────
    
    def get_tickers(self, exchange: str) -> Dict:
        """
        Obtiene todos los tickers del exchange.
        
        Returns:
            Dict con {symbol: {last, bid, ask, volume, ...}}
        
        Caché: 60 segundos
        """
        cache_key = f"tickers:{exchange}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        self._respect_rate_limit()
        tickers = self.driver.get_all_tickers(exchange)
        self.cache.set(cache_key, tickers, self.TTL_TICKERS)
        
        return tickers
    
    def get_top_pairs(
        self, 
        exchange: str, 
        quote: str = 'USDT', 
        top_n: int = 50,
        min_volume: float = 0
    ) -> List[str]:
        """
        Obtiene Top N pares ordenados por volumen 24h.
        
        Args:
            exchange: Nombre del exchange
            quote: Moneda de cotización (USDT, BTC, etc.)
            top_n: Cantidad de pares a retornar
            min_volume: Volumen mínimo en quote currency
        
        Returns:
            Lista de símbolos: ['BTC/USDT', 'ETH/USDT', ...]
        
        Caché: 1 hora
        """
        cache_key = f"top_pairs:{exchange}:{quote}:{top_n}:{min_volume}"
        cached = self.cache.get(cache_key)
        if cached:
            self.logger.info(f"Top pairs desde caché: {len(cached)} pares")
            return cached
        
        # Obtener tickers
        tickers = self.get_tickers(exchange)
        self.logger.info(f"DEBUG: get_tickers returned {len(tickers)} tickers for {exchange}")
        
        # Filtrar y ordenar
        pairs_with_volume = []
        for symbol, ticker in tickers.items():
            if not symbol.endswith(f'/{quote}'):
                # self.logger.debug(f"DEBUG: Skipping {symbol} (quote mismatch)")
                continue
            
            volume = ticker.get('quoteVolume', 0) or 0
            if volume < min_volume:
                # self.logger.debug(f"DEBUG: Skipping {symbol} (vol {volume} < {min_volume})")
                continue
            
            pairs_with_volume.append((symbol, volume))
            
        self.logger.info(f"DEBUG: Found {len(pairs_with_volume)} pairs matching quote {quote} and min_vol {min_volume}")
        
        # Ordenar por volumen descendente
        pairs_with_volume.sort(key=lambda x: x[1], reverse=True)
        
        # Tomar top N
        top_pairs = [pair[0] for pair in pairs_with_volume[:top_n]]
        
        self.cache.set(cache_key, top_pairs, self.TTL_TOP_PAIRS)
        self.logger.info(f"Top {len(top_pairs)} pares por volumen obtenidos")
        
        return top_pairs
    
    def get_ohlcv(
        self, 
        exchange: str, 
        market_pair: str, 
        timeframe: str,
        limit: int = 240
    ) -> List[List]:
        """
        Obtiene datos OHLCV (velas).
        
        Args:
            exchange: Nombre del exchange
            market_pair: Par de mercado (BTC/USDT)
            timeframe: Periodo de velas (4h, 1d, etc.)
            limit: Cantidad de velas
        
        Returns:
            Lista de [timestamp, open, high, low, close, volume]
        
        Caché: 5 minutos
        """
        cache_key = f"ohlcv:{exchange}:{market_pair}:{timeframe}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        self._respect_rate_limit()
        ohlcv = self.driver.get_historical_data(
            market_pair=market_pair,
            exchange=exchange,
            time_unit=timeframe,
            max_periods=limit
        )
        
        self.cache.set(cache_key, ohlcv, self.TTL_OHLCV)
        return ohlcv
    
    def get_market_context(self, exchange: str, quote: str = 'USDT') -> Dict:
        """
        Obtiene contexto general del mercado.
        
        Returns:
            {
                'total_pairs': int,
                'total_volume_24h': float,
                'top_gainers': [(symbol, pct), ...],
                'top_losers': [(symbol, pct), ...],
                'btc_change_24h': float
            }
        """
        tickers = self.get_tickers(exchange)
        
        pairs_data = []
        total_volume = 0
        btc_change = 0
        
        for symbol, ticker in tickers.items():
            if not symbol.endswith(f'/{quote}'):
                continue
            
            pct = ticker.get('percentage', 0) or 0
            vol = ticker.get('quoteVolume', 0) or 0
            
            pairs_data.append((symbol, pct, vol))
            total_volume += vol
            
            if symbol == f'BTC/{quote}':
                btc_change = pct
        
        # Ordenar por cambio %
        pairs_data.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'total_pairs': len(pairs_data),
            'total_volume_24h': total_volume,
            'top_gainers': [(p[0], p[1]) for p in pairs_data[:5]],
            'top_losers': [(p[0], p[1]) for p in pairs_data[-5:]],
            'btc_change_24h': btc_change
        }
    
    # ─────────────────────────────────────────
    # MÉTODOS PRIVADOS
    # ─────────────────────────────────────────
    
    def _respect_rate_limit(self) -> None:
        """Espera si es necesario para respetar rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
