"""
Backtest de validacion historica para Spring/Upthrust de Wyckoff
(specs/015-wyckoff-historical-validation/).

A diferencia de specs/007 y specs/011 (que validaban el score 0-100 de SignalEnhancer),
este script valida el patron de precio CRUDO -- Spring/Upthrust tal como lo detecta
WyckoffPrimitives (specs/014-.../) -- independiente de cualquier formula de scoring,
porque el recuerdo del operador ("alerta HOT -> +20-30% en 1-2 semanas") es sobre la
senal cruda, no sobre un tier de calidad. Usa las mismas funciones reales importadas
de app/, sin reimplementar la deteccion.

Horizontes pre-declarados (FR-003): 24h, 72h (comparables con specs/007/011) y
7d/14d (para chequear directamente el recuerdo del operador).

Uso:
    PYTHONPATH=/work/app python specs/015-wyckoff-historical-validation/validate_wyckoff_springs.py
"""
import math
import sys
import time
import random
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
TIMEFRAME = '4h'
MONTHS_BACK = 10
LOOKBACK = 20
CONFIRM_WINDOW = 3
HORIZONS = {'24h': 6, '72h': 18, '7d': 42, '14d': 84}
VOLUME_CONFIRMED_THRESHOLD = 1.5  # break_relative_volume >= esto = "ruptura con volumen"
N_PERMUTATIONS = 2000
RANDOM_SEED = 42
CLAIM_LOW, CLAIM_HIGH = 20.0, 30.0  # recuerdo del operador, en % (FR-004)


def fetch_ohlcv_paginated(exchange, pair, since_ms, now_ms, limit=1000):
    all_rows = []
    since = since_ms
    while True:
        batch = exchange.fetch_ohlcv(pair, timeframe=TIMEFRAME, since=since, limit=limit)
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


def fetch_all_pairs(exchange, months_back):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30 * months_back)
    since_ms = int(since.timestamp() * 1000)
    now_ms = int(now.timestamp() * 1000)

    data = {}
    for pair in BASKET:
        print(f"Fetching {pair}...", file=sys.stderr)
        try:
            df = fetch_ohlcv_paginated(exchange, pair, since_ms, now_ms)
        except Exception as e:
            print(f"  FAILED ({type(e).__name__}: {e}) -- skipping pair", file=sys.stderr)
            continue
        data[pair] = df
        print(f"  {len(df)} candles", file=sys.stderr)
    return data


def collect_events(all_data):
    records = []
    min_history = LOOKBACK + max(HORIZONS.values()) + CONFIRM_WINDOW + 5

    for pair, df in all_data.items():
        if len(df) < min_history:
            print(f"Skipping {pair}: insufficient history ({len(df)} candles)", file=sys.stderr)
            continue

        closes = df['close'].values.astype(float)
        timestamps = df['timestamp'].values

        springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK,
                                                     confirm_window=CONFIRM_WINDOW)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK,
                                                         confirm_window=CONFIRM_WINDOW)

        for i in range(len(df)):
            direction = None
            break_rv = confirm_rv = None
            if bool(springs['is_spring'].iloc[i]):
                direction = 'hot'
                break_rv = springs['break_relative_volume'].iloc[i]
                confirm_rv = springs['confirm_relative_volume'].iloc[i]
            elif bool(upthrusts['is_upthrust'].iloc[i]):
                direction = 'cold'
                break_rv = upthrusts['break_relative_volume'].iloc[i]
                confirm_rv = upthrusts['confirm_relative_volume'].iloc[i]

            if direction is None:
                continue

            record = {
                'pair': pair, 'timestamp': timestamps[i], 'direction': direction,
                'break_relative_volume': break_rv, 'confirm_relative_volume': confirm_rv,
            }
            for label, n_candles in HORIZONS.items():
                j = i + n_candles
                if j < len(closes):
                    fwd = (closes[j] - closes[i]) / closes[i]
                    record[f'expected_dir_return_{label}'] = fwd if direction == 'hot' else -fwd
                else:
                    record[f'expected_dir_return_{label}'] = None
            records.append(record)

    return pd.DataFrame(records)


def permutation_p_value(x, y, n=N_PERMUTATIONS, seed=RANDOM_SEED):
    rng = random.Random(seed)
    x_ranks = pd.Series(x).rank().values
    y_ranks = list(pd.Series(y).rank().values)
    real_corr = np.corrcoef(x_ranks, y_ranks)[0, 1]

    count = 0
    for _ in range(n):
        rng.shuffle(y_ranks)
        shuffled = np.corrcoef(x_ranks, y_ranks)[0, 1]
        if abs(shuffled) >= abs(real_corr):
            count += 1
    return real_corr, (count + 1) / (n + 1)


def win_rate_z_test(n, win_rate, null_p=0.5):
    """
    Test de proporcion contra un baseline (50/50), aproximacion normal -- evita
    depender de scipy para un solo script (mismo criterio que en specs/007/011).
    Retorna (z, p_value_dos_colas).
    """
    if n == 0:
        return 0.0, 1.0
    se = math.sqrt(null_p * (1 - null_p) / n)
    z = (win_rate - null_p) / se
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, p_value


def report(events_df):
    print("\n" + "=" * 70)
    print("WYCKOFF SPRING/UPTHRUST VALIDATION REPORT")
    print("=" * 70)

    print(f"\nTotal events: {len(events_df)}")
    if len(events_df) == 0:
        print("No events detected -- nothing to report.")
        return
    print(events_df['direction'].value_counts().to_string())

    volume_confirmed = events_df['break_relative_volume'] >= VOLUME_CONFIRMED_THRESHOLD
    print(f"\nVolume-confirmed breaks (break_relative_volume >= {VOLUME_CONFIRMED_THRESHOLD}): "
          f"{volume_confirmed.sum()} / {len(events_df)}")

    for label in HORIZONS:
        col = f'expected_dir_return_{label}'
        valid = events_df.dropna(subset=[col])
        print(f"\n--- Horizon {label} (n={len(valid)}) ---")

        for bucket_name, mask in [('ALL', pd.Series(True, index=valid.index)),
                                   ('volume-confirmed', valid['break_relative_volume'] >= VOLUME_CONFIRMED_THRESHOLD),
                                   ('not volume-confirmed', valid['break_relative_volume'] < VOLUME_CONFIRMED_THRESHOLD)]:
            bucket = valid[mask]
            n = len(bucket)
            if n < 10:
                print(f"  {bucket_name}: n={n} -- INSUFFICIENT SAMPLE")
                continue
            mean = bucket[col].mean()
            median = bucket[col].median()
            win_rate = (bucket[col] > 0).mean()
            z, p_wr = win_rate_z_test(n, win_rate)
            sig = " *SIGNIFICANT vs 50%*" if p_wr < 0.05 else ""
            print(f"  {bucket_name}: n={n:4d} | mean={mean:+.4%} | median={median:+.4%} | "
                  f"win_rate={win_rate:.1%} (z={z:+.2f}, p={p_wr:.4f}){sig}")

        if len(valid) >= 20:
            corr, p_value = permutation_p_value(
                valid['break_relative_volume'].fillna(0).values, valid[col].values
            )
            print(f"  Spearman-rank corr(break_relative_volume, {col}) = {corr:+.4f}, "
                  f"permutation p-value = {p_value:.4f}")
        else:
            print(f"  INSUFFICIENT SAMPLE for correlation test (n={len(valid)} < 20)")

    # Fact-check explicito del recuerdo del operador (FR-004)
    print("\n" + "-" * 70)
    print(f"FACT-CHECK: recuerdo del operador = HOT -> +{CLAIM_LOW:.0f}% a +{CLAIM_HIGH:.0f}% "
          f"en 1-2 semanas")
    for label in ['7d', '14d']:
        col = f'expected_dir_return_{label}'
        hot = events_df[(events_df['direction'] == 'hot')].dropna(subset=[col])
        if len(hot) < 10:
            print(f"  {label} (solo HOT): n={len(hot)} -- INSUFFICIENT SAMPLE para el fact-check")
            continue
        mean_pct = hot[col].mean() * 100
        median_pct = hot[col].median() * 100
        pct_in_claim_range = ((hot[col] * 100 >= CLAIM_LOW) & (hot[col] * 100 <= CLAIM_HIGH)).mean() * 100
        replicates = mean_pct >= CLAIM_LOW or median_pct >= CLAIM_LOW
        print(f"  {label} (solo HOT, n={len(hot)}): mean={mean_pct:+.2f}%, median={median_pct:+.2f}%, "
              f"{pct_in_claim_range:.1f}% de eventos cayeron dentro del rango reclamado "
              f"({'REPLICA' if replicates else 'NO REPLICA'} la magnitud del recuerdo)")

    print("\n" + "=" * 70)


def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    all_data = fetch_all_pairs(exchange, MONTHS_BACK)
    events_df = collect_events(all_data)
    print(f"\nTotal events: {len(events_df)}", file=sys.stderr)
    report(events_df)


if __name__ == '__main__':
    main()
