"""
Genera la lista de eventos Wyckoff de altcoins (BTC excluido) con resultado
conocido, para el piloto de Twitter event-triggered (specs/028).

Uso:
    PYTHONPATH=/work/app python specs/028-twitter-event-triggered-pilot/generate_altcoin_events.py
"""
import sys
import time
import json
from datetime import datetime, timezone, timedelta

import ccxt
import numpy as np
import pandas as pd

from analyzers.indicators.wyckoff import WyckoffPrimitives


BASKET = [
    'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT',
    'BCH/USDT', 'ATOM/USDT', 'NEAR/USDT',
]
TICKER_NAMES = {
    'ETH/USDT': 'ETH', 'BNB/USDT': 'BNB', 'SOL/USDT': 'SOL', 'XRP/USDT': 'XRP',
    'ADA/USDT': 'ADA', 'DOGE/USDT': 'DOGE', 'AVAX/USDT': 'AVAX', 'LINK/USDT': 'LINK',
    'DOT/USDT': 'DOT', 'LTC/USDT': 'LTC', 'BCH/USDT': 'BCH', 'ATOM/USDT': 'ATOM',
    'NEAR/USDT': 'NEAR',
}
TIMEFRAME = '4h'
MONTHS_BACK = 3  # ventana de busqueda historica realista de getxapi (spec 020/022)
LOOKBACK = 20
CONFIRM_WINDOW = 3
EXTREME_VOLUME_THRESHOLD = 2.5
MIN_AGE_DAYS = 15  # necesitamos ret_14d ya conocido


def fetch_ohlcv_paginated(exchange, pair, timeframe, since_ms, now_ms, limit=1000):
    all_rows = []
    since = since_ms
    while True:
        batch = exchange.fetch_ohlcv(pair, timeframe=timeframe, since=since, limit=limit)
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        time.sleep(exchange.rateLimit / 1000)
        if last_ts >= now_ms or len(batch) < limit:
            break
        since = last_ts + 1
    if not all_rows:
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = pd.DataFrame(all_rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)
    df = df[df['timestamp'] <= now_ms].reset_index(drop=True)
    return df


def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30 * MONTHS_BACK)
    since_ms, now_ms = int(since.timestamp() * 1000), int(now.timestamp() * 1000)
    cutoff_ms = int((now - timedelta(days=MIN_AGE_DAYS)).timestamp() * 1000)

    events = []
    for pair in BASKET:
        print(f"Fetching {pair}...", file=sys.stderr)
        df = fetch_ohlcv_paginated(exchange, pair, TIMEFRAME, since_ms, now_ms)
        if len(df) < LOOKBACK + CONFIRM_WINDOW + 84 + 5:
            print(f"  insufficient history, skipping", file=sys.stderr)
            continue

        closes = df['close'].values.astype(float)
        timestamps = df['timestamp'].values

        springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)

        for i in range(len(df)):
            direction = None
            if bool(springs['is_spring'].iloc[i]):
                direction, flags = 'hot', springs
            elif bool(upthrusts['is_upthrust'].iloc[i]):
                direction, flags = 'cold', upthrusts
            else:
                continue

            rv = flags['break_relative_volume'].iloc[i]
            if pd.isna(rv) or rv < EXTREME_VOLUME_THRESHOLD:
                continue

            ts = int(timestamps[i])
            if ts > cutoff_ms:
                continue  # muy reciente, no tiene ret_14d todavia

            j7 = i + 42
            j14 = i + 84
            if j14 >= len(closes):
                continue
            ret7 = (closes[j7] - closes[i]) / closes[i]
            ret14 = (closes[j14] - closes[i]) / closes[i]
            ret7 = ret7 if direction == 'hot' else -ret7
            ret14 = ret14 if direction == 'hot' else -ret14

            events.append({
                'pair': pair, 'ticker': TICKER_NAMES[pair],
                'timestamp_ms': ts,
                'datetime_utc': datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(),
                'direction': direction, 'break_relative_volume': float(rv),
                'ret_7d': float(ret7), 'ret_14d': float(ret14),
                'win_7d': bool(ret7 > 0), 'win_14d': bool(ret14 > 0),
            })

    events.sort(key=lambda e: e['timestamp_ms'])
    print(f"\nTotal altcoin events with known outcome: {len(events)}", file=sys.stderr)
    print(json.dumps(events, indent=2))


if __name__ == '__main__':
    main()
