"""
Patrones de vela como filtro adicional sobre el edge Wyckoff
(specs/029-wyckoff-candle-pattern-filter/), continuacion de specs/026/027.

Reutiliza WyckoffPrimitives TAL CUAL desde app/ (mismos eventos que
produccion: Spring/Upthrust + volumen extremo >=2.5x, 4h) y anota cada evento
con los patrones CDL* de TA-Lib en la vela de confirmacion, para ver si
alguno mejora el baseline ya validado (specs/017/018/023).

Aplica la leccion de spec 027: reporta baseline in-sample Y out-of-sample
lado a lado, y solo marca "confirmed" si el lift es consistente en AMBOS
tramos (no solo si el out-of-sample pasa la vara mecanica aislado).

No conecta nada a codigo de produccion (FR-005).

Uso:
    PYTHONPATH=/work/app python specs/029-wyckoff-candle-pattern-filter/validate_candle_patterns.py
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
TIMEFRAME = '4h'
MONTHS_BACK = 10
LOOKBACK = 20
CONFIRM_WINDOW = 3
EXTREME_VOLUME_THRESHOLD = 2.5
HORIZONS = {'24h': 6, '72h': 18, '7d': 42, '14d': 84}
IN_SAMPLE_FRACTION = 0.7
MIN_SAMPLE = 30
ACTIONABLE_WIN_RATE = 0.60

ALL_CDL_NAMES = talib.get_function_groups()['Pattern Recognition']
CORE_CDL_NAMES = [
    'CDLENGULFING', 'CDLHAMMER', 'CDLINVERTEDHAMMER', 'CDLHANGINGMAN',
    'CDLSHOOTINGSTAR', 'CDLMORNINGSTAR', 'CDLEVENINGSTAR', 'CDLPIERCING',
    'CDLDARKCLOUDCOVER', 'CDLMORNINGDOJISTAR', 'CDLEVENINGDOJISTAR',
]


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
        if len(df) == 0:
            print(f"  0 candles -- skipping", file=sys.stderr)
            continue
        data[pair] = df
        print(f"  {len(df)} candles", file=sys.stderr)
    return data


def compute_pattern_matrix(df, names):
    o = df['open'].values.astype(float)
    h = df['high'].values.astype(float)
    l = df['low'].values.astype(float)
    c = df['close'].values.astype(float)
    matrix = {}
    for name in names:
        fn = getattr(talib, name)
        matrix[name] = fn(o, h, l, c)
    return matrix


def collect_events(basket_4h):
    records = []
    max_horizon = max(HORIZONS.values())
    min_history = LOOKBACK + CONFIRM_WINDOW + max_horizon + 5

    for pair, df in basket_4h.items():
        if len(df) < min_history:
            print(f"Skipping {pair}: insufficient history ({len(df)} candles)", file=sys.stderr)
            continue

        closes = df['close'].values.astype(float)
        timestamps = df['timestamp'].values

        all_patterns = compute_pattern_matrix(df, ALL_CDL_NAMES)
        core_patterns = {k: all_patterns[k] for k in CORE_CDL_NAMES}

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
                continue  # mismo baseline que produccion (specs/023)

            valid = True
            rets = {}
            for h_label, h_candles in HORIZONS.items():
                jj = i + h_candles
                if jj >= len(closes):
                    valid = False
                    break
                fwd = (closes[jj] - closes[i]) / closes[i]
                rets[f'ret_{h_label}'] = fwd if direction == 'hot' else -fwd
            if not valid:
                continue

            def any_aligned(pattern_dict):
                for values in pattern_dict.values():
                    v = values[i]
                    if v == 0:
                        continue
                    if direction == 'hot' and v > 0:
                        return True
                    if direction == 'cold' and v < 0:
                        return True
                return False

            row = {
                'pair': pair, 'timestamp': timestamps[i], 'direction': direction,
                'any_pattern_aligned': any_aligned(all_patterns),
                'core_pattern_aligned': any_aligned(core_patterns),
            }
            row.update(rets)
            records.append(row)

    return pd.DataFrame(records)


def win_rate_z_test(n, win_rate, null_p=0.5):
    if n == 0:
        return 0.0, 1.0
    se = math.sqrt(null_p * (1 - null_p) / n)
    z = (win_rate - null_p) / se
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, p_value


def evaluate_bucket(df, mask, ret_col, label):
    bucket = df[mask]
    n = len(bucket)
    if n < MIN_SAMPLE:
        return {'label': label, 'n': n, 'win_rate': None, 'mean': None, 'insufficient': True}
    win_rate = (bucket[ret_col] > 0).mean()
    mean = bucket[ret_col].mean()
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


def evaluate_candidate(name, events, filter_fn, baseline_in, baseline_out):
    events = events.sort_values('timestamp').reset_index(drop=True)
    split_idx = int(len(events) * IN_SAMPLE_FRACTION)
    in_sample, out_sample = events.iloc[:split_idx], events.iloc[split_idx:]

    print(f"\n--- Candidate: {name} ---")
    in_mask = filter_fn(in_sample)
    out_mask = filter_fn(out_sample)
    print(f"    in-sample matching: {in_mask.sum()}/{len(in_sample)} | "
          f"out-of-sample matching: {out_mask.sum()}/{len(out_sample)}")

    any_confirmed = False
    per_horizon = {}
    for h_label in HORIZONS:
        ret_col = f'ret_{h_label}'
        in_b = evaluate_bucket(in_sample, in_mask, ret_col, f'in-sample  {h_label}')
        out_b = evaluate_bucket(out_sample, out_mask, ret_col, f'out-sample {h_label}')
        print_bucket(in_b)
        print_bucket(out_b)

        base_in_wr = baseline_in[h_label]['win_rate']
        base_out_wr = baseline_out[h_label]['win_rate']

        if in_b['insufficient'] or out_b['insufficient']:
            verdict = 'insufficient_sample'
        else:
            lift_in = (base_in_wr is not None) and (in_b['win_rate'] > base_in_wr)
            lift_out = (base_out_wr is not None) and (out_b['win_rate'] > base_out_wr)
            meets_bar = out_b['win_rate'] >= ACTIONABLE_WIN_RATE and out_b['p'] < 0.05
            if meets_bar and lift_in and lift_out:
                verdict = 'confirmed'
                any_confirmed = True
            elif meets_bar and not lift_in:
                verdict = 'inconsistent_in_sample_worse'  # spec 027's NVI trap
            else:
                verdict = 'did_not_replicate'
        per_horizon[h_label] = {'in_sample': in_b, 'out_of_sample': out_b, 'verdict': verdict}
        print(f"      -> baseline in={base_in_wr}, out={base_out_wr} | verdict={verdict}")

    overall = 'confirmed' if any_confirmed else 'did_not_replicate'
    if all(v['verdict'] == 'insufficient_sample' for v in per_horizon.values()):
        overall = 'insufficient_sample'
    print(f"    OVERALL VERDICT: {overall}")
    return {'name': name, 'per_horizon': per_horizon, 'overall': overall}


def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    basket_4h = fetch_all(exchange, TIMEFRAME, MONTHS_BACK)

    events = collect_events(basket_4h)
    print(f"\nTotal qualifying events (volume>=2.5x, same as production): {len(events)}", file=sys.stderr)

    events_sorted = events.sort_values('timestamp').reset_index(drop=True)
    split_idx = int(len(events_sorted) * IN_SAMPLE_FRACTION)
    in_sample_all = events_sorted.iloc[:split_idx]
    out_sample_all = events_sorted.iloc[split_idx:]

    print("\n" + "=" * 78)
    print("BASELINE (produccion actual: Spring/Upthrust + volumen extremo, sin filtro adicional)")
    print("=" * 78)
    baseline_in, baseline_out = {}, {}
    for h_label in HORIZONS:
        bi = evaluate_bucket(in_sample_all, pd.Series(True, index=in_sample_all.index),
                              f'ret_{h_label}', f'in-sample  {h_label}')
        bo = evaluate_bucket(out_sample_all, pd.Series(True, index=out_sample_all.index),
                              f'ret_{h_label}', f'out-sample {h_label}')
        print_bucket(bi)
        print_bucket(bo)
        baseline_in[h_label] = bi
        baseline_out[h_label] = bo

    results = []
    results.append(evaluate_candidate(
        "1. Cualquier patron CDL* reconocido, alineado con direccion", events,
        lambda d: d['any_pattern_aligned'] == True, baseline_in, baseline_out  # noqa: E712
    ))
    results.append(evaluate_candidate(
        "2. Patrones de reversion 'core' alineados", events,
        lambda d: d['core_pattern_aligned'] == True, baseline_in, baseline_out  # noqa: E712
    ))

    print("\n" + "=" * 78)
    print("SUMMARY")
    confirmed = [r for r in results if r['overall'] == 'confirmed']
    if confirmed:
        for r in confirmed:
            print(f"  CONFIRMED (lift consistente en ambos tramos): {r['name']}")
            for h_label, v in r['per_horizon'].items():
                if v['verdict'] == 'confirmed':
                    ob = v['out_of_sample']
                    print(f"      -> {h_label}: win_rate={ob['win_rate']:.1%}, n={ob['n']}, p={ob['p']:.4f}")
    else:
        print("  Ningun candidato mostro lift consistente sobre el baseline en ambos tramos.")
    print("=" * 78)


if __name__ == '__main__':
    main()
