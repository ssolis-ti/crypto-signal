"""AgentStateStore es best-effort, pero un error de SQLite no debe pasar en silencio."""
import sqlite3
from unittest.mock import patch

from api.store import AgentStateStore


def test_write_error_is_logged_not_swallowed_silently(tmp_path):
    store = AgentStateStore(str(tmp_path / 's.db'))
    with patch('api.store._log_db_error') as log, \
         patch.object(store, '_connect', side_effect=sqlite3.OperationalError('database is locked')):
        store.record_market_context('binance', {'btc_trend': 'up'})
    assert log.call_count == 1
    assert log.call_args.args[0] == 'escritura'


def test_read_error_returns_empty_and_logs(tmp_path):
    store = AgentStateStore(str(tmp_path / 's.db'))
    with patch('api.store._log_db_error') as log, \
         patch.object(store, '_connect', side_effect=sqlite3.OperationalError('disk I/O error')):
        assert store.get_recent_signals() == []
    assert log.called
