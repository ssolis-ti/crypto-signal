"""
Calibration Logger - Logs Detallados para Depuración
=====================================================
Módulo para logging de calibración de datos CCXT y análisis técnico.

Uso:
    from utils.calibration import CalibrationLogger
    
    calib = CalibrationLogger()
    calib.log_ohlcv(symbol, ohlcv_data)
    calib.log_indicator('RSI', rsi_values)
    calib.validate_ranges(indicator_name, values)
"""

import structlog
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime


class CalibrationLogger:
    """
    Logger especializado para calibración y debugging.
    
    Proporciona:
        - Logs de datos OHLCV crudos
        - Validación de rangos de indicadores
        - Comparación con valores esperados
        - Alertas de anomalías
    """
    
    # Rangos válidos para indicadores comunes
    VALID_RANGES = {
        'rsi': (0, 100),
        'lrsi': (0, 1),
        'stoch_rsi': (0, 100),
        'mfi': (0, 100),
        'macd': (-float('inf'), float('inf')),  # Sin límite
        'macd_signal': (-float('inf'), float('inf')),
        'ema': (0, float('inf')),  # Debe ser positivo
        'sma': (0, float('inf')),
        'bollinger_upper': (0, float('inf')),
        'bollinger_lower': (0, float('inf')),
        'volume': (0, float('inf')),
        'price': (0, float('inf')),
    }
    
    def __init__(self, enabled: bool = True, verbose: bool = False):
        """
        Args:
            enabled: Si False, no genera logs
            verbose: Si True, logs más detallados
        """
        self.logger = structlog.get_logger()
        self.enabled = enabled
        self.verbose = verbose
        self.anomalies = []
    
    def log_ohlcv(self, symbol: str, ohlcv: List[List], last_n: int = 5) -> None:
        """
        Logea datos OHLCV crudos.
        
        Args:
            symbol: Par de mercado
            ohlcv: Lista de velas [[timestamp, o, h, l, c, v], ...]
            last_n: Cuántas velas mostrar
        """
        if not self.enabled:
            return
        
        if not ohlcv or len(ohlcv) == 0:
            self.logger.warning(f"[CALIB] {symbol}: OHLCV vacío!")
            return
        
        total = len(ohlcv)
        last_candles = ohlcv[-last_n:]
        
        self.logger.info(f"[CALIB] {symbol}: {total} velas disponibles")
        
        for candle in last_candles:
            if len(candle) >= 6:
                ts, o, h, l, c, v = candle[:6]
                time_str = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M')
                self.logger.info(
                    f"[CALIB] {symbol} | {time_str} | "
                    f"O:{o:.4f} H:{h:.4f} L:{l:.4f} C:{c:.4f} V:{v:.0f}"
                )
                
                # Validar sanidad de datos
                if h < l:
                    self._report_anomaly(symbol, 'HIGH < LOW', f"{h} < {l}")
                if o < 0 or c < 0:
                    self._report_anomaly(symbol, 'Precio negativo', f"O:{o}, C:{c}")
    
    def log_indicator(
        self, 
        symbol: str, 
        indicator_name: str, 
        values: Any, 
        last_n: int = 5
    ) -> None:
        """
        Logea valores de un indicador.
        
        Args:
            symbol: Par de mercado
            indicator_name: Nombre del indicador (RSI, MACD, etc)
            values: Serie o lista de valores
            last_n: Cuántos valores mostrar
        """
        if not self.enabled:
            return
        
        indicator_lower = indicator_name.lower()
        
        # Convertir a lista si es Series
        if isinstance(values, pd.Series):
            value_list = values.dropna().tolist()
        elif isinstance(values, pd.DataFrame):
            value_list = values.iloc[:, 0].dropna().tolist() if len(values.columns) > 0 else []
        else:
            value_list = list(values) if values else []
        
        if not value_list:
            self.logger.warning(f"[CALIB] {symbol} {indicator_name}: Sin valores!")
            return
        
        # Últimos N valores
        recent = value_list[-last_n:]
        current = value_list[-1] if value_list else None
        
        self.logger.info(
            f"[CALIB] {symbol} {indicator_name}: "
            f"Actual={current:.4f} | Últimos {last_n}: {[f'{v:.4f}' for v in recent]}"
        )
        
        # Validar rango
        self._validate_range(symbol, indicator_lower, current)
    
    def log_signal(
        self, 
        symbol: str, 
        signal_type: str, 
        indicator: str,
        quality: str,
        score: float,
        context: Dict
    ) -> None:
        """
        Logea una señal generada.
        """
        if not self.enabled:
            return
        
        self.logger.info(
            f"[CALIB] SEÑAL {symbol}: {signal_type.upper()} | "
            f"Indicador: {indicator} | Quality: {quality} | Score: {score:.0f}"
        )
        
        if self.verbose:
            self.logger.info(f"[CALIB] Contexto: {context}")
    
    def log_correlation_context(
        self,
        btc_trend: str,
        btc_change: float,
        sentiment: str,
        gainers: int,
        losers: int
    ) -> None:
        """
        Logea el contexto de correlación.
        """
        if not self.enabled:
            return
        
        self.logger.info(
            f"[CALIB] CONTEXTO: BTC {btc_trend} ({btc_change:+.2f}%) | "
            f"Sentiment: {sentiment} | G/L: {gainers}/{losers}"
        )
    
    def log_score_breakdown(
        self,
        symbol: str,
        base_score: float,
        btc_adj: float,
        alt_adj: float,
        sentiment_adj: float,
        rsi_adj: float,
        final_score: float
    ) -> None:
        """
        Logea desglose del cálculo de score.
        """
        if not self.enabled:
            return
        
        self.logger.info(
            f"[CALIB] SCORE {symbol}: "
            f"Base=50 + BTC({btc_adj:+.0f}) + ALT({alt_adj:+.0f}) + "
            f"Sent({sentiment_adj:+.0f}) + RSI({rsi_adj:+.0f}) = {final_score:.0f}"
        )
    
    def _validate_range(self, symbol: str, indicator: str, value: float) -> bool:
        """Valida que un valor esté en rango esperado."""
        if indicator not in self.VALID_RANGES:
            return True
        
        min_val, max_val = self.VALID_RANGES[indicator]
        
        if value < min_val or value > max_val:
            self._report_anomaly(
                symbol, 
                f"{indicator} fuera de rango", 
                f"{value} (esperado: {min_val}-{max_val})"
            )
            return False
        
        return True
    
    def _report_anomaly(self, symbol: str, anomaly_type: str, details: str) -> None:
        """Reporta una anomalía."""
        anomaly = {
            'symbol': symbol,
            'type': anomaly_type,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.anomalies.append(anomaly)
        self.logger.error(f"[CALIB] ⚠️ ANOMALÍA {symbol}: {anomaly_type} - {details}")
    
    def get_anomalies(self) -> List[Dict]:
        """Retorna lista de anomalías detectadas."""
        return self.anomalies
    
    def clear_anomalies(self) -> None:
        """Limpia lista de anomalías."""
        self.anomalies = []


# Instancia global para uso fácil
calibration_logger = CalibrationLogger(enabled=True, verbose=False)
