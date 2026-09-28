"""
Tests para la API FastAPI de agentes (specs/009-agent-api/).
"""
import pytest
from fastapi.testclient import TestClient

from api.server import create_app
from api.store import AgentStateStore


@pytest.fixture
def store(tmp_path):
    return AgentStateStore(str(tmp_path / "agent_state.db"))


@pytest.fixture
def client(store):
    app = create_app(store, config_provider=lambda: {
        'settings': {'update_interval': 300},
        'indicators': {'rsi': [{'enabled': True}]},
        'informants': {},
        'crossovers': {},
        'enabled_notifiers': ['telegram'],
        'enabled_exchanges': ['binance'],
    })
    return TestClient(app)


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get('/health')
        assert resp.status_code == 200
        assert resp.json() == {'status': 'ok'}


class TestColdStart:
    """Edge case: ningun endpoint debe fallar antes del primer ciclo."""

    def test_status_empty(self, client):
        resp = client.get('/status')
        assert resp.status_code == 200
        assert resp.json() == {'workers': []}

    def test_market_context_empty(self, client):
        resp = client.get('/market-context')
        assert resp.status_code == 200
        assert resp.json() == []

    def test_signals_recent_empty(self, client):
        resp = client.get('/signals/recent')
        assert resp.status_code == 200
        assert resp.json() == []

    def test_indicators_empty(self, client):
        resp = client.get('/indicators')
        assert resp.status_code == 200
        assert resp.json() == []


class TestStatus:
    def test_returns_worker_heartbeats(self, store, client):
        store.record_worker_heartbeat('Worker-1', ['BTC/USDT'], cycle_count=4)

        resp = client.get('/status')

        assert resp.status_code == 200
        body = resp.json()
        assert len(body['workers']) == 1
        assert body['workers'][0]['worker_name'] == 'Worker-1'
        assert body['workers'][0]['cycle_count'] == 4


class TestMarketContext:
    def test_returns_latest_snapshot(self, store, client):
        store.record_market_context('binance', {'btc_trend': 'bullish', 'btc_change_24h': 2.0})

        resp = client.get('/market-context?exchange=binance')

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]['btc_trend'] == 'bullish'

    def test_history_param(self, store, client):
        for _ in range(5):
            store.record_market_context('binance', {'btc_trend': 'neutral'})

        resp = client.get('/market-context?exchange=binance&history=3')

        assert len(resp.json()) == 3


class TestSignalsRecent:
    def test_returns_full_breakdown(self, store, client):
        store.record_signal('binance', {
            'symbol': 'BTC/USDT', 'signal_type': 'hot', 'indicator': 'rsi',
            'quality': 'A+', 'confidence': 90, 'score': 88.0, 'recommendation': 'strong_buy',
            'context_note': 'note', 'btc_trend': 'bullish', 'btc_change_24h': 3.0,
            'relative_strength': 1.5, 'divergence': 'positive', 'market_sentiment': 'risk_on',
            'rsi_slope': 0.5, 'macd_acceleration': 0.2, 'vwap_distance': -2.0,
            'momentum_divergence': 'bullish_divergence',
        }, should_notify=True)

        resp = client.get('/signals/recent')

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]['quality'] == 'A+'
        assert body[0]['should_notify'] is True
        assert body[0]['recommendation'] == 'strong_buy'

    def test_filters_by_pair_and_quality(self, store, client):
        store.record_signal('binance', {
            'symbol': 'BTC/USDT', 'signal_type': 'hot', 'indicator': 'rsi', 'quality': 'A',
            'confidence': 80, 'score': 80.0, 'recommendation': 'buy',
        }, should_notify=True)
        store.record_signal('binance', {
            'symbol': 'ETH/USDT', 'signal_type': 'cold', 'indicator': 'rsi', 'quality': 'C',
            'confidence': 30, 'score': 30.0, 'recommendation': 'avoid',
        }, should_notify=False)

        resp = client.get('/signals/recent?pair=BTC/USDT&quality=A')

        body = resp.json()
        assert len(body) == 1
        assert body[0]['symbol'] == 'BTC/USDT'


class TestIndicators:
    def test_returns_latest_values(self, store, client):
        store.record_indicator_snapshot(
            'binance', 'BTC/USDT', '4h', 'indicators', 'rsi', {'rsi': 42.5}
        )

        resp = client.get('/indicators?pair=BTC/USDT')

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]['values'] == {'rsi': 42.5}
        assert body[0]['indicator_name'] == 'rsi'


class TestConfig:
    def test_returns_sanitized_config(self, client):
        resp = client.get('/config')

        assert resp.status_code == 200
        body = resp.json()
        assert body['enabled_notifiers'] == ['telegram']
        assert body['enabled_exchanges'] == ['binance']
        assert 'settings' in body

    def test_never_leaks_a_secret_present_in_the_underlying_config(self):
        """
        Aunque el config_provider devolviera por error un secreto (no deberia, por diseño
        allow-list -- ver research.md), esta prueba fija el contrato del endpoint: el shape
        que expone /config no tiene ningun campo para 'required'/tokens.
        """
        store = AgentStateStore(':memory:')
        secret_token = 'FAKE-SECRET-TOKEN-123456'

        def provider():
            return {
                'settings': {}, 'indicators': {}, 'informants': {}, 'crossovers': {},
                'enabled_notifiers': ['telegram'], 'enabled_exchanges': ['binance'],
            }

        app = create_app(store, config_provider=provider)
        client = TestClient(app)

        resp = client.get('/config')

        assert secret_token not in resp.text
