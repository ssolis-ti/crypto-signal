"""
AgentStateStore - Persistencia de estado para integracion con agentes/IA
==========================================================================
Guarda, de forma duradera (SQLite), lo que el bot ya calcula cada ciclo pero hoy se
descarta despues de loguearlo: contexto de mercado, señales enriquecidas con su
score/quality, snapshot de indicadores por par, y salud de cada worker.

No agrega ninguna decision nueva -- solo persiste valores que Behaviour ya produce,
para que app/api/server.py (o cualquier otro consumidor) pueda consultarlos.

Ver specs/009-agent-api/data-model.md para el esquema completo.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

_logger = structlog.get_logger()


def _log_db_error(operation: str, error: Exception) -> None:
    """La API de agentes es best-effort (nunca debe romper el bot), pero un fallo no debe pasar en silencio."""
    _logger.error(f"[STORE] Error de SQLite en {operation}: {error}")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    indicator TEXT NOT NULL,
    quality TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    score REAL NOT NULL,
    recommendation TEXT NOT NULL,
    context_note TEXT,
    btc_trend TEXT,
    btc_change_24h REAL,
    relative_strength REAL,
    divergence TEXT,
    market_sentiment TEXT,
    rsi_slope REAL,
    macd_acceleration REAL,
    vwap_distance REAL,
    momentum_divergence TEXT,
    should_notify INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_created ON signals(symbol, created_at);
CREATE INDEX IF NOT EXISTS idx_signals_quality_created ON signals(quality, created_at);

CREATE TABLE IF NOT EXISTS market_context_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    exchange TEXT NOT NULL,
    btc_trend TEXT,
    btc_change_24h REAL,
    btc_change_1h REAL,
    market_sentiment TEXT,
    total_gainers INTEGER,
    total_losers INTEGER,
    dominance_ratio REAL
);
CREATE INDEX IF NOT EXISTS idx_context_exchange_created
    ON market_context_snapshots(exchange, created_at);

CREATE TABLE IF NOT EXISTS indicator_snapshots (
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    candle_period TEXT NOT NULL,
    indicator_type TEXT NOT NULL,
    indicator_name TEXT NOT NULL,
    values_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (exchange, symbol, candle_period, indicator_type, indicator_name)
);

CREATE TABLE IF NOT EXISTS worker_status (
    worker_name TEXT PRIMARY KEY,
    pairs_json TEXT NOT NULL,
    cycle_count INTEGER NOT NULL,
    last_cycle_at TEXT,
    last_error TEXT,
    updated_at TEXT NOT NULL
);
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentStateStore:
    """
    Almacen SQLite thread-safe para el estado que un agente/IA puede consultar.

    Cada escritura abre una conexion de corta vida bajo un lock global -- la
    frecuencia de escritura (una tanda por worker por ciclo, cada varios minutos)
    hace innecesario un pool de conexiones o modo WAL (ver specs/009-agent-api/research.md).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000")
        except sqlite3.Error as e:
            _log_db_error('busy_timeout', e)
        return conn

    # ─────────────────────────────────────────
    # Escritura
    # ─────────────────────────────────────────

    def record_signal(
        self,
        exchange: str,
        signal: Dict[str, Any],
        should_notify: bool,
        created_at: Optional[str] = None,
    ) -> None:
        row = (
            created_at or _utc_now_iso(),
            exchange,
            signal.get('symbol', ''),
            signal.get('signal_type', 'neutral'),
            signal.get('indicator', ''),
            signal.get('quality', 'B'),
            int(signal.get('confidence', 50)),
            float(signal.get('score', 50.0)),
            signal.get('recommendation', 'hold'),
            signal.get('context_note', ''),
            signal.get('btc_trend', 'neutral'),
            signal.get('btc_change_24h', 0.0),
            signal.get('relative_strength', 1.0),
            signal.get('divergence', 'neutral'),
            signal.get('market_sentiment', 'neutral'),
            signal.get('rsi_slope', 0.0),
            signal.get('macd_acceleration', 0.0),
            signal.get('vwap_distance', 0.0),
            signal.get('momentum_divergence', 'none'),
            1 if should_notify else 0,
        )
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """INSERT INTO signals (
                        created_at, exchange, symbol, signal_type, indicator, quality,
                        confidence, score, recommendation, context_note, btc_trend,
                        btc_change_24h, relative_strength, divergence, market_sentiment,
                        rsi_slope, macd_acceleration, vwap_distance, momentum_divergence,
                        should_notify
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    row,
                )
        except sqlite3.Error as e:
            _log_db_error('escritura', e)

    def record_market_context(
        self, exchange: str, context: Dict[str, Any], created_at: Optional[str] = None
    ) -> None:
        row = (
            created_at or _utc_now_iso(),
            exchange,
            context.get('btc_trend', 'neutral'),
            context.get('btc_change_24h', 0.0),
            context.get('btc_change_1h', 0.0),
            context.get('market_sentiment', 'neutral'),
            context.get('total_gainers', 0),
            context.get('total_losers', 0),
            context.get('dominance_ratio', 1.0),
        )
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """INSERT INTO market_context_snapshots (
                        created_at, exchange, btc_trend, btc_change_24h, btc_change_1h,
                        market_sentiment, total_gainers, total_losers, dominance_ratio
                    ) VALUES (?,?,?,?,?,?,?,?,?)""",
                    row,
                )
        except sqlite3.Error as e:
            _log_db_error('escritura', e)

    def record_indicator_snapshot(
        self,
        exchange: str,
        symbol: str,
        candle_period: str,
        indicator_type: str,
        indicator_name: str,
        values: Dict[str, Any],
        updated_at: Optional[str] = None,
    ) -> None:
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """INSERT INTO indicator_snapshots (
                        exchange, symbol, candle_period, indicator_type, indicator_name,
                        values_json, updated_at
                    ) VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(exchange, symbol, candle_period, indicator_type, indicator_name)
                    DO UPDATE SET values_json=excluded.values_json, updated_at=excluded.updated_at""",
                    (
                        exchange, symbol, candle_period, indicator_type, indicator_name,
                        json.dumps(values), updated_at or _utc_now_iso(),
                    ),
                )
        except sqlite3.Error as e:
            _log_db_error('escritura', e)

    def record_worker_heartbeat(
        self,
        worker_name: str,
        pairs: List[str],
        cycle_count: int,
        last_error: Optional[str] = None,
        last_cycle_at: Optional[str] = None,
    ) -> None:
        now = _utc_now_iso()
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """INSERT INTO worker_status (
                        worker_name, pairs_json, cycle_count, last_cycle_at, last_error, updated_at
                    ) VALUES (?,?,?,?,?,?)
                    ON CONFLICT(worker_name) DO UPDATE SET
                        pairs_json=excluded.pairs_json,
                        cycle_count=excluded.cycle_count,
                        last_cycle_at=excluded.last_cycle_at,
                        last_error=excluded.last_error,
                        updated_at=excluded.updated_at""",
                    (worker_name, json.dumps(pairs), cycle_count, last_cycle_at or now, last_error, now),
                )
        except sqlite3.Error as e:
            _log_db_error('escritura', e)

    # ─────────────────────────────────────────
    # Lectura
    # ─────────────────────────────────────────

    def get_recent_signals(
        self,
        limit: int = 50,
        symbol: Optional[str] = None,
        quality: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        query = "SELECT * FROM signals WHERE 1=1"
        params: List[Any] = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if quality:
            query += " AND quality = ?"
            params.append(quality)
        if signal_type:
            query += " AND signal_type = ?"
            params.append(signal_type)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        try:
            with self._connect() as conn:
                rows = conn.execute(query, params).fetchall()
            return [dict(r) | {'should_notify': bool(r['should_notify'])} for r in rows]
        except sqlite3.Error as e:
            _log_db_error('lectura', e)
            return []

    def get_market_context(
        self, exchange: Optional[str] = None, limit: int = 1
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 500))
        query = "SELECT * FROM market_context_snapshots WHERE 1=1"
        params: List[Any] = []
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        try:
            with self._connect() as conn:
                rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            _log_db_error('lectura', e)
            return []

    def get_indicator_snapshots(
        self, symbol: Optional[str] = None, exchange: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM indicator_snapshots WHERE 1=1"
        params: List[Any] = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange)
        query += " ORDER BY symbol, indicator_type, indicator_name"

        try:
            with self._connect() as conn:
                rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d['values'] = json.loads(d.pop('values_json'))
                results.append(d)
            return results
        except sqlite3.Error as e:
            _log_db_error('lectura', e)
            return []

    def get_worker_status(self) -> List[Dict[str, Any]]:
        try:
            with self._connect() as conn:
                rows = conn.execute("SELECT * FROM worker_status ORDER BY worker_name").fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d['pairs'] = json.loads(d.pop('pairs_json'))
                results.append(d)
            return results
        except sqlite3.Error as e:
            _log_db_error('lectura', e)
            return []
