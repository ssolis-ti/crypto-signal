from analysis.market_microstructure import MarketMicrostructure


class FakeExchange:
    def __init__(self, fail=()):
        self.markets = {'BTC/USDT:USDT': {}}
        self.fail = set(fail)

    def _maybe(self, name):
        if name in self.fail:
            raise RuntimeError(f"{name} caido")

    def fetch_funding_rate(self, symbol):
        self._maybe('funding')
        return {'fundingRate': 0.0001, 'markPrice': 100.0}

    def fetch_open_interest_history(self, symbol, tf, limit):
        self._maybe('oi')
        return [{'openInterestValue': 1000.0}, {'openInterestValue': 1100.0}]

    def fetch_open_interest(self, symbol):
        return {'openInterestAmount': 5.0}

    def fetch_long_short_ratio_history(self, symbol, tf, limit):
        self._maybe('ls')
        return [{'longShortRatio': 1.25}]

    def fetch_order_book(self, symbol, limit):
        self._maybe('book')
        return {'bids': [[99.9, 10], [98.5, 10]], 'asks': [[100.1, 5], [101.5, 5]]}


def test_disabled_or_other_exchange_returns_none():
    assert MarketMicrostructure(enabled=False, exchange=FakeExchange()).snapshot('binance', 'BTC/USDT') is None
    assert MarketMicrostructure(enabled=True, exchange=FakeExchange()).snapshot('kraken', 'BTC/USDT') is None


def test_pair_without_perpetual_returns_none():
    assert MarketMicrostructure(enabled=True, exchange=FakeExchange()).snapshot('binance', 'XYZ/USDT') is None


def test_full_snapshot():
    data = MarketMicrostructure(enabled=True, exchange=FakeExchange()).snapshot('binance', 'BTC/USDT')
    assert data['funding_rate_pct'] == 0.01
    assert data['open_interest_usd'] == 1100.0
    assert data['oi_change_24h_pct'] == 10.0
    assert data['long_short_ratio'] == 1.25
    assert data['book_imbalance'] > 0  # mas dinero en bids que en asks
    assert data['spread_pct'] > 0


def test_each_source_fails_independently():
    data = MarketMicrostructure(enabled=True, exchange=FakeExchange(fail=('funding', 'book'))).snapshot(
        'binance', 'BTC/USDT')
    assert 'funding_rate_pct' not in data and 'book_imbalance' not in data
    assert data['long_short_ratio'] == 1.25 and data['oi_change_24h_pct'] == 10.0


def test_oi_falls_back_to_current_when_history_fails():
    data = MarketMicrostructure(enabled=True, exchange=FakeExchange(fail=('oi',))).snapshot('binance', 'BTC/USDT')
    assert data['open_interest_usd'] == 500.0  # 5 contratos * markPrice 100


def test_book_metrics_empty_and_band():
    assert MarketMicrostructure.book_metrics([], []) == {}
    m = MarketMicrostructure.book_metrics([[100, 1], [98, 1]], [[100.2, 1], [102, 1]])
    assert m['imbalance_1pct'] is not None  # el libro cubre mas de 1% de cada lado
    m = MarketMicrostructure.book_metrics([[100, 1], [99.9, 1]], [[100.1, 1], [100.2, 1]])
    assert 'imbalance_1pct' not in m  # libro muy corto: no se inventa la banda


def test_futures_symbol():
    assert MarketMicrostructure.futures_symbol('BTC/USDT') == 'BTC/USDT:USDT'
    assert MarketMicrostructure.futures_symbol('BTC/USDT:USDT') == 'BTC/USDT:USDT'
