"""
Validacion del edge Wyckoff (volumen extremo en Spring/Upthrust) en otros
timeframes (specs/025-wyckoff-multi-timeframe-validation/), continuacion de
specs/017-018 (donde se valido en 4h, unico timeframe hoy en produccion via
specs/023-wyckoff-live-alerts/).

Reutiliza WyckoffPrimitives TAL CUAL desde app/ (codigo de produccion, sin
reimplementar) -- solo varia el timeframe de entrada. Mismo split cronologico
70/30 in-sample/out-of-sample y misma vara de "confirmed" que specs/017/018/024.

No conecta nada a codigo de produccion (FR-007).

Uso:
    PYTHONPATH=/work/app python specs/025-wyckoff-multi-timeframe-validation/validate_wyckoff_timeframes.py
"""
import sys
import time
import math
from datetime import datetime, timezone, timedelta

import ccxt
import numpy as np
import pandas as pd

from analyzers.indicators.wyckoff import WyckoffPrimitives


BASKET = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT',
    'BCH/USDT', 'ATOM/USDT', 'NEAR/USDT', 'MATIC/USDT',
]
MONTHS_BACK = 10
LOOKBACK = 20
CONFIRM_WINDOW = 3
EXTREME_VOLUME_THRESHOLD = 2.5
IN_SAMPLE_FRACTION = 0.7
MIN_SAMPLE = 30
ACTIONABLE_WIN_RATE = 0.60

# timeframe -> hours per candle (used to convert real-time horizons to candle counts)
TIMEFRAMES = {
    '1h': 1, '2h': 2, '4h': 4, '8h': 8, '1d': 24,
}
HORIZONS_HOURS = {'24h': 24, '72h': 72, '7d': 168, '14d': 336}


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


def fetch_all(exchange, timeframe, months_back):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30 * months_back)
    since_ms, now_ms = int(since.timestamp() * 1000), int(now.timestamp() * 1000)

    data = {}
    for pair in BASKET:
        print(f"  Fetching {pair} ({timeframe})...", file=sys.stderr)
        try:
            df = fetch_ohlcv_paginated(exchange, pair, timeframe, since_ms, now_ms)
        except Exception as e:
            print(f"    FAILED ({type(e).__name__}: {e}) -- skipping", file=sys.stderr)
            continue
        if len(df) == 0:
            print(f"    0 candles -- skipping", file=sys.stderr)
            continue
        data[pair] = df
        print(f"    {len(df)} candles", file=sys.stderr)
    return data


def collect_events(basket_df, hours_per_candle):
    horizons_candles = {
        label: max(1, round(hours / hours_per_candle))
        for label, hours in HORIZONS_HOURS.items()
    }
    max_horizon_candles = max(horizons_candles.values())
    min_history = LOOKBACK + CONFIRM_WINDOW + max_horizon_candles + 5

    records = []
    for pair, df in basket_df.items():
        if len(df) < min_history:
            print(f"  Skipping {pair}: insufficient history ({len(df)} candles, need {min_history})",
                  file=sys.stderr)
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

            break_rv = flags['break_relative_volume'].iloc[i]
            if pd.isna(break_rv) or break_rv < EXTREME_VOLUME_THRESHOLD:
                continue  # solo el mecanismo ya validado: volumen extremo en la ruptura

            row = {'pair': pair, 'timestamp': timestamps[i], 'direction': direction}
            valid = True
            for h_label, h_candles in horizons_candles.items():
                j = i + h_candles
                if j >= len(closes):
                    valid = False
                    break
                fwd = (closes[j] - closes[i]) / closes[i]
                row[f'ret_{h_label}'] = fwd if direction == 'hot' else -fwd
            if not valid:
                continue
            records.append(row)

    return pd.DataFrame(records), horizons_candles


def win_rate_z_test(n, win_rate, null_p=0.5):
    if n == 0:
        return 0.0, 1.0
    se = math.sqrt(null_p * (1 - null_p) / n)
    z = (win_rate - null_p) / se
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, p_value


def evaluate_bucket(df, ret_col, label):
    n = len(df)
    if n < MIN_SAMPLE:
        return {'label': label, 'n': n, 'win_rate': None, 'mean': None, 'insufficient': True}
    win_rate = (df[ret_col] > 0).mean()
    mean = df[ret_col].mean()
    z, p = win_rate_z_test(n, win_rate)
    return {'label': label, 'n': n, 'win_rate': win_rate, 'mean': mean, 'z': z, 'p': p,
            'insufficient': False}


def print_bucket(b):
    if b['insufficient']:
        print(f"      {b['label']}: n={b['n']} -- INSUFFICIENT SAMPLE")
    else:
        sig = " *sig*" if b['p'] < 0.05 else ""
        print(f"      {b['label']}: n={b['n']:4d} | win_rate={b['win_rate']:.1%} "
              f"(p={b['p']:.4f}){sig} | mean={b['mean']:+.4%}")


def evaluate_timeframe(tf_label, events, months_covered, n_pairs):
    events = events.sort_values('timestamp').reset_index(drop=True)
    split_idx = int(len(events) * IN_SAMPLE_FRACTION)
    in_sample, out_sample = events.iloc[:split_idx], events.iloc[split_idx:]

    events_per_pair_per_month = (len(events) / n_pairs / months_covered) if n_pairs and months_covered else 0.0

    print(f"\n--- Timeframe: {tf_label} ---")
    print(f"    total qualifying events (volume>=2.5x): {len(events)} | "
          f"in-sample: {len(in_sample)} | out-of-sample: {len(out_sample)}")
    print(f"    frequency: ~{events_per_pair_per_month:.2f} eventos/par/mes")

    any_confirmed = False
    per_horizon = {}
    for h_label in HORIZONS_HOURS:
        ret_col = f'ret_{h_label}'
        in_b = evaluate_bucket(in_sample, ret_col, f'in-sample  {h_label}')
        out_b = evaluate_bucket(out_sample, ret_col, f'out-sample {h_label}')
        print_bucket(in_b)
        print_bucket(out_b)

        if in_b['insufficient'] or out_b['insufficient']:
            verdict = 'insufficient_sample'
        elif out_b['win_rate'] >= ACTIONABLE_WIN_RATE and out_b['p'] < 0.05:
            verdict = 'confirmed'
            any_confirmed = True
        else:
            verdict = 'did_not_replicate'
        per_horizon[h_label] = {'in_sample': in_b, 'out_of_sample': out_b, 'verdict': verdict}

    overall = 'confirmed' if any_confirmed else 'did_not_replicate'
    if all(v['verdict'] == 'insufficient_sample' for v in per_horizon.values()):
        overall = 'insufficient_sample'
    print(f"    OVERALL VERDICT: {overall}")
    return {'timeframe': tf_label, 'per_horizon': per_horizon, 'overall': overall,
            'events_per_pair_per_month': events_per_pair_per_month, 'total_events': len(events)}


def main():
    exchange = ccxt.binance({'enableRateLimit': True})

    results = []
    for tf_label, hours_per_candle in TIMEFRAMES.items():
        print(f"\n{'=' * 78}\nFetching timeframe {tf_label}...\n{'=' * 78}", file=sys.stderr)
        basket_df = fetch_all(exchange, tf_label, MONTHS_BACK)
        events, horizons_candles = collect_events(basket_df, hours_per_candle)
        print(f"{tf_label}: {len(events)} qualifying events (volume>=2.5x) across "
              f"{len(basket_df)} pairs", file=sys.stderr)
        results.append(evaluate_timeframe(tf_label, events, MONTHS_BACK, len(basket_df)))

    print("\n" + "=" * 78)
    print("SUMMARY -- Wyckoff extreme-volume edge across timeframes")
    print("=" * 78)
    confirmed = [r for r in results if r['overall'] == 'confirmed']
    if confirmed:
        for r in confirmed:
            print(f"  CONFIRMED: {r['timeframe']} -- "
                  f"~{r['events_per_pair_per_month']:.2f} eventos/par/mes")
            for h_label, v in r['per_horizon'].items():
                if v['verdict'] == 'confirmed':
                    ob = v['out_of_sample']
                    print(f"      -> {h_label}: win_rate={ob['win_rate']:.1%}, n={ob['n']}, p={ob['p']:.4f}")
    else:
        print("  Ningun timeframe confirmo en ningun horizonte "
              f"(bar: win_rate>={ACTIONABLE_WIN_RATE:.0%}, p<0.05, n>={MIN_SAMPLE}).")
    print("\n  Frecuencia de eventos por timeframe (referencia):")
    for r in results:
        print(f"    {r['timeframe']}: {r['total_events']} eventos totales, "
              f"~{r['events_per_pair_per_month']:.2f}/par/mes")
    print("=" * 78)


if __name__ == '__main__':
    main()
