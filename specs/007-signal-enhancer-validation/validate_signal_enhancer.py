"""
Backtest de validacion historica para SignalEnhancer (specs/007-signal-enhancer-validation/).

Research artifact -- NO es parte de la aplicacion en ejecucion (ver plan.md Structure Decision).
Reutiliza la funcion real SignalEnhancer._calculate_quality (no la reimplementa) contra datos
OHLCV historicos reales obtenidos por CCXT (solo lectura), replicando el disparador de senal
real de produccion (config-clean.yml: RSI(14) en velas 4h, hot<30, cold>70).

Uso (ver quickstart.md):
    PYTHONPATH=/work/app python specs/007-signal-enhancer-validation/validate_signal_enhancer.py
"""
import sys
import time
import random
from datetime import datetime, timezone, timedelta

import ccxt
import numpy as np
import pandas as pd
import talib

from analysis.signal_enhancer import SignalEnhancer
from analysis.market_context import MarketContextData, AltStrengthData


# ─────────────────────────────────────────
# Configuracion (fija ANTES de correr -- FR-005: horizontes pre-declarados)
# ─────────────────────────────────────────
REFERENCE_PAIR = 'BTC/USDT'
BASKET = [
    'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT',
    'BCH/USDT', 'ATOM/USDT', 'NEAR/USDT', 'MATIC/USDT',
]
TIMEFRAME = '4h'
RSI_PERIOD = 14
EMA_PERIOD = 99
HOT_THRESHOLD = 30
COLD_THRESHOLD = 70
HORIZONS = {'24h': 6, '72h': 18}  # en velas de 4h
MONTHS_BACK = 10
N_PERMUTATIONS = 2000
RANDOM_SEED = 42


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


def fetch_all_pairs(exchange):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30 * MONTHS_BACK)
    since_ms = int(since.timestamp() * 1000)
    now_ms = int(now.timestamp() * 1000)

    data = {}
    for pair in [REFERENCE_PAIR] + BASKET:
        print(f"Fetching {pair}...", file=sys.stderr)
        try:
            df = fetch_ohlcv_paginated(exchange, pair, since_ms, now_ms)
        except Exception as e:
            print(f"  FAILED ({type(e).__name__}: {e}) -- skipping pair", file=sys.stderr)
            continue
        data[pair] = df
        print(f"  {len(df)} candles", file=sys.stderr)
    return data


def compute_indicators(df):
    closes = df['close'].values.astype(float)
    rsi = talib.RSI(closes, timeperiod=RSI_PERIOD)
    ema99 = talib.EMA(closes, timeperiod=EMA_PERIOD)
    macd, macdsignal, macdhist = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
    return rsi, ema99, macdhist


def pct_change_24h(closes, i, lookback=6):
    """% cambio sobre 24h (6 velas de 4h), mismo horizonte que ticker['percentage'] en produccion."""
    if i < lookback:
        return None
    prev = closes[i - lookback]
    if prev == 0 or np.isnan(prev) or np.isnan(closes[i]):
        return None
    return (closes[i] - prev) / prev * 100.0


def build_breadth_table(all_data):
    """DataFrame timestamp -> %cambio 24h por par de la canasta (proxy de mercado, ver research.md)."""
    frames = {}
    for pair, df in all_data.items():
        closes = df['close'].values.astype(float)
        changes = [pct_change_24h(closes, i) for i in range(len(closes))]
        s = pd.Series(changes, index=df['timestamp'].values, name=pair)
        frames[pair] = s
    breadth = pd.DataFrame(frames)
    return breadth


def sentiment_for_row(row, btc_change):
    values = row.dropna()
    gainers = (values > 0).sum()
    losers = (values <= 0).sum()
    ratio = gainers / max(losers, 1)
    if ratio > 1.5 and btc_change is not None and btc_change > 1:
        return 'risk_on'
    elif ratio < 0.7 and btc_change is not None and btc_change < -1:
        return 'risk_off'
    return 'neutral'


def determine_trend(change_24h, bullish=1.5, bearish=-1.0):
    if change_24h is None:
        return 'neutral'
    if change_24h >= bullish:
        return 'bullish'
    elif change_24h <= bearish:
        return 'bearish'
    return 'neutral'


def relative_strength(btc_change, alt_change):
    if btc_change is None or alt_change is None:
        return 1.0
    if abs(btc_change) < 0.01:
        return 1.0 if abs(alt_change) < 0.01 else (2.0 if alt_change > 0 else 0.5)
    return (1 + alt_change / 100) / (1 + btc_change / 100)


def detect_events(rsi):
    """Un evento por cruce (no uno por vela en zona extrema) -- ver research.md."""
    events = []
    for i in range(1, len(rsi)):
        if np.isnan(rsi[i - 1]) or np.isnan(rsi[i]):
            continue
        if rsi[i - 1] >= HOT_THRESHOLD and rsi[i] < HOT_THRESHOLD:
            events.append((i, 'hot'))
        elif rsi[i - 1] <= COLD_THRESHOLD and rsi[i] > COLD_THRESHOLD:
            events.append((i, 'cold'))
    return events


def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    all_data = fetch_all_pairs(exchange)

    btc_df = all_data[REFERENCE_PAIR]
    btc_closes = btc_df['close'].values.astype(float)
    btc_ts_to_idx = {ts: i for i, ts in enumerate(btc_df['timestamp'].values)}

    breadth = build_breadth_table(all_data)

    enhancer = SignalEnhancer(market_context=None, settings=None)  # defaults == config-clean.yml

    records = []
    min_warmup = max(EMA_PERIOD, RSI_PERIOD) + 1

    for pair in BASKET:
        if pair not in all_data:
            continue
        df = all_data[pair]
        if len(df) < min_warmup + max(HORIZONS.values()) + 10:
            print(f"Skipping {pair}: insufficient history ({len(df)} candles)", file=sys.stderr)
            continue

        closes = df['close'].values.astype(float)
        timestamps = df['timestamp'].values
        rsi, ema99, macdhist = compute_indicators(df)
        events = detect_events(rsi)

        for i, direction in events:
            if i < min_warmup:
                continue

            ts = timestamps[i]
            btc_i = btc_ts_to_idx.get(ts)
            if btc_i is None:
                continue

            btc_change = pct_change_24h(btc_closes, btc_i)
            alt_change = pct_change_24h(closes, i)
            btc_trend = determine_trend(btc_change)

            if ts in breadth.index:
                row = breadth.loc[ts]
                sentiment = sentiment_for_row(row, btc_change)
            else:
                sentiment = 'neutral'

            alt = AltStrengthData(
                symbol=pair,
                alt_change_24h=alt_change or 0.0,
                btc_change_24h=btc_change or 0.0,
                relative_strength=relative_strength(btc_change, alt_change),
            )

            context_data = {
                'close': closes[i],
                'ema_99': ema99[i] if not np.isnan(ema99[i]) else 0,
                'macd_hist': macdhist[i] if not np.isnan(macdhist[i]) else 0,
            }

            quality, confidence, note, score = enhancer._calculate_quality(
                signal_type=direction,
                btc_trend=btc_trend,
                alt_strength=alt,
                sentiment=sentiment,
                rsi_value=rsi[i],
                context_data=context_data,
            )

            record = {
                'pair': pair, 'timestamp': ts, 'direction': direction,
                'rsi': rsi[i], 'score': score, 'quality': quality,
            }
            for label, n_candles in HORIZONS.items():
                j = i + n_candles
                if j < len(closes):
                    fwd = (closes[j] - closes[i]) / closes[i]
                    record[f'expected_dir_return_{label}'] = fwd if direction == 'hot' else -fwd
                else:
                    record[f'expected_dir_return_{label}'] = None

            records.append(record)

    events_df = pd.DataFrame(records)
    print(f"\nTotal events: {len(events_df)}", file=sys.stderr)

    report(events_df)


def permutation_p_value(scores, outcomes, n=N_PERMUTATIONS, seed=RANDOM_SEED):
    rng = random.Random(seed)
    score_ranks = pd.Series(scores).rank().values
    outcome_ranks = pd.Series(outcomes).rank().values
    real_corr = np.corrcoef(score_ranks, outcome_ranks)[0, 1]

    count = 0
    outcome_list = list(outcome_ranks)
    for _ in range(n):
        rng.shuffle(outcome_list)
        shuffled_corr = np.corrcoef(score_ranks, outcome_list)[0, 1]
        if abs(shuffled_corr) >= abs(real_corr):
            count += 1
    p_value = (count + 1) / (n + 1)
    return real_corr, p_value


def report(events_df):
    print("\n" + "=" * 70)
    print("SIGNAL ENHANCER VALIDATION REPORT")
    print("=" * 70)

    print(f"\nTotal events: {len(events_df)}")
    print(events_df['direction'].value_counts().to_string())
    print("\nQuality tier distribution:")
    print(events_df['quality'].value_counts().to_string())

    for label in HORIZONS:
        col = f'expected_dir_return_{label}'
        valid = events_df.dropna(subset=[col])
        print(f"\n--- Horizon {label} (n={len(valid)}) ---")
        for tier in ['A+', 'A', 'B', 'C']:
            tier_data = valid[valid['quality'] == tier][col]
            n = len(tier_data)
            if n < 10:
                print(f"  {tier}: n={n} -- INSUFFICIENT SAMPLE")
                continue
            mean = tier_data.mean()
            median = tier_data.median()
            win_rate = (tier_data > 0).mean()
            print(f"  {tier}: n={n:4d} | mean={mean:+.4%} | median={median:+.4%} | win_rate={win_rate:.1%}")

        if len(valid) >= 20:
            corr, p_value = permutation_p_value(valid['score'].values, valid[col].values)
            print(f"  Spearman-rank corr(score, {col}) = {corr:+.4f}, permutation p-value = {p_value:.4f}")
        else:
            print(f"  INSUFFICIENT SAMPLE for correlation test (n={len(valid)} < 20)")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
