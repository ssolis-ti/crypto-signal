"""
Tests adversariales para Area 4:
- app/app.py (AnalysisWorker, loop, manejo de excepciones y sleeps seguros)
- app/api/store.py (concurrencia basica, DB bloqueada, timeouts, inputs degenerados)
- app/api/server.py (endpoints con parametros invalidos, limites extremos)
"""
import os
import sqlite3
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import importlib.util

from api.store import AgentStateStore
from api.server import create_app

# Cargar AnalysisWorker desde app/app.py
spec = importlib.util.spec_from_file_location("app_main", os.path.join(os.path.dirname(__file__), "..", "..", "app", "app.py"))
app_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_main)
AnalysisWorker = app_main.AnalysisWorker


class TestAnalysisWorkerAdversarial:
    """Pruebas sobre AnalysisWorker y robustez del ciclo/sleeps."""

    def test_worker_safe_sleep_with_string_interval(self):
        class BreakLoop(BaseException):
            pass

        behaviour = MagicMock()
        notifier = MagicMock()
        logger = MagicMock()
        settings = {
            "update_interval": "1",  # string en vez de int
            "output_mode": "cli",
        }
        worker = AnalysisWorker("TestWorker", behaviour, notifier, {}, settings, logger)

        # Simular una iteracion del loop
        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = BreakLoop
            try:
                worker.run()
            except BreakLoop:
                pass

            # Debe haber dormido con un float/int valido, no string
            mock_sleep.assert_called_once_with(1.0)
            behaviour.run.assert_called_once()

    def test_worker_missing_output_mode_uses_default(self):
        behaviour = MagicMock()
        notifier = MagicMock()
        logger = MagicMock()
        settings = {"update_interval": 1}  # Sin output_mode
        worker = AnalysisWorker("TestWorker", behaviour, notifier, {}, settings, logger)

        with patch("time.sleep", side_effect=StopIteration):
            try:
                worker.run()
            except StopIteration:
                pass

            behaviour.run.assert_called_once_with({}, "cli")


class TestAgentStateStoreAdversarial:
    """Pruebas sobre AgentStateStore, concurrencia y DB bloqueada."""

    @pytest.fixture
    def temp_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_state.db")
            store = AgentStateStore(db_path)
            yield store

    def test_concurrent_writes_and_reads(self, temp_store):
        """Multiples hilos escribiendo y leyendo concurrentemente no deben corromper la DB."""
        errors = []

        def writer(worker_id):
            try:
                for i in range(20):
                    temp_store.record_signal(
                        "binance",
                        {
                            "symbol": f"COIN{worker_id}/USDT",
                            "signal_type": "hot",
                            "indicator": "rsi",
                            "score": 75.0,
                        },
                        should_notify=True,
                    )
                    temp_store.record_worker_heartbeat(f"Worker-{worker_id}", ["BTC/USDT"], i)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(20):
                    temp_store.get_recent_signals(limit=10)
                    temp_store.get_worker_status()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        threads += [threading.Thread(target=reader) for _ in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        signals = temp_store.get_recent_signals(limit=100)
        assert len(signals) == 80  # 4 writers * 20 records

    def test_database_locked_handling(self, temp_store):
        """Si la DB esta bloqueada por una conexion exclusiva externa, no debe crashear."""
        # Abrir conexion que bloquea
        conn_locker = sqlite3.connect(temp_store.db_path, timeout=0.1)
        conn_locker.execute("BEGIN EXCLUSIVE")

        # Intentar leer desde el store cuando esta bloqueada
        with patch.object(temp_store, "_connect") as mock_conn:
            # Simular un OperationalError: database is locked
            mock_conn.side_effect = sqlite3.OperationalError("database is locked")
            # get_recent_signals debe degradar devolviendo []
            res = temp_store.get_recent_signals()
            assert res == []

            # get_market_context debe degradar devolviendo []
            res_ctx = temp_store.get_market_context()
            assert res_ctx == []

            # record_signal no debe explotar al caller
            temp_store.record_signal("binance", {"symbol": "BTC/USDT"}, should_notify=False)

        conn_locker.rollback()
        conn_locker.close()


class TestAgentServerAdversarial:
    """Pruebas sobre endpoints de FastAPI en server.py."""

    @pytest.fixture
    def client(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_api.db")
            store = AgentStateStore(db_path)
            config_dict = {
                "settings": {"timezone": "UTC"},
                "indicators": {},
                "informants": {},
                "crossovers": {},
                "enabled_notifiers": ["telegram"],
                "enabled_exchanges": ["binance"],
            }
            app = create_app(store, lambda: config_dict)
            yield TestClient(app), store

    def test_signals_recent_invalid_parameters(self, client):
        tc, store = client
        # Limite invalido (fuera de rango)
        res = tc.get("/signals/recent?limit=0")
        assert res.status_code == 422  # Validation error de FastAPI

        res = tc.get("/signals/recent?limit=5000")
        assert res.status_code == 422

        # Filtro inexistente devuelve lista vacia
        res = tc.get("/signals/recent?pair=NONEXISTENT/USDT&quality=Z&signal_type=unknown")
        assert res.status_code == 200
        assert res.json() == []

    def test_market_context_invalid_history(self, client):
        tc, store = client
        res = tc.get("/market-context?history=0")
        assert res.status_code == 422

        res = tc.get("/market-context?history=1000")
        assert res.status_code == 422

        res = tc.get("/market-context?exchange=unknown_exchange")
        assert res.status_code == 200
        assert res.json() == []

    def test_indicators_empty_response(self, client):
        tc, store = client
        res = tc.get("/indicators?pair=FOO/BAR&exchange=binance")
        assert res.status_code == 200
        assert res.json() == []

    def test_config_endpoint_returns_sanitized_config(self, client):
        tc, store = client
        res = tc.get("/config")
        assert res.status_code == 200
        data = res.json()
        assert "settings" in data
        assert "enabled_notifiers" in data
        # Asegurar que nunca se expongan tokens ni credenciales
        assert "token" not in str(data)
        assert "chat_id" not in str(data)
