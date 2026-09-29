"""
Taker buy/sell flow como refinamiento Wyckoff (specs/021-wyckoff-taker-flow/), continuacion
de specs/017-wyckoff-edge-refinement/ y specs/020-orderflow-and-social-data-research/.

Binance expone en su endpoint crudo de klines (verificado directamente, ver research.md de
specs/020/) el volumen comprado agresivamente (taker) por vela -- CCXT lo descarta en su
fetch_ohlcv unificado. Este script lo recupera para calcular taker_buy_ratio en la vela de
ruptura de cada uno de los 330 eventos ya validados en slice 017, y prueba DOS hipotesis
declaradas de antemano (ver spec.md):

  1. Absorcion: ruptura dominada por el lado OPUESTO a la reversion (venta agresiva en un
     Spring, compra agresiva en un Upthrust) que termina siendo absorbida.
  2. Entrada agresiva: ruptura dominada por el mismo lado de la reversion (compradores ya
     entrando agresivamente durante el Spring, vendedores durante el Upthrust).

Mismo split cronologico 70/30 in-sample/out-of-sample que slices 017/019. Ningun filtro se
conecta a codigo de produccion (FR-004).

Uso:
    PYTHONPATH=/work/app python specs/021-wyckoff-taker-flow/test_taker_flow.py
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
HORIZON_CANDLES = 84  # 14 dias en velas de 4h
IN_SAMPLE_FRACTION = 0.7
MIN_SAMPLE = 30
ACTIONABLE_WIN_RATE = 0.60


def fetch_raw_klines_paginated(exchange, pair, since_ms, now_ms, limit=1000):
    """Klines crudas de Binance (no el fetch_ohlcv unificado de CCXT) -- conserva
    taker_buy_base_volume (columna 9), que fetch_ohlcv descarta."""
    symbol = exchange.market(pair)['id']
    all_rows = []
    since = since_ms
    while True:
        batch = exchange.publicGetKlines({
            'symbol': symbol, 'interval': '4h', 'startTime': since, 'limit': limit,
        })
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = int(batch[-1][0])
        time.sleep(exchange.rateLimit / 1000)
        if last_ts >= now_ms or len(batch) < limit:
            break
        since = last_ts + 1

    if not all_rows:
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                      'taker_buy_base_volume'])

    rows = []
    for r in all_rows:
        rows.append({
            'timestamp': int(r[0]), 'open': float(r[1]), 'high': float(r[2]),
            'low': float(r[3]), 'close': float(r[4]), 'volume': float(r[5]),
            'taker_buy_base_volume': float(r[9]),
        })
    df = pd.DataFrame(rows)
    df = df.drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)
    df = df[df['timestamp'] <= now_ms].reset_index(drop=True)
    return df


def fetch_all(exchange, months_back):
    now = datetime.now(timezone.utc)
    since_ms = int((now - timedelta(days=30 * months_back)).timestamp() * 1000)
    now_ms = int(now.timestamp() * 1000)
    data = {}
    for pair in BASKET:
        print(f"Fetching {pair} (4h, raw klines w/ taker volume)...", file=sys.stderr)
        try:
            df = fetch_raw_klines_paginated(exchange, pair, since_ms, now_ms)
        except Exception as e:
            print(f"  FAILED ({type(e).__name__}: {e}) -- skipping", file=sys.stderr)
            continue
        data[pair] = df
        print(f"  {len(df)} candles", file=sys.stderr)
    return data


def collect_events(basket_4h):
    records = []
    min_history = LOOKBACK + HORIZON_CANDLES + CONFIRM_WINDOW + 5

    for pair, df in basket_4h.items():
        if len(df) < min_history:
            continue

        closes = df['close'].values.astype(float)
        volume = df['volume'].values.astype(float)
        taker_buy = df['taker_buy_base_volume'].values.astype(float)
        timestamps = df['timestamp'].values

        with np.errstate(divide='ignore', invalid='ignore'):
            taker_buy_ratio = np.where(volume > 0, taker_buy / volume, np.nan)

        springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)

        # necesitamos el indice de la vela de RUPTURA (no solo la de confirmacion) para leer
        # el taker_buy_ratio en el momento real de la ruptura -- reconstruido igual que en
        # specs/019 (mismo soporte/resistencia con shift(1), sin tocar app/).
        ranges = WyckoffPrimitives.detect_trading_range(df, lookback=LOOKBACK)
        support, resistance = ranges['support'].values, ranges['resistance'].values
        lows, highs = df['low'].values.astype(float), df['high'].values.astype(float)

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
                continue  # mismo set ya validado en slice 017

            break_idx = None
            for k in range(max(0, i - CONFIRM_WINDOW), i):
                if direction == 'hot' and not np.isnan(support[k]) and lows[k] < support[k]:
                    break_idx = k
                    break
                if direction == 'cold' and not np.isnan(resistance[k]) and highs[k] > resistance[k]:
                    break_idx = k
                    break
            if break_idx is None:
                continue

            j = i + HORIZON_CANDLES
            if j >= len(closes):
                continue
            fwd = (closes[j] - closes[i]) / closes[i]
            expected_dir_return = fwd if direction == 'hot' else -fwd

            ratio = taker_buy_ratio[break_idx]
            if np.isnan(ratio):
                continue

            # Hipotesis 1 (absorcion): lado OPUESTO a la reversion domino la ruptura.
            absorption = (direction == 'hot' and ratio < 0.45) or (direction == 'cold' and ratio > 0.55)
            # Hipotesis 2 (entrada agresiva): lado IGUAL a la reversion ya dominaba la ruptura.
            aggressive_entry = (direction == 'hot' and ratio > 0.55) or (direction == 'cold' and ratio < 0.45)

            records.append({
                'pair': pair, 'timestamp': timestamps[i], 'direction': direction,
                'expected_dir_return': expected_dir_return,
                'taker_buy_ratio': ratio,
                'absorption': absorption, 'aggressive_entry': aggressive_entry,
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
    print(f"\n--- Hypothesis: {name} ---")
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
    exchange.load_markets()
    basket_4h = fetch_all(exchange, MONTHS_BACK)

    events = collect_events(basket_4h)
    events = events.sort_values('timestamp').reset_index(drop=True)
    print(f"\nTotal events with valid taker_buy_ratio: {len(events)}", file=sys.stderr)

    split_idx = int(len(events) * IN_SAMPLE_FRACTION)
    in_sample, out_sample = events.iloc[:split_idx], events.iloc[split_idx:]

    print("\n" + "=" * 70)
    print("TAKER BUY/SELL FLOW -- IN-SAMPLE / OUT-OF-SAMPLE")
    print("=" * 70)
    print(f"\nTotal events: {len(events)} | in-sample: {len(in_sample)} | "
          f"out-of-sample: {len(out_sample)}")
    print(f"taker_buy_ratio distribution: mean={events['taker_buy_ratio'].mean():.3f}, "
          f"median={events['taker_buy_ratio'].median():.3f}")

    base_in = evaluate_bucket(in_sample, pd.Series(True, index=in_sample.index), 'baseline (all)')
    base_out = evaluate_bucket(out_sample, pd.Series(True, index=out_sample.index), 'baseline (all)')
    print("\n--- Baseline (slice 017's validated filter, no further refinement) ---")
    print_bucket(base_in)
    print_bucket(base_out)

    results = []
    results.append(evaluate_filter("1. Absorption (taker opposite to reversal direction)",
                                    in_sample, out_sample, base_in, base_out, 'absorption'))
    results.append(evaluate_filter("2. Aggressive entry (taker same as reversal direction)",
                                    in_sample, out_sample, base_in, base_out, 'aggressive_entry'))

    print("\n" + "=" * 70)
    print("SUMMARY")
    confirmed = [r for r in results if r['verdict'] == 'confirmed']
    if confirmed:
        for r in confirmed:
            print(f"  CONFIRMED: {r['name']} -- "
                  f"out-of-sample win_rate={r['out_of_sample']['win_rate']:.1%}, "
                  f"n={r['out_of_sample']['n']}")
    else:
        print("  Neither hypothesis added a confirmed incremental edge beyond slice 017's baseline.")
    print("=" * 70)


if __name__ == '__main__':
    main()
