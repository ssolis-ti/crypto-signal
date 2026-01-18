"""
PairResolver - Resuelve qué pares de mercado analizar
=====================================================
Determina la lista de pares basándose en configuración:
- Manual: Lee market_pairs del config
- Dinámico: Usa DataManager para obtener Top N por volumen

Flujo:
    app.py → PairResolver.resolve() → Lista de pares
    
Uso:
    resolver = PairResolver(config, data_manager)
    pairs = resolver.resolve(exchange)  # ['BTC/USDT', 'ETH/USDT', ...]
"""

import structlog
from typing import List, Optional


class PairResolver:
    """
    Resuelve la lista de pares a analizar.
    
    Modos:
        - manual: Usa market_pairs del config.yml
        - volume: Top N por volumen 24h vía DataManager
    """
    
    def __init__(self, settings: dict, data_manager=None):
        """
        Args:
            settings: Sección 'settings' del config
            data_manager: Instancia de DataManager (requerido para modo dinámico)
        """
        self.logger = structlog.get_logger()
        self.settings = settings
        self.data_manager = data_manager
        
        # Configuración de pares
        self.market_pairs = settings.get('market_pairs')
        self.dynamic_conf = settings.get('dynamic_pairs', {})
    
    def resolve(self, exchange: str) -> List[str]:
        """
        Resuelve la lista de pares para un exchange.
        
        Lógica:
            1. Si market_pairs está definido → usar esos (modo manual)
            2. Si dynamic_pairs.enabled → usar filtros dinámicos
            3. Si nada → lista vacía (error de config)
        
        Args:
            exchange: Nombre del exchange
            
        Returns:
            Lista de símbolos ['BTC/USDT', 'ETH/USDT', ...]
        """
        # Modo 1: Manual (market_pairs definido)
        if self.market_pairs:
            self.logger.info(f"Modo manual: {len(self.market_pairs)} pares configurados")
            return self.market_pairs
        
        # Modo 2: Dinámico
        if self.dynamic_conf.get('enabled', False):
            return self._resolve_dynamic(exchange)
        
        # Fallback: Error de configuración
        self.logger.warning("No hay pares configurados (market_pairs=null, dynamic_pairs.enabled=false)")
        return []
    
    def _resolve_dynamic(self, exchange: str) -> List[str]:
        """
        Resuelve pares usando filtros dinámicos.
        
        Flujo: DataManager.get_top_pairs() → Filtrar exclusiones → Retornar
        """
        if not self.data_manager:
            self.logger.error("DataManager no disponible para modo dinámico")
            return []
        
        source = self.dynamic_conf.get('source', 'volume')
        
        if source == 'volume':
            return self._resolve_by_volume(exchange)
        
        # Futuro: source == 'coingecko', 'cmc', etc.
        self.logger.warning(f"Fuente dinámica '{source}' no implementada")
        return []
    
    def _resolve_by_volume(self, exchange: str) -> List[str]:
        """
        Obtiene Top N pares ordenados por volumen 24h.
        """
        top_n = self.dynamic_conf.get('top_n', 50)
        quote = self.dynamic_conf.get('quote_currency', 'USDT')
        min_vol = self.dynamic_conf.get('min_volume_24h', 0)
        exclude = set(self.dynamic_conf.get('exclude', []))
        
        self.logger.info(f"Modo dinámico: Top {top_n} por volumen ({quote}), min ${min_vol:,.0f}")
        
        # Obtener del DataManager (con caché)
        pairs = self.data_manager.get_top_pairs(
            exchange=exchange,
            quote=quote,
            top_n=top_n + len(exclude),  # Pedir más para compensar exclusiones
            min_volume=min_vol
        )
        
        # Aplicar exclusiones
        filtered = [p for p in pairs if p not in exclude][:top_n]
        
        self.logger.info(f"Pares resueltos: {len(filtered)} activos")
        return filtered
    
    def get_market_context(self, exchange: str) -> Optional[dict]:
        """
        Obtiene contexto de mercado (opcional, para futuras features).
        
        Returns:
            {
                'total_pairs': int,
                'total_volume_24h': float,
                'top_gainers': [...],
                'top_losers': [...],
                'btc_change_24h': float
            }
        """
        if not self.data_manager:
            return None
        
        return self.data_manager.get_market_context(exchange)
