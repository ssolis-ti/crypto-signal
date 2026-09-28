"""
API REST de solo lectura para integracion con agentes/IA (specs/009-agent-api/).

Expone el estado que el bot ya calcula cada ciclo (contexto de mercado, señales
enriquecidas con su score, snapshot de indicadores, salud de workers) via HTTP,
para que un agente pueda consultarlo en vez de parsear logs de texto.

Solo lectura -- no agrega ninguna accion nueva sobre el exchange ni los notificadores
(Principio I). Pensada para exponerse solo en localhost (ver docker-compose.yml:
127.0.0.1:8090:8090), sin autenticacion.
"""
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

from api.store import AgentStateStore


class SignalOut(BaseModel):
    id: int
    created_at: str
    exchange: str
    symbol: str
    signal_type: str
    indicator: str
    quality: str
    confidence: int
    score: float
    recommendation: str
    context_note: Optional[str] = None
    btc_trend: Optional[str] = None
    btc_change_24h: Optional[float] = None
    relative_strength: Optional[float] = None
    divergence: Optional[str] = None
    market_sentiment: Optional[str] = None
    rsi_slope: Optional[float] = None
    macd_acceleration: Optional[float] = None
    vwap_distance: Optional[float] = None
    momentum_divergence: Optional[str] = None
    should_notify: bool


class MarketContextOut(BaseModel):
    id: int
    created_at: str
    exchange: str
    btc_trend: Optional[str] = None
    btc_change_24h: Optional[float] = None
    btc_change_1h: Optional[float] = None
    market_sentiment: Optional[str] = None
    total_gainers: Optional[int] = None
    total_losers: Optional[int] = None
    dominance_ratio: Optional[float] = None


class IndicatorSnapshotOut(BaseModel):
    exchange: str
    symbol: str
    candle_period: str
    indicator_type: str
    indicator_name: str
    values: Dict[str, Any]
    updated_at: str


class WorkerStatusOut(BaseModel):
    worker_name: str
    pairs: List[str]
    cycle_count: int
    last_cycle_at: Optional[str] = None
    last_error: Optional[str] = None
    updated_at: str


class StatusOut(BaseModel):
    workers: List[WorkerStatusOut]


class ConfigOut(BaseModel):
    settings: Dict[str, Any]
    indicators: Dict[str, Any]
    informants: Dict[str, Any]
    crossovers: Dict[str, Any]
    enabled_notifiers: List[str]
    enabled_exchanges: List[str]


def create_app(store: AgentStateStore, config_provider) -> FastAPI:
    """
    Crea la app FastAPI.

    Args:
        store: AgentStateStore ya inicializado (schema creado).
        config_provider: callable sin argumentos que retorna
            Configuration.to_sanitized_dict() -- se llama en cada request a /config,
            no una vez al arrancar, para reflejar la config vigente.
    """
    app = FastAPI(
        title="crypto-signal Agent API",
        description=(
            "API de solo lectura para que un agente/IA consulte el estado del bot: "
            "contexto de mercado, señales con su score, snapshot de indicadores y "
            "salud operativa. Ver /docs para el detalle de cada endpoint."
        ),
        version="1.0.0",
    )

    @app.get("/health", summary="Liveness check")
    def health() -> Dict[str, str]:
        """Confirma que el proceso de la API esta vivo (no depende de los workers)."""
        return {"status": "ok"}

    @app.get("/status", response_model=StatusOut, summary="Estado operativo de cada worker")
    def status() -> StatusOut:
        """Pares cubiertos, ciclos completados, ultimo ciclo y ultimo error por worker."""
        return StatusOut(workers=store.get_worker_status())

    @app.get(
        "/market-context",
        response_model=List[MarketContextOut],
        summary="Contexto de mercado (BTC trend, sentiment, gainers/losers)",
    )
    def market_context(
        exchange: Optional[str] = Query(None, description="Filtrar por exchange, ej. 'binance'"),
        history: int = Query(1, ge=1, le=500, description="Cantidad de snapshots recientes"),
    ) -> List[Dict[str, Any]]:
        """Ultimo(s) snapshot(s) de contexto de mercado, mas reciente primero."""
        return store.get_market_context(exchange=exchange, limit=history)

    @app.get(
        "/signals/recent",
        response_model=List[SignalOut],
        summary="Historial de señales con su score/quality breakdown",
    )
    def signals_recent(
        limit: int = Query(50, ge=1, le=1000),
        pair: Optional[str] = Query(None, description="Filtrar por symbol, ej. 'BTC/USDT'"),
        quality: Optional[str] = Query(None, description="Filtrar por calidad: A+, A, B, C"),
        signal_type: Optional[str] = Query(None, description="Filtrar por 'hot' o 'cold'"),
    ) -> List[Dict[str, Any]]:
        """Señales mas recientes primero, con el desglose completo de SignalEnhancer."""
        return store.get_recent_signals(
            limit=limit, symbol=pair, quality=quality, signal_type=signal_type
        )

    @app.get(
        "/indicators",
        response_model=List[IndicatorSnapshotOut],
        summary="Ultimo valor conocido de cada indicador/informante por par",
    )
    def indicators(
        pair: Optional[str] = Query(None, description="Filtrar por symbol, ej. 'BTC/USDT'"),
        exchange: Optional[str] = Query(None, description="Filtrar por exchange"),
    ) -> List[Dict[str, Any]]:
        """Snapshot actual (no historico) de todos los indicadores/informantes calculados."""
        return store.get_indicator_snapshots(symbol=pair, exchange=exchange)

    @app.get(
        "/config",
        response_model=ConfigOut,
        summary="Configuracion activa del bot (sin secretos)",
    )
    def config() -> Dict[str, Any]:
        """
        Settings/indicadores/informantes/crossovers vigentes, y que notificadores/
        exchanges estan habilitados. Nunca incluye tokens, chat_id, ni credenciales de
        webhook -- ver Configuration.to_sanitized_dict().
        """
        return config_provider()

    return app
