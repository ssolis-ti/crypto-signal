"""
Cola de Notificaciones Prioritaria
===================================
Gestiona el envío de notificaciones con:
- Ordenamiento por prioridad (score/quality)
- Delay entre envíos para respetar rate limits
- Detección de señales duplicadas/updates

Uso:
    queue = NotificationQueue()
    queue.add(message_data, priority=score)
    queue.process_all(telegram_client, delay=1.0)
"""

import asyncio
import hashlib
import time
import structlog
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class QueuedNotification:
    """Una notificación en cola."""
    message: Dict[str, Any]
    priority: float  # Score 0-100, mayor = más urgente
    chart_file: Optional[str] = None
    symbol: str = ''
    indicator: str = ''
    created_at: float = field(default_factory=time.time)
    is_update: bool = False
    
    def get_signature(self) -> str:
        """Genera firma única para detectar duplicados."""
        key = f"{self.symbol}:{self.indicator}:{self.message.get('status', '')}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


class NotificationQueue:
    """
    Cola prioritaria de notificaciones con rate limiting.
    
    Features:
        - Ordena por prioridad (score más alto primero)
        - Detecta señales duplicadas y las marca como "update"
        - Respeta rate limits de Telegram con delays configurables
        - Filtra señales de baja calidad opcionalmente
    """
    
    # Rate limits de Telegram (aproximados)
    DELAY_BETWEEN_MESSAGES = 0.5  # segundos
    DELAY_BETWEEN_PHOTOS = 1.5    # segundos (fotos son más pesadas)
    DUPLICATE_WINDOW = 300        # segundos para considerar duplicado (5 min)
    
    def __init__(self, min_quality: str = 'C'):
        self.logger = structlog.get_logger()
        self.queue: List[QueuedNotification] = []
        self.sent_signatures: Dict[str, float] = {}  # signature -> timestamp
        self.min_quality = min_quality
        self.quality_order = {'A+': 4, 'A': 3, 'B': 2, 'C': 1}
    
    def add(
        self,
        message: Dict[str, Any],
        chart_file: Optional[str] = None
    ) -> bool:
        """
        Agrega notificación a la cola.
        
        Args:
            message: Dict con datos del mensaje (debe incluir score, quality, market)
            chart_file: Path al gráfico opcional
            
        Returns:
            True si fue agregado, False si fue filtrado
        """
        symbol = message.get('market', 'UNKNOWN')
        indicator = message.get('indicator', '')
        quality = message.get('quality', 'C')
        priority = message.get('score', 50.0)
        
        # Filtrar por calidad mínima
        if self.quality_order.get(quality, 0) < self.quality_order.get(self.min_quality, 0):
            self.logger.debug(f"[QUEUE] {symbol} filtrado (quality {quality} < {self.min_quality})")
            return False
        
        notification = QueuedNotification(
            message=message,
            priority=priority,
            chart_file=chart_file,
            symbol=symbol,
            indicator=indicator
        )
        
        # Detectar duplicados
        sig = notification.get_signature()
        if self._is_duplicate(sig):
            notification.is_update = True
            self.logger.info(f"[QUEUE] {symbol} marcado como UPDATE (señal reciente)")
        
        self.queue.append(notification)
        self.logger.debug(f"[QUEUE] Agregado: {symbol} (priority={priority:.0f}, update={notification.is_update})")
        
        return True
    
    def _is_duplicate(self, signature: str) -> bool:
        """Verifica si la señal fue enviada recientemente."""
        now = time.time()
        
        # Limpiar firmas expiradas
        expired = [s for s, t in self.sent_signatures.items() 
                   if now - t > self.DUPLICATE_WINDOW]
        for s in expired:
            del self.sent_signatures[s]
        
        return signature in self.sent_signatures
    
    def _mark_sent(self, signature: str):
        """Marca una firma como enviada."""
        self.sent_signatures[signature] = time.time()
    
    def sort_by_priority(self):
        """Ordena la cola por prioridad (mayor primero)."""
        self.queue.sort(key=lambda x: x.priority, reverse=True)
        self.logger.info(f"[QUEUE] Cola ordenada: {len(self.queue)} notificaciones")
    
    def get_next(self) -> Optional[QueuedNotification]:
        """Obtiene la siguiente notificación de mayor prioridad."""
        if not self.queue:
            return None
        return self.queue.pop(0)
    
    def process_all(
        self,
        send_func,
        delay_msg: float = None,
        delay_photo: float = None
    ) -> int:
        """
        Procesa todas las notificaciones en cola.
        
        Args:
            send_func: Función que recibe (message, chart_file, is_update)
            delay_msg: Delay entre mensajes (usa default si None)
            delay_photo: Delay entre fotos (usa default si None)
            
        Returns:
            Cantidad de notificaciones enviadas
        """
        delay_msg = delay_msg or self.DELAY_BETWEEN_MESSAGES
        delay_photo = delay_photo or self.DELAY_BETWEEN_PHOTOS
        
        self.sort_by_priority()
        sent_count = 0
        
        while self.queue:
            notif = self.get_next()
            if notif is None:
                break
            
            try:
                send_func(notif.message, notif.chart_file, notif.is_update)
                self._mark_sent(notif.get_signature())
                sent_count += 1
                
                # Delay según tipo
                if notif.chart_file:
                    time.sleep(delay_photo)
                else:
                    time.sleep(delay_msg)
                    
            except Exception as e:
                self.logger.error(f"[QUEUE] Error enviando {notif.symbol}: {e}")
        
        self.logger.info(f"[QUEUE] Procesadas {sent_count} notificaciones")
        return sent_count
    
    def clear(self):
        """Limpia la cola."""
        self.queue.clear()
    
    def size(self) -> int:
        """Retorna tamaño de la cola."""
        return len(self.queue)
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumen de la cola actual."""
        if not self.queue:
            return {'count': 0, 'top': None, 'updates': 0}
        
        updates = sum(1 for n in self.queue if n.is_update)
        top = max(self.queue, key=lambda x: x.priority)
        
        return {
            'count': len(self.queue),
            'top': f"{top.symbol} (score={top.priority:.0f})",
            'updates': updates,
            'quality_distribution': self._quality_distribution()
        }
    
    def _quality_distribution(self) -> Dict[str, int]:
        """Distribución de calidades en la cola."""
        dist = {'A+': 0, 'A': 0, 'B': 0, 'C': 0}
        for n in self.queue:
            q = n.message.get('quality', 'C')
            if q in dist:
                dist[q] += 1
        return dist
