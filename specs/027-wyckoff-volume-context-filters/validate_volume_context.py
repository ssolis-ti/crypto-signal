"""
Filtros de contexto de volumen (CMF/PVT/NVI) sobre el edge Wyckoff
(specs/027-wyckoff-volume-context-filters/), continuacion de specs/026.

Reutiliza WyckoffPrimitives TAL CUAL desde app/ (mismos eventos que produccion:
Spring/Upthrust + volumen extremo >=2.5x, 4h) y anota cada evento con
CMF(20)/PVT/NVI (TA-Lib nativo, sin reimplementar) en la vela de confirmacion,
para ver si alguno mejora el baseline ya validado (specs/017/018/023).

No conecta nada a codigo de produccion (FR-006).

Uso:
    PYTHONPATH=/work/app python specs/027-wyckoff-volume-context-filters/validate_volume_context.py
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
CMF_PERIOD = 20
TREND_LOOKBACK = 20  # velas hacia atras para juzgar tendencia de PVT/NVI


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


def collect_events(basket_4h):
    records = []
    max_horizon = max(HORIZONS.values())
    min_history = LOOKBACK + CONFIRM_WINDOW + max_horizon + max(CMF_PERIOD, TREND_LOOKBACK) + 5

    for pair, df in basket_4h.items():
        if len(df) < min_history:
            print(f"Skipping {pair}: insufficient history ({len(df)} candles)", file=sys.stderr)
            continue

        closes = df['close'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        volumes = df['volume'].values.astype(float)
        timestamps = df['timestamp'].values

        cmf = talib.CMF(highs, lows, closes, volumes, timeperiod=CMF_PERIOD)
        pvt = talib.PVT(closes, volumes)
        nvi = talib.NVI(closes, volumes)

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

            j = i + max(HORIZONS.values())  # placeholder, se recalcula por horizonte abajo
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

            if i < TREND_LOOKBACK or np.isnan(pvt[i]) or np.isnan(pvt[i - TREND_LOOKBACK]):
                pvt_rising = None
            else:
                pvt_rising = pvt[i] > pvt[i - TREND_LOOKBACK]

            if i < TREND_LOOKBACK or np.isnan(nvi[i]) or np.isnan(nvi[i - TREND_LOOKBACK]):
                nvi_rising = None
            else:
                nvi_rising = nvi[i] > nvi[i - TREND_LOOKBACK]

            cmf_val = cmf[i] if not np.isnan(cmf[i]) else None

            row = {
                'pair': pair, 'timestamp': timestamps[i], 'direction': direction,
                'cmf_aligned': (cmf_val is not None) and (
                    (direction == 'hot' and cmf_val > 0) or (direction == 'cold' and cmf_val < 0)
                ),
                'pvt_aligned': (pvt_rising is not None) and (
                    (direction == 'hot' and pvt_rising) or (direction == 'cold' and not pvt_rising)
                ),
                'nvi_aligned': (nvi_rising is not None) and (
                    (direction == 'hot' and nvi_rising) or (direction == 'cold' and not nvi_rising)
                ),
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


def evaluate_candidate(name, events, filter_fn, baseline_out):
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

        base_wr = baseline_out[h_label]['win_rate']
        if in_b['insufficient'] or out_b['insufficient']:
            verdict = 'insufficient_sample'
        elif (out_b['win_rate'] >= ACTIONABLE_WIN_RATE and out_b['p'] < 0.05
              and (base_wr is None or out_b['win_rate'] > base_wr)):
            verdict = 'confirmed'
            any_confirmed = True
        else:
            verdict = 'did_not_replicate'
        per_horizon[h_label] = {'in_sample': in_b, 'out_of_sample': out_b, 'verdict': verdict}

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
    out_sample_all = events_sorted.iloc[split_idx:]

    print("\n" + "=" * 78)
    print("BASELINE (produccion actual: Spring/Upthrust + volumen extremo, sin filtro adicional)")
    print("=" * 78)
    baseline_out = {}
    for h_label in HORIZONS:
        b = evaluate_bucket(out_sample_all, pd.Series(True, index=out_sample_all.index),
                             f'ret_{h_label}', f'out-sample {h_label}')
        print_bucket(b)
        baseline_out[h_label] = b

    results = []
    results.append(evaluate_candidate(
        "1. CMF(20) alineado con direccion", events,
        lambda d: d['cmf_aligned'] == True, baseline_out  # noqa: E712
    ))
    results.append(evaluate_candidate(
        "2. PVT en tendencia alineada", events,
        lambda d: d['pvt_aligned'] == True, baseline_out  # noqa: E712
    ))
    results.append(evaluate_candidate(
        "3. NVI en tendencia alineada", events,
        lambda d: d['nvi_aligned'] == True, baseline_out  # noqa: E712
    ))

    print("\n" + "=" * 78)
    print("SUMMARY")
    confirmed = [r for r in results if r['overall'] == 'confirmed']
    if confirmed:
        for r in confirmed:
            print(f"  CONFIRMED (mejora sobre baseline): {r['name']}")
            for h_label, v in r['per_horizon'].items():
                if v['verdict'] == 'confirmed':
                    ob = v['out_of_sample']
                    print(f"      -> {h_label}: win_rate={ob['win_rate']:.1%}, n={ob['n']}, p={ob['p']:.4f}")
    else:
        print("  Ningun candidato mejoro el baseline de produccion con significancia "
              f"(bar: win_rate>={ACTIONABLE_WIN_RATE:.0%}, p<0.05, n>={MIN_SAMPLE}, y mayor que baseline).")
    print("=" * 78)


if __name__ == '__main__':
    main()
