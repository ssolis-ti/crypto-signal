"""
Busqueda de un edge Wyckoff realmente accionable (specs/017-wyckoff-edge-refinement/),
continuacion de specs/015-wyckoff-historical-validation/.

Slice 015 encontro un win-rate significativo (53-55%) pero demasiado chico para alertar
"opera esto" por Telegram. Este script prueba 4 refinamientos motivados por la teoria de
Wyckoff, con un split cronologico in-sample/out-of-sample estricto (70/30) para evitar
reportar como "hallazgo" algo que solo es sobreajuste al propio dataset -- ver research.md
en spec.md y plan.md. Ningun filtro se conecta a codigo de produccion aqui (FR-004).

Uso:
    PYTHONPATH=/work/app python specs/017-wyckoff-edge-refinement/search_wyckoff_edge.py
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
HORIZON_LABEL, HORIZON_CANDLES = '14d', 84  # el horizonte que el operador realmente le importa
EXTREME_VOLUME_THRESHOLD = 2.5
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


def pct_change_24h(closes, i, lookback=6):
    if i < lookback:
        return None
    prev = closes[i - lookback]
    if prev == 0 or np.isnan(prev) or np.isnan(closes[i]):
        return None
    return (closes[i] - prev) / prev * 100.0


def determine_trend(change_24h, bullish=1.5, bearish=-1.0):
    if change_24h is None:
        return 'neutral'
    if change_24h >= bullish:
        return 'bullish'
    elif change_24h <= bearish:
        return 'bearish'
    return 'neutral'


def find_break_index(lows, highs, support, resistance, confirm_index, confirm_window, direction):
    for i in range(max(0, confirm_index - confirm_window), confirm_index):
        if direction == 'hot':
            level = support[i]
            if not np.isnan(level) and lows[i] < level:
                return i
        else:
            level = resistance[i]
            if not np.isnan(level) and highs[i] > level:
                return i
    return None


def build_daily_trend_lookup(daily_df):
    """EMA(50) diario; retorna (timestamps_ordenados, closes, ema50) para busqueda por fecha."""
    closes = daily_df['close'].values.astype(float)
    ema50 = talib.EMA(closes, timeperiod=50)
    return daily_df['timestamp'].values, closes, ema50


def htf_bias_at(daily_ts, daily_closes, daily_ema50, event_ts):
    """Ultima vela diaria CERRADA antes o en event_ts (sin lookahead)."""
    idx = np.searchsorted(daily_ts, event_ts, side='right') - 1
    if idx < 0 or idx >= len(daily_closes) or np.isnan(daily_ema50[idx]):
        return None
    return 'bullish' if daily_closes[idx] > daily_ema50[idx] else 'bearish'


def collect_events(basket_4h, basket_1d, btc_trend_lookup):
    records = []
    min_history = LOOKBACK + HORIZON_CANDLES + CONFIRM_WINDOW + 5
    btc_ts_to_trend = btc_trend_lookup

    for pair, df in basket_4h.items():
        if len(df) < min_history:
            print(f"Skipping {pair}: insufficient history ({len(df)} candles)", file=sys.stderr)
            continue

        closes = df['close'].values.astype(float)
        lows = df['low'].values.astype(float)
        highs = df['high'].values.astype(float)
        timestamps = df['timestamp'].values

        ranges = WyckoffPrimitives.detect_trading_range(df, lookback=LOOKBACK)
        support, resistance = ranges['support'].values, ranges['resistance'].values
        range_width_pct = ranges['range_width_pct'].values
        climax_flags = WyckoffPrimitives.is_climax(df).values

        springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)

        daily = basket_1d.get(pair)
        daily_ts, daily_closes, daily_ema50 = build_daily_trend_lookup(daily) if daily is not None and len(daily) > 55 else (None, None, None)

        for i in range(len(df)):
            direction = None
            if bool(springs['is_spring'].iloc[i]):
                direction, flags = 'hot', springs
            elif bool(upthrusts['is_upthrust'].iloc[i]):
                direction, flags = 'cold', upthrusts
            else:
                continue

            confirm_index = i
            break_index = find_break_index(lows, highs, support, resistance,
                                            confirm_index, CONFIRM_WINDOW, direction)

            j = confirm_index + HORIZON_CANDLES
            if j >= len(closes):
                continue
            fwd = (closes[j] - closes[confirm_index]) / closes[confirm_index]
            expected_dir_return = fwd if direction == 'hot' else -fwd

            htf_bias = None
            if daily_ts is not None:
                htf_bias = htf_bias_at(daily_ts, daily_closes, daily_ema50, timestamps[confirm_index])
            htf_aligned = (
                (direction == 'hot' and htf_bias == 'bullish') or
                (direction == 'cold' and htf_bias == 'bearish')
            ) if htf_bias is not None else None

            btc_trend = btc_ts_to_trend.get(timestamps[confirm_index])
            btc_aligned = (
                (direction == 'hot' and btc_trend != 'bearish') or
                (direction == 'cold' and btc_trend != 'bullish')
            ) if btc_trend is not None else None

            is_climax_at_break = bool(climax_flags[break_index]) if break_index is not None else False
            break_rel_vol = flags['break_relative_volume'].iloc[i]
            range_width_at_confirm = range_width_pct[confirm_index]

            records.append({
                'pair': pair, 'timestamp': timestamps[confirm_index], 'direction': direction,
                'expected_dir_return': expected_dir_return,
                'htf_aligned': htf_aligned, 'btc_aligned': btc_aligned,
                'is_climax_at_break': is_climax_at_break,
                'extreme_volume': (break_rel_vol >= EXTREME_VOLUME_THRESHOLD) if not pd.isna(break_rel_vol) else False,
                'range_width_pct': range_width_at_confirm,
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


def evaluate_filter(name, in_sample, out_sample, mask_fn):
    print(f"\n--- Filter: {name} (horizon {HORIZON_LABEL}) ---")
    in_mask = mask_fn(in_sample)
    out_mask = mask_fn(out_sample)

    in_b = evaluate_bucket(in_sample, in_mask, 'in-sample (filtered)')
    out_b = evaluate_bucket(out_sample, out_mask, 'out-of-sample (filtered)')
    print_bucket(in_b)
    print_bucket(out_b)

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

    btc_df = basket_4h['BTC/USDT']
    btc_closes = btc_df['close'].values.astype(float)
    btc_ts = btc_df['timestamp'].values
    btc_ts_to_trend = {}
    for i in range(len(btc_closes)):
        change = pct_change_24h(btc_closes, i)
        btc_ts_to_trend[btc_ts[i]] = determine_trend(change)

    events = collect_events(basket_4h, basket_1d, btc_ts_to_trend)
    events = events.sort_values('timestamp').reset_index(drop=True)
    print(f"\nTotal events: {len(events)}", file=sys.stderr)

    split_idx = int(len(events) * IN_SAMPLE_FRACTION)
    in_sample, out_sample = events.iloc[:split_idx], events.iloc[split_idx:]

    print("\n" + "=" * 70)
    print("WYCKOFF EDGE SEARCH -- IN-SAMPLE / OUT-OF-SAMPLE")
    print("=" * 70)
    print(f"\nTotal events: {len(events)} | in-sample: {len(in_sample)} | "
          f"out-of-sample: {len(out_sample)}")

    baseline_in = evaluate_bucket(in_sample, pd.Series(True, index=in_sample.index), 'baseline (all)')
    baseline_out = evaluate_bucket(out_sample, pd.Series(True, index=out_sample.index), 'baseline (all)')
    print("\n--- Baseline (no filter) ---")
    print_bucket(baseline_in)
    print_bucket(baseline_out)

    results = []
    results.append(evaluate_filter(
        "1. HTF (1D EMA50) trend alignment", in_sample, out_sample,
        lambda d: d['htf_aligned'] == True  # noqa: E712
    ))

    median_width_in_sample = in_sample['range_width_pct'].median()
    print(f"\n(range_width_pct median, in-sample only: {median_width_in_sample:.2f}%)")
    results.append(evaluate_filter(
        "2. Range compression (below in-sample median width)", in_sample, out_sample,
        lambda d: d['range_width_pct'] < median_width_in_sample
    ))

    results.append(evaluate_filter(
        f"3. Extreme break volume (relative_volume >= {EXTREME_VOLUME_THRESHOLD})",
        in_sample, out_sample,
        lambda d: d['extreme_volume'] == True  # noqa: E712
    ))

    results.append(evaluate_filter(
        "4. BTC 4h regime alignment", in_sample, out_sample,
        lambda d: d['btc_aligned'] == True  # noqa: E712
    ))

    print("\n" + "=" * 70)
    print("SUMMARY")
    confirmed = [r for r in results if r['verdict'] == 'confirmed']
    if confirmed:
        for r in confirmed:
            print(f"  CONFIRMED: {r['name']} -- "
                  f"out-of-sample win_rate={r['out_of_sample']['win_rate']:.1%}, "
                  f"n={r['out_of_sample']['n']}")
    else:
        print("  No candidate filter survived the out-of-sample check "
              f"(bar: win_rate >= {ACTIONABLE_WIN_RATE:.0%}, p<0.05, n>={MIN_SAMPLE}).")
    print("=" * 70)


if __name__ == '__main__':
    main()
