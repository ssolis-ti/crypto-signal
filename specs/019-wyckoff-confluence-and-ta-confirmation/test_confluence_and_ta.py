"""
Confluencia 1D/4h y confirmacion con TA existente (specs/019-.../), continuacion de
specs/017-wyckoff-edge-refinement/.

Prueba UNA hipotesis fractal puntual (no un barrido de 9 temporalidades, ver spec.md):
¿un Spring/Upthrust de 4h con volumen extremo ya validado (slice 017) es mas fuerte
cuando el MISMO patron estructural tambien se confirma en 1D cerca del mismo momento?
Ademas suma dos herramientas de TA que el proyecto ya usa (RSI, ADX via talib) como
posibles factores de confirmacion. Mismo split cronologico 70/30 in-sample/out-of-sample
que slice 017 -- ningun filtro se conecta a codigo de produccion (FR-005).

Uso:
    PYTHONPATH=/work/app python specs/019-wyckoff-confluence-and-ta-confirmation/test_confluence_and_ta.py
"""
import sys
import time
import math
from datetime import datetime, timezone, timedelta

import ccxt
import numpy as np
import pandas as pd
import talib

from analyzers.indicators.wyckoff import WyckoffPrimitives


BASKET = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT',
    'BCH/USDT', 'ATOM/USDT', 'NEAR/USDT', 'MATIC/USDT',
]
MONTHS_BACK = 10
LOOKBACK_4H = 20
CONFIRM_WINDOW_4H = 3
LOOKBACK_1D = 20
CONFIRM_WINDOW_1D = 3
EXTREME_VOLUME_THRESHOLD = 2.5
HORIZON_CANDLES_4H = 84  # 14 dias en velas de 4h
CONFLUENCE_WINDOW_MS = 3 * 24 * 3600 * 1000  # +-3 dias
RSI_HOT_MAX, RSI_COLD_MIN = 35, 65
ADX_STRONG_THRESHOLD = 25
IN_SAMPLE_FRACTION = 0.7
MIN_SAMPLE = 30
ACTIONABLE_WIN_RATE = 0.60


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
        print(f"Fetching {pair} ({timeframe})...", file=sys.stderr)
        try:
            df = fetch_ohlcv_paginated(exchange, pair, timeframe, since_ms, now_ms)
        except Exception as e:
            print(f"  FAILED ({type(e).__name__}: {e}) -- skipping", file=sys.stderr)
            continue
        data[pair] = df
        print(f"  {len(df)} candles", file=sys.stderr)
    return data


def get_1d_events(df_1d):
    """(timestamps, direction) de eventos Spring/Upthrust confirmados en 1D."""
    if df_1d is None or len(df_1d) < LOOKBACK_1D + CONFIRM_WINDOW_1D + 5:
        return []
    springs = WyckoffPrimitives.detect_springs(df_1d, lookback=LOOKBACK_1D, confirm_window=CONFIRM_WINDOW_1D)
    upthrusts = WyckoffPrimitives.detect_upthrusts(df_1d, lookback=LOOKBACK_1D, confirm_window=CONFIRM_WINDOW_1D)
    ts = df_1d['timestamp'].values
    events = []
    for i in range(len(df_1d)):
        if bool(springs['is_spring'].iloc[i]):
            events.append((ts[i], 'hot'))
        elif bool(upthrusts['is_upthrust'].iloc[i]):
            events.append((ts[i], 'cold'))
    return events


def has_confluence(event_ts, direction, daily_events):
    for d_ts, d_dir in daily_events:
        if d_dir == direction and abs(int(d_ts) - int(event_ts)) <= CONFLUENCE_WINDOW_MS:
            return True
    return False


def collect_events(basket_4h, basket_1d):
    records = []
    min_history = LOOKBACK_4H + HORIZON_CANDLES_4H + CONFIRM_WINDOW_4H + 5

    for pair, df in basket_4h.items():
        if len(df) < min_history:
            continue

        closes = df['close'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        timestamps = df['timestamp'].values

        rsi = talib.RSI(closes, timeperiod=14)
        adx = talib.ADX(highs, lows, closes, timeperiod=14)

        springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK_4H, confirm_window=CONFIRM_WINDOW_4H)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK_4H, confirm_window=CONFIRM_WINDOW_4H)

        daily_events = get_1d_events(basket_1d.get(pair))

        for i in range(len(df)):
            direction, flags = None, None
            if bool(springs['is_spring'].iloc[i]):
                direction, flags = 'hot', springs
            elif bool(upthrusts['is_upthrust'].iloc[i]):
                direction, flags = 'cold', upthrusts
            else:
                continue

            break_rv = flags['break_relative_volume'].iloc[i]
            if pd.isna(break_rv) or break_rv < EXTREME_VOLUME_THRESHOLD:
                continue  # solo el set ya validado en slice 017

            j = i + HORIZON_CANDLES_4H
            if j >= len(closes):
                continue
            fwd = (closes[j] - closes[i]) / closes[i]
            expected_dir_return = fwd if direction == 'hot' else -fwd

            rsi_val = rsi[i] if not np.isnan(rsi[i]) else None
            adx_val = adx[i] if not np.isnan(adx[i]) else None
            rsi_extreme = (
                (direction == 'hot' and rsi_val is not None and rsi_val < RSI_HOT_MAX) or
                (direction == 'cold' and rsi_val is not None and rsi_val > RSI_COLD_MIN)
            )

            records.append({
                'pair': pair, 'timestamp': timestamps[i], 'direction': direction,
                'expected_dir_return': expected_dir_return,
                'confluence_1d': has_confluence(timestamps[i], direction, daily_events),
                'rsi_extreme': rsi_extreme,
                'adx_strong': (adx_val is not None and adx_val >= ADX_STRONG_THRESHOLD),
            })

    return pd.DataFrame(records)


def win_rate_z_test(n, win_rate, null_p=0.5):
    if n == 0:
        return 0.0, 1.0
    se = math.sqrt(null_p * (1 - null_p) / n)
    z = (win_rate - null_p) / se
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, p_value


def evaluate_bucket(df, mask, label):
    bucket = df[mask]
    n = len(bucket)
    if n < MIN_SAMPLE:
        return {'label': label, 'n': n, 'win_rate': None, 'mean': None, 'insufficient': True}
    win_rate = (bucket['expected_dir_return'] > 0).mean()
    mean = bucket['expected_dir_return'].mean()
    z, p = win_rate_z_test(n, win_rate)
    return {'label': label, 'n': n, 'win_rate': win_rate, 'mean': mean, 'z': z, 'p': p,
            'insufficient': False}


def print_bucket(b):
    if b['insufficient']:
        print(f"    {b['label']}: n={b['n']} -- INSUFFICIENT SAMPLE")
    else:
        sig = " *sig*" if b['p'] < 0.05 else ""
        print(f"    {b['label']}: n={b['n']:4d} | win_rate={b['win_rate']:.1%} "
              f"(p={b['p']:.4f}){sig} | mean={b['mean']:+.4%}")


def evaluate_filter(name, in_sample, out_sample, base_in, base_out, mask_col):
    print(f"\n--- Filter: {name} ---")
    in_b = evaluate_bucket(in_sample, in_sample[mask_col] == True, 'in-sample (filtered)')  # noqa: E712
    out_b = evaluate_bucket(out_sample, out_sample[mask_col] == True, 'out-of-sample (filtered)')  # noqa: E712
    print_bucket(in_b)
    print_bucket(out_b)

    if not in_b['insufficient']:
        print(f"    lift vs in-sample baseline ({base_in['win_rate']:.1%}): "
              f"{(in_b['win_rate'] - base_in['win_rate']) * 100:+.1f}pp")
    if not out_b['insufficient']:
        print(f"    lift vs out-of-sample baseline ({base_out['win_rate']:.1%}): "
              f"{(out_b['win_rate'] - base_out['win_rate']) * 100:+.1f}pp")

    if in_b['insufficient'] or out_b['insufficient']:
        verdict = 'insufficient_sample'
    elif out_b['win_rate'] >= ACTIONABLE_WIN_RATE and out_b['p'] < 0.05:
        verdict = 'confirmed'
    else:
        verdict = 'did_not_replicate'
    print(f"    VERDICT: {verdict}")
    return {'name': name, 'in_sample': in_b, 'out_of_sample': out_b, 'verdict': verdict}


def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    basket_4h = fetch_all(exchange, '4h', MONTHS_BACK)
    basket_1d = fetch_all(exchange, '1d', MONTHS_BACK)

    events = collect_events(basket_4h, basket_1d)
    events = events.sort_values('timestamp').reset_index(drop=True)
    print(f"\nTotal events: {len(events)}", file=sys.stderr)

    split_idx = int(len(events) * IN_SAMPLE_FRACTION)
    in_sample, out_sample = events.iloc[:split_idx], events.iloc[split_idx:]

    print("\n" + "=" * 70)
    print("CONFLUENCE 1D/4h + TA CONFIRMATION -- IN-SAMPLE / OUT-OF-SAMPLE")
    print("=" * 70)
    print(f"\nTotal events: {len(events)} | in-sample: {len(in_sample)} | "
          f"out-of-sample: {len(out_sample)}")

    base_in = evaluate_bucket(in_sample, pd.Series(True, index=in_sample.index), 'baseline (all)')
    base_out = evaluate_bucket(out_sample, pd.Series(True, index=out_sample.index), 'baseline (all)')
    print("\n--- Baseline (slice 017's validated filter, no further refinement) ---")
    print_bucket(base_in)
    print_bucket(base_out)

    confluence_count = events['confluence_1d'].sum()
    print(f"\n(events with 1D confluence: {confluence_count} / {len(events)})")

    results = []
    results.append(evaluate_filter("1. 1D/4h structural confluence (+-3d)",
                                    in_sample, out_sample, base_in, base_out, 'confluence_1d'))
    results.append(evaluate_filter(f"2. RSI(14) extremity aligned (<{RSI_HOT_MAX}/>{RSI_COLD_MIN})",
                                    in_sample, out_sample, base_in, base_out, 'rsi_extreme'))
    results.append(evaluate_filter(f"3. ADX(14) strong trend (>={ADX_STRONG_THRESHOLD})",
                                    in_sample, out_sample, base_in, base_out, 'adx_strong'))

    print("\n" + "=" * 70)
    print("SUMMARY")
    confirmed = [r for r in results if r['verdict'] == 'confirmed']
    if confirmed:
        for r in confirmed:
            print(f"  CONFIRMED: {r['name']} -- "
                  f"out-of-sample win_rate={r['out_of_sample']['win_rate']:.1%}, "
                  f"n={r['out_of_sample']['n']}")
    else:
        print("  No candidate filter added a confirmed incremental edge beyond slice 017's baseline.")
    print("=" * 70)


if __name__ == '__main__':
    main()
