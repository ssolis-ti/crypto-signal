"""
Smart Notification System - Resumen + Detalle por Calidad
==========================================================
Sistema de notificación inteligente que reduce ruido y evita rate limits.

Flujo:
    ┌─────────────────────────────────────┐
    │ SEÑALES DETECTADAS (5)              │
    └──────────────┬──────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │ 1️⃣ RESUMEN RÁPIDO (1 mensaje)       │
    │    - Lista todas las señales        │
    │    - Sin imágenes                   │
    │    - Ordenadas por calidad          │
    └──────────────┬──────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │ 2️⃣ DETALLE SOLO A+ / A              │
    │    - Con imagen/chart               │
    │    - Análisis completo              │
    │    - Delay entre envíos (3s)        │
    └─────────────────────────────────────┘

Configuración (config.yml):
    settings:
      notifications:
        summary_enabled: true       # Enviar resumen inicial
        detail_min_quality: A       # Mínimo para enviar detalle
        chart_min_quality: A        # Mínimo para enviar chart

Conexiones:
    notifications/core.py → SmartNotificationManager
    SmartNotificationManager → TelegramClient
    
Advertencias:
    - Este módulo reemplaza el flujo anterior de NotificationQueue
    - Los templates de Telegram deben estar actualizados
    - El delay entre envíos es crítico para evitar rate limits
"""

import time
import structlog
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SignalSummary:
    """
    Resumen de una señal para el mensaje consolidado.
    
    Attributes:
        symbol: Par de mercado (ej: SUI/USDT)
        quality: Calidad calculada (A+, A, B, C)
        score: Score continuo 0-100
        signal_type: hot/cold
        indicator: Indicador que generó la señal
        rsi_value: Valor RSI si disponible
        btc_trend: Tendencia de BTC
    """
    symbol: str
    quality: str
    score: float
    signal_type: str
    indicator: str
    rsi_value: float = 0.0
    btc_trend: str = 'neutral'


class SmartNotificationManager:
    """
    Gestor de notificaciones inteligente.
    
    Responsabilidades:
        1. Agrupa señales por ciclo de análisis
        2. Genera resumen consolidado (1 mensaje)
        3. Envía detalles solo para señales de alta calidad
        4. Adjunta charts solo a señales A+ / A
    
    Flujo:
        add_signal() → ... → finalize_cycle() → send_summary() → send_details()
    
    Uso:
        manager = SmartNotificationManager(telegram_client, config)
        
        # Durante análisis
        manager.add_signal(signal_data, chart_file)
        manager.add_signal(signal_data2, chart_file2)
        
        # Al final del ciclo
        manager.finalize_cycle()
    """
    
    # Configuración por defecto
    DEFAULT_CONFIG = {
        'summary_enabled': True,
        'detail_min_quality': 'A',  # Mínimo para enviar detalle completo
        'chart_min_quality': 'A',   # Mínimo para enviar con chart
        'delay_between_details': 3.0,  # Segundos entre detalles
        'delay_after_summary': 2.0,    # Segundos después del resumen
        # [A] Gate global
        'market_scan_mode': True,      # Si all C + bearish → solo summary
        # [C] Límite señales C
        'max_c_signals': 5,            # Máximo señales C en summary
        'sort_by_score': True,         # Ordenar por score descendente
    }
    
    # Orden de calidades para comparación
    QUALITY_ORDER = {'A+': 4, 'A': 3, 'B': 2, 'C': 1}
    
    def __init__(self, config: Dict = None):
        """
        Inicializa el manager.
        
        Args:
            config: settings.notifications del config.yml
        
        Warning:
            Si config es None, usa valores por defecto.
        """
        self.logger = structlog.get_logger()
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
        # Estado del ciclo actual
        self.current_cycle: List[Dict[str, Any]] = []
        self.summaries: List[SignalSummary] = []
        self.btc_context: Dict = {}
        
        self.logger.info(f"[SMART] Manager initialized: min_detail={self.config['detail_min_quality']}")
    
    def set_market_context(self, btc_trend: str, btc_change: float, sentiment: str):
        """
        Establece contexto de mercado para el ciclo.
        
        Args:
            btc_trend: bullish/bearish/neutral
            btc_change: Cambio % 24h de BTC
            sentiment: risk_on/risk_off/neutral
        
        Note:
            Llamar antes de add_signal() para incluir en resumen.
        """
        self.btc_context = {
            'trend': btc_trend,
            'change': btc_change,
            'sentiment': sentiment
        }
        self.logger.debug(f"[SMART] Context set: BTC {btc_trend} ({btc_change}%)")
    
    def add_signal(
        self, 
        message_data: Dict[str, Any], 
        chart_file: Optional[str] = None
    ):
        """
        Agrega una señal al ciclo actual.
        
        Args:
            message_data: Dict con todos los campos para el template
                - market: Par de mercado
                - quality: Calidad (A+, A, B, C)
                - score: Score 0-100
                - status: hot/cold
                - indicator: Nombre del indicador
                - values: Dict con valores del indicador
            chart_file: Path al gráfico (si existe)
        
        Direction:
            Los datos llegan desde notifications/core.py → queue → aquí
        """
        symbol = message_data.get('market', 'UNKNOWN')
        quality = message_data.get('quality', 'C')
        score = message_data.get('score', 50.0)
        signal_type = message_data.get('status', 'neutral')
        indicator = message_data.get('indicator', '')
        
        # Extraer RSI si disponible
        values = message_data.get('values', {})
        rsi_value = 0.0
        if isinstance(values, dict) and 'rsi' in values:
            try:
                rsi_value = float(values['rsi'])
            except (ValueError, TypeError):
                pass
        
        # Crear resumen
        summary = SignalSummary(
            symbol=symbol,
            quality=quality,
            score=score,
            signal_type=signal_type,
            indicator=indicator,
            rsi_value=rsi_value,
            btc_trend=self.btc_context.get('trend', 'neutral')
        )
        self.summaries.append(summary)
        
        # Guardar datos completos para detalles
        self.current_cycle.append({
            'message_data': message_data,
            'chart_file': chart_file,
            'summary': summary
        })
        
        self.logger.debug(f"[SMART] Signal added: {symbol} {quality} (score={score:.0f})")
    
    def _should_send_detail(self, quality: str) -> bool:
        """
        Determina si una señal merece detalle completo.
        
        Args:
            quality: Calidad de la señal
            
        Returns:
            True si la calidad >= config.detail_min_quality
        """
        min_q = self.config['detail_min_quality']
        return self.QUALITY_ORDER.get(quality, 0) >= self.QUALITY_ORDER.get(min_q, 3)
    
    def _should_send_chart(self, quality: str) -> bool:
        """
        Determina si una señal merece chart adjunto.
        
        Args:
            quality: Calidad de la señal
            
        Returns:
            True si la calidad >= config.chart_min_quality
        """
        min_q = self.config['chart_min_quality']
        return self.QUALITY_ORDER.get(quality, 0) >= self.QUALITY_ORDER.get(min_q, 3)
    
    def build_summary_message(self) -> str:
        """
        Construye el mensaje de resumen consolidado.
        
        Returns:
            Mensaje HTML listo para Telegram
        
        Format:
            🔔 <b>5 señales detectadas</b>
            
            🔴 BTC Bajista (-2.5%)
            
            ⭐⭐ A  SUI/USDT   RSI 25  🟢
            ⭐   B  ENA/USDT   RSI 22  🟢
            ...
        """
        if not self.summaries:
            return ""
        
        # Ordenar por score descendente
        sorted_signals = sorted(self.summaries, key=lambda x: x.score, reverse=True)
        
        # ─────────────────────────────────────────
        # [C] Aplicar límite de señales C
        # ─────────────────────────────────────────
        max_c = self.config.get('max_c_signals', 5)
        high_quality = [s for s in sorted_signals if s.quality in ['A+', 'A', 'B']]
        low_quality = [s for s in sorted_signals if s.quality == 'C']
        
        # Limitar señales C
        limited_c = low_quality[:max_c]
        truncated_count = len(low_quality) - len(limited_c)
        
        # Combinar (alta calidad primero, luego C limitadas)
        display_signals = high_quality + limited_c
        
        lines = []
        
        # Header
        total_count = len(sorted_signals)
        lines.append(f"🔔 <b>{total_count} señales detectadas</b>")
        lines.append("")
        
        # Contexto BTC
        if self.btc_context:
            trend = self.btc_context.get('trend', 'neutral')
            change = self.btc_context.get('change', 0)
            
            if trend == 'bullish':
                lines.append(f"🟢 BTC Alcista (+{change:.1f}%)")
            elif trend == 'bearish':
                lines.append(f"🔴 BTC Bajista ({change:.1f}%)")
            else:
                lines.append("⚪ BTC Neutral")
            lines.append("")
        
        # Lista de señales (limitada)
        for sig in display_signals:
            # Estrellas de calidad
            stars = "⭐⭐⭐" if sig.quality == 'A+' else "⭐⭐" if sig.quality == 'A' else "⭐" if sig.quality == 'B' else ""
            
            # Emoji de dirección
            direction = "🟢" if sig.signal_type == 'hot' else "🔴"
            
            # RSI formateado
            rsi_str = f"RSI {sig.rsi_value:.0f}" if sig.rsi_value > 0 else sig.indicator[:8]
            
            # Línea formateada
            line = f"{stars:6} {sig.quality}  {sig.symbol:12} {rsi_str:8} {direction}"
            lines.append(line)
        
        # Indicar si se truncaron señales
        if truncated_count > 0:
            lines.append(f"<i>... y {truncated_count} señales C más (score bajo)</i>")
        
        lines.append("")
        lines.append(f"<i>Detalles enviados para A+ y A</i>")
        
        return "\n".join(lines)
    
    def finalize_cycle(self, send_func, send_chart_func) -> Dict[str, int]:
        """
        Finaliza el ciclo y envía notificaciones.
        
        Args:
            send_func: Función para enviar mensaje de texto
                       signature: (message: str) -> None
            send_chart_func: Función para enviar mensaje con chart
                             signature: (chart_path: str, message: str) -> None
        
        Returns:
            Dict con estadísticas: {'summary': 1, 'details': 2, 'charts': 1}
        
        Flow:
            1. Enviar resumen consolidado (sin esperar)
            2. Esperar delay_after_summary
            3. Para cada señal A+/A:
               a. Si hay chart y calidad >= chart_min: enviar con chart
               b. Sino: enviar solo texto
               c. Esperar delay_between_details
        
        Warning:
            Esta función es bloqueante y puede tomar varios segundos.
        """
        stats = {'summary': 0, 'details': 0, 'charts': 0}
        
        if not self.summaries:
            self.logger.info("[SMART] No signals in cycle, skipping")
            return stats
        
        # 1. Enviar resumen
        if self.config['summary_enabled']:
            summary_msg = self.build_summary_message()
            if summary_msg:
                try:
                    send_func(summary_msg)
                    stats['summary'] = 1
                    self.logger.info(f"[SMART] Summary sent: {len(self.summaries)} signals")
                except Exception as e:
                    self.logger.error(f"[SMART] Error sending summary: {e}")
        
        # 2. Esperar antes de detalles
        time.sleep(self.config['delay_after_summary'])
        
        # 3. Enviar detalles para A+ y A
        for item in self.current_cycle:
            summary = item['summary']
            
            if not self._should_send_detail(summary.quality):
                continue
            
            message_data = item['message_data']
            chart_file = item['chart_file']
            
            try:
                # ¿Enviar con chart?
                if chart_file and self._should_send_chart(summary.quality):
                    send_chart_func(chart_file, message_data)
                    stats['charts'] += 1
                else:
                    # Solo texto sin chart
                    send_func(message_data)
                
                stats['details'] += 1
                self.logger.info(f"[SMART] Detail sent: {summary.symbol} ({summary.quality})")
                
            except Exception as e:
                self.logger.error(f"[SMART] Error sending detail {summary.symbol}: {e}")
            
            # Delay entre detalles
            time.sleep(self.config['delay_between_details'])
        
        # Limpiar ciclo
        self.clear_cycle()
        
        self.logger.info(f"[SMART] Cycle complete: {stats}")
        return stats
    
    def clear_cycle(self):
        """
        Limpia el estado del ciclo actual.
        
        Note:
            Llamar automáticamente por finalize_cycle() o manualmente si es necesario.
        """
        self.current_cycle = []
        self.summaries = []
        self.btc_context = {}
    
    def get_cycle_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas del ciclo actual.
        
        Returns:
            Dict con count, quality_distribution, top_signal
        """
        if not self.summaries:
            return {'count': 0}
        
        dist = {'A+': 0, 'A': 0, 'B': 0, 'C': 0}
        for s in self.summaries:
            if s.quality in dist:
                dist[s.quality] += 1
        
        top = max(self.summaries, key=lambda x: x.score)
        
        return {
            'count': len(self.summaries),
            'distribution': dist,
            'top': f"{top.symbol} ({top.quality}, score={top.score:.0f})",
            'high_quality_count': dist['A+'] + dist['A']
        }
