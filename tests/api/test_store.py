"""
Tests para AgentStateStore (specs/009-agent-api/).
"""
import json

import pytest

from api.store import AgentStateStore


@pytest.fixture
def store(tmp_path):
    return AgentStateStore(str(tmp_path / "agent_state.db"))


def _signal(**overrides):
    base = {
        'symbol': 'BTC/USDT', 'signal_type': 'hot', 'indicator': 'rsi',
        'quality': 'A', 'confidence': 80, 'score': 82.0, 'recommendation': 'buy',
        'context_note': 'BTC alcista', 'btc_trend': 'bullish', 'btc_change_24h': 2.5,
        'relative_strength': 1.2, 'divergence': 'neutral', 'market_sentiment': 'risk_on',
        'rsi_slope': 0.3, 'macd_acceleration': 0.1, 'vwap_distance': -1.5,
        'momentum_divergence': 'none',
    }
    base.update(overrides)
    return base


class TestSignals:
    def test_round_trip(self, store):
        store.record_signal('binance', _signal(), should_notify=True)

        results = store.get_recent_signals(limit=10)

        assert len(results) == 1
        assert results[0]['symbol'] == 'BTC/USDT'
        assert results[0]['quality'] == 'A'
        assert results[0]['should_notify'] is True

    def test_filters_by_symbol(self, store):
        store.record_signal('binance', _signal(symbol='BTC/USDT'), should_notify=True)
        store.record_signal('binance', _signal(symbol='ETH/USDT'), should_notify=True)

        results = store.get_recent_signals(limit=10, symbol='ETH/USDT')

        assert len(results) == 1
        assert results[0]['symbol'] == 'ETH/USDT'

    def test_filters_by_quality_and_signal_type(self, store):
        store.record_signal('binance', _signal(quality='A', signal_type='hot'), should_notify=True)
        store.record_signal('binance', _signal(quality='C', signal_type='cold'), should_notify=False)

        results = store.get_recent_signals(limit=10, quality='A', signal_type='hot')

        assert len(results) == 1
        assert results[0]['quality'] == 'A'

    def test_most_recent_first(self, store):
        store.record_signal('binance', _signal(symbol='FIRST'), should_notify=True,
                             created_at='2026-01-01T00:00:00+00:00')
        store.record_signal('binance', _signal(symbol='SECOND'), should_notify=True,
                             created_at='2026-01-02T00:00:00+00:00')

        results = store.get_recent_signals(limit=10)

        assert [r['symbol'] for r in results] == ['SECOND', 'FIRST']

    def test_limit_is_respected(self, store):
        for i in range(5):
            store.record_signal('binance', _signal(symbol=f'PAIR{i}'), should_notify=True)

        assert len(store.get_recent_signals(limit=2)) == 2


class TestMarketContext:
    def test_round_trip(self, store):
        context = {
            'btc_trend': 'bullish', 'btc_change_24h': 3.1, 'btc_change_1h': 0.2,
            'market_sentiment': 'risk_on', 'total_gainers': 30, 'total_losers': 10,
            'dominance_ratio': 3.0,
        }
        store.record_market_context('binance', context)

        results = store.get_market_context(exchange='binance', limit=1)

        assert len(results) == 1
        assert results[0]['btc_trend'] == 'bullish'
        assert results[0]['total_gainers'] == 30

    def test_history_param_limits_results(self, store):
        for i in range(5):
            store.record_market_context('binance', {'btc_trend': 'neutral'})

        assert len(store.get_market_context(exchange='binance', limit=3)) == 3

    def test_filters_by_exchange(self, store):
        store.record_market_context('binance', {'btc_trend': 'bullish'})
        store.record_market_context('coinbase', {'btc_trend': 'bearish'})

        results = store.get_market_context(exchange='coinbase', limit=10)

        assert len(results) == 1
        assert results[0]['btc_trend'] == 'bearish'


class TestIndicatorSnapshots:
    def test_round_trip(self, store):
        store.record_indicator_snapshot(
            'binance', 'BTC/USDT', '4h', 'indicators', 'rsi', {'rsi': 42.5}
        )

        results = store.get_indicator_snapshots(symbol='BTC/USDT')

        assert len(results) == 1
        assert results[0]['values'] == {'rsi': 42.5}

    def test_upsert_replaces_not_appends(self, store):
        store.record_indicator_snapshot(
            'binance', 'BTC/USDT', '4h', 'indicators', 'rsi', {'rsi': 42.5}
        )
        store.record_indicator_snapshot(
            'binance', 'BTC/USDT', '4h', 'indicators', 'rsi', {'rsi': 55.0}
        )

        results = store.get_indicator_snapshots(symbol='BTC/USDT')

        assert len(results) == 1
        assert results[0]['values'] == {'rsi': 55.0}

    def test_filters_by_symbol_and_exchange(self, store):
        store.record_indicator_snapshot('binance', 'BTC/USDT', '4h', 'indicators', 'rsi', {'rsi': 1})
        store.record_indicator_snapshot('binance', 'ETH/USDT', '4h', 'indicators', 'rsi', {'rsi': 2})

        results = store.get_indicator_snapshots(symbol='ETH/USDT', exchange='binance')

        assert len(results) == 1
        assert results[0]['symbol'] == 'ETH/USDT'


class TestWorkerStatus:
    def test_round_trip(self, store):
        store.record_worker_heartbeat('Worker-1', ['BTC/USDT', 'ETH/USDT'], cycle_count=3)

        results = store.get_worker_status()

        assert len(results) == 1
        assert results[0]['worker_name'] == 'Worker-1'
        assert results[0]['pairs'] == ['BTC/USDT', 'ETH/USDT']
        assert results[0]['cycle_count'] == 3

    def test_upsert_replaces_not_appends(self, store):
        store.record_worker_heartbeat('Worker-1', ['BTC/USDT'], cycle_count=1)
        store.record_worker_heartbeat('Worker-1', ['BTC/USDT'], cycle_count=2, last_error='boom')

        results = store.get_worker_status()

        assert len(results) == 1
        assert results[0]['cycle_count'] == 2
        assert results[0]['last_error'] == 'boom'

    def test_multiple_workers_tracked_independently(self, store):
        store.record_worker_heartbeat('Worker-1', ['BTC/USDT'], cycle_count=1)
        store.record_worker_heartbeat('Worker-2', ['ETH/USDT'], cycle_count=5)

        results = store.get_worker_status()

        assert len(results) == 2
        names = {r['worker_name'] for r in results}
        assert names == {'Worker-1', 'Worker-2'}
