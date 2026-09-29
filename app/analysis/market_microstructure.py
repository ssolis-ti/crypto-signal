"""
Microestructura al momento de la alerta (specs/037-microestructura-funding/).

Toma una foto de datos PUBLICOS de Binance USD-M (funding, open interest, ratio long/short,
libro de ordenes) cuando sale una alerta y la deja en el registro. NO filtra ni cambia nada
del mensaje: el libro y el open interest no tienen historia larga en Binance (el open interest
solo 30 dias), asi que no se pueden backtestear; la unica forma de validarlos es registrarlos
hoy y compararlos con el resultado real a 24h/72h cuando haya >= 50 alertas (Principio III).

Solo lectura, sin llaves (Principio I). Cada dato falla por separado: un error en uno no
impide registrar los demas, y nunca rompe el ciclo.
"""
from typing import Dict, Optional

import ccxt
import structlog

REQUEST_TIMEOUT_MS = 10000
BOOK_LEVELS = 500
OI_HISTORY_HOURS = 24
OI_MIN_SPAN_HOURS = 23
DEPTH_BAND_PCT = 1.0


class MarketMicrostructure:
    def __init__(self, enabled: bool = False, exchange=None):
        self.logger = structlog.get_logger()
        self.enabled = enabled
        self._exchange = exchange
        self._markets_loaded = exchange is not None

    @staticmethod
    def futures_symbol(market_pair: str) -> str:
        """'BTC/USDT' -> 'BTC/USDT:USDT' (perpetuo lineal de Binance)."""
        if ':' in market_pair:
            return market_pair
        quote = market_pair.split('/')[1] if '/' in market_pair else 'USDT'
        return f"{market_pair}:{quote}"

    def _get_exchange(self):
        if self._exchange is None:
            self._exchange = ccxt.binanceusdm({'enableRateLimit': True, 'timeout': REQUEST_TIMEOUT_MS})
        if not self._markets_loaded:
            self._exchange.load_markets()
            self._markets_loaded = True
        return self._exchange

    def snapshot(self, exchange_name: str, market_pair: str) -> Optional[Dict]:
        """Foto de microestructura, o None si esta deshabilitado / no es Binance / no hay perpetuo."""
        if not self.enabled or exchange_name != 'binance':
            return None
        try:
            ex = self._get_exchange()
            symbol = self.futures_symbol(market_pair)
            if symbol not in ex.markets:
                return None
        except Exception as e:
            self.logger.error(f"[MICRO] No se pudo preparar el exchange: {e}")
            return None

        data: Dict = {}
        mark_price = self._funding(ex, symbol, data)
        self._open_interest(ex, symbol, mark_price, data)
        self._long_short(ex, symbol, data)
        self._order_book(ex, symbol, data)
        return data

    def _funding(self, ex, symbol: str, data: Dict) -> Optional[float]:
        try:
            info = ex.fetch_funding_rate(symbol)
            rate = info.get('fundingRate')
            data['funding_rate_pct'] = None if rate is None else round(float(rate) * 100, 5)
            return info.get('markPrice')
        except Exception as e:
            self.logger.error(f"[MICRO] funding {symbol}: {e}")
            return None

    def _open_interest(self, ex, symbol: str, mark_price, data: Dict) -> None:
        try:
            history = ex.fetch_open_interest_history(symbol, '1h', limit=OI_HISTORY_HOURS + 1)
            rows = [h for h in history if h.get('openInterestValue')]
            if rows:
                first, last = rows[0], rows[-1]
                data['open_interest_usd'] = round(float(last['openInterestValue']), 0)
                # Un par recien listado (o un hueco del endpoint) no cubre 24h: no se rotula como cambio 24h.
                span_ms = (last.get('timestamp') or 0) - (first.get('timestamp') or 0)
                if len(rows) >= 2 and span_ms >= OI_MIN_SPAN_HOURS * 3600 * 1000:
                    data['oi_change_24h_pct'] = round(
                        (last['openInterestValue'] - first['openInterestValue']) / first['openInterestValue'] * 100, 2)
                return
        except Exception as e:
            self.logger.error(f"[MICRO] historial de open interest {symbol}: {e}")
        try:
            amount = ex.fetch_open_interest(symbol).get('openInterestAmount')
            if amount and mark_price:
                data['open_interest_usd'] = round(float(amount) * float(mark_price), 0)
        except Exception as e:
            self.logger.error(f"[MICRO] open interest {symbol}: {e}")

    def _long_short(self, ex, symbol: str, data: Dict) -> None:
        try:
            rows = ex.fetch_long_short_ratio_history(symbol, '1h', limit=1)
            if rows and rows[-1].get('longShortRatio') is not None:
                data['long_short_ratio'] = round(float(rows[-1]['longShortRatio']), 3)
        except Exception as e:
            self.logger.error(f"[MICRO] long/short {symbol}: {e}")

    def _order_book(self, ex, symbol: str, data: Dict) -> None:
        try:
            book = ex.fetch_order_book(symbol, limit=BOOK_LEVELS)
            data.update(self.book_metrics(book.get('bids') or [], book.get('asks') or []))
        except Exception as e:
            self.logger.error(f"[MICRO] libro {symbol}: {e}")

    @staticmethod
    def book_metrics(bids: list, asks: list) -> Dict:
        """
        Desequilibrio del libro. imbalance en [-1, 1]: >0 = mas dinero comprando que vendiendo.
        Se mide sobre todos los niveles pedidos (imbalance) y, si el libro llega tan lejos,
        dentro de +-1% del precio medio (imbalance_1pct). *_range_pct dice hasta donde llega.
        """
        if not bids or not asks:
            return {}
        best_bid, best_ask = float(bids[0][0]), float(asks[0][0])
        mid = (best_bid + best_ask) / 2
        if mid <= 0:
            return {}
        bid_usd = sum(float(p) * float(q) for p, q in bids)
        ask_usd = sum(float(p) * float(q) for p, q in asks)
        result = {
            'spread_pct': round((best_ask - best_bid) / mid * 100, 4),
            'book_bid_usd': round(bid_usd, 0),
            'book_ask_usd': round(ask_usd, 0),
            'book_imbalance': round((bid_usd - ask_usd) / (bid_usd + ask_usd), 3) if bid_usd + ask_usd else None,
            'book_bid_range_pct': round((mid - float(bids[-1][0])) / mid * 100, 3),
            'book_ask_range_pct': round((float(asks[-1][0]) - mid) / mid * 100, 3),
        }
        if result['book_bid_range_pct'] >= DEPTH_BAND_PCT and result['book_ask_range_pct'] >= DEPTH_BAND_PCT:
            low, high = mid * (1 - DEPTH_BAND_PCT / 100), mid * (1 + DEPTH_BAND_PCT / 100)
            near_bid = sum(float(p) * float(q) for p, q in bids if float(p) >= low)
            near_ask = sum(float(p) * float(q) for p, q in asks if float(p) <= high)
            total = near_bid + near_ask
            result['imbalance_1pct'] = round((near_bid - near_ask) / total, 3) if total else None
        return result
