"""
Tests para PairResolver.resolve (specs/004-core-pipeline-test-coverage/).
"""
import pytest

from data.pair_resolver import PairResolver


class FakeDataManager:
    def __init__(self, pairs):
        self.pairs = pairs
        self.calls = []

    def get_top_pairs(self, exchange, quote, top_n, min_volume):
        self.calls.append({
            'exchange': exchange, 'quote': quote, 'top_n': top_n, 'min_volume': min_volume
        })
        return self.pairs[:top_n]


class TestPairResolverManualMode:
    def test_manual_pairs_take_precedence(self):
        dm = FakeDataManager(['XRP/USDT'])
        settings = {
            'market_pairs': ['BTC/USDT', 'ETH/USDT'],
            'dynamic_pairs': {'enabled': True, 'source': 'volume'},
        }
        resolver = PairResolver(settings, dm)

        result = resolver.resolve('binance')

        assert result == ['BTC/USDT', 'ETH/USDT']
        assert dm.calls == []


class TestPairResolverDynamicMode:
    def test_volume_mode_applies_exclusions_and_top_n(self):
        dm = FakeDataManager(['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT'])
        settings = {
            'market_pairs': None,
            'dynamic_pairs': {
                'enabled': True, 'source': 'volume', 'top_n': 2,
                'quote_currency': 'USDT', 'exclude': ['ETH/USDT'],
            },
        }
        resolver = PairResolver(settings, dm)

        result = resolver.resolve('binance')

        assert 'ETH/USDT' not in result
        assert len(result) == 2
        # requested more than top_n to compensate for the exclusion
        assert dm.calls[0]['top_n'] == 2 + 1

    def test_spot_exclusion_also_drops_the_perpetual_symbol(self):
        dm = FakeDataManager(['BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT'])
        settings = {
            'market_pairs': None,
            'dynamic_pairs': {
                'enabled': True, 'source': 'volume', 'top_n': 5,
                'quote_currency': 'USDT', 'exclude': ['ETH/USDT'],
            },
        }
        resolver = PairResolver(settings, dm)

        result = resolver.resolve('binance')

        assert result == ['BTC/USDT:USDT', 'BNB/USDT:USDT']

    def test_data_manager_none_returns_empty_list(self):
        settings = {
            'market_pairs': None,
            'dynamic_pairs': {'enabled': True, 'source': 'volume'},
        }
        resolver = PairResolver(settings, data_manager=None)

        assert resolver.resolve('binance') == []

    def test_unsupported_source_returns_empty_without_calling_data_manager(self):
        dm = FakeDataManager(['BTC/USDT'])
        settings = {
            'market_pairs': None,
            'dynamic_pairs': {'enabled': True, 'source': 'coingecko'},
        }
        resolver = PairResolver(settings, dm)

        assert resolver.resolve('binance') == []
        assert dm.calls == []


class TestPairResolverUnconfigured:
    def test_no_config_returns_empty_list(self):
        settings = {'market_pairs': None, 'dynamic_pairs': {}}
        resolver = PairResolver(settings, data_manager=None)

        assert resolver.resolve('binance') == []

    def test_empty_manual_list_falls_through_to_fallback(self):
        settings = {'market_pairs': [], 'dynamic_pairs': {}}
        resolver = PairResolver(settings, data_manager=None)

        assert resolver.resolve('binance') == []
