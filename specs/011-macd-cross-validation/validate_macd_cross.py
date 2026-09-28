"""
Backtest de validacion historica para SignalEnhancer aplicado a macd_cross
(specs/011-macd-cross-validation/, continuacion de specs/007-signal-enhancer-validation/).

Misma metodologia que slice 007 (canasta, rango de fechas, reconstruccion de contexto,
scoring real via SignalEnhancer, horizontes de retorno, test de permutacion) -- ver
research.md. Unico cambio: el disparador de senal es el cruce MACD/signal real de
app/analyzers/indicators/macd_cross.py (deteccion via cambio de signo del histograma,
matematicamente identica: histograma = macd - signal, ver research.md).

Uso:
    PYTHONPATH=/work/app python specs/011-macd-cross-validation/validate_macd_cross.py
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
from analysis.market_context import AltStrengthData


REFERENCE_PAIR = 'BTC/USDT'
BASKET = [
    'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT',
    'BCH/USDT', 'ATOM/USDT', 'NEAR/USDT', 'MATIC/USDT',
]
TIMEFRAME = '4h'
RSI_PERIOD = 14
EMA_PERIOD = 99
HORIZONS = {'24h': 6, '72h': 18}
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
    if i < lookback:
        return None
    prev = closes[i - lookback]
    if prev == 0 or np.isnan(prev) or np.isnan(closes[i]):
        return None
    return (closes[i] - prev) / prev * 100.0


def build_breadth_table(all_data):
    frames = {}
    for pair, df in all_data.items():
        closes = df['close'].values.astype(float)
        changes = [pct_change_24h(closes, i) for i in range(len(closes))]
        s = pd.Series(changes, index=df['timestamp'].values, name=pair)
        frames[pair] = s
    return pd.DataFrame(frames)


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


def detect_macd_cross_events(macdhist):
    """
    Un evento por cruce, replicando MACDCross.analyze (ver research.md): histograma
    cambia de signo <=> MACD cruza su signal line. NaN < 0 / NaN > 0 son siempre False,
    asi que el warm-up de talib.MACD queda excluido sin necesidad de chequeo explicito.
    """
    events = []
    for i in range(1, len(macdhist)):
        prev, curr = macdhist[i - 1], macdhist[i]
        if np.isnan(prev) or np.isnan(curr):
            continue
        if prev < 0 and curr > 0:
            events.append((i, 'hot'))
        elif prev > 0 and curr < 0:
            events.append((i, 'cold'))
    return events


def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    all_data = fetch_all_pairs(exchange)

    btc_df = all_data[REFERENCE_PAIR]
    btc_closes = btc_df['close'].values.astype(float)
    btc_ts_to_idx = {ts: i for i, ts in enumerate(btc_df['timestamp'].values)}

    breadth = build_breadth_table(all_data)
    enhancer = SignalEnhancer(market_context=None, settings=None)

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
        events = detect_macd_cross_events(macdhist)

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

            sentiment = 'neutral'
            if ts in breadth.index:
                sentiment = sentiment_for_row(breadth.loc[ts], btc_change)

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
            rsi_value = rsi[i] if not np.isnan(rsi[i]) else None

            quality, confidence, note, score = enhancer._calculate_quality(
                signal_type=direction,
                btc_trend=btc_trend,
                alt_strength=alt,
                sentiment=sentiment,
                rsi_value=rsi_value,
                context_data=context_data,
            )

            record = {
                'pair': pair, 'timestamp': ts, 'direction': direction,
                'score': score, 'quality': quality,
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
    outcome_ranks = list(pd.Series(outcomes).rank().values)
    real_corr = np.corrcoef(score_ranks, outcome_ranks)[0, 1]

    count = 0
    for _ in range(n):
        rng.shuffle(outcome_ranks)
        shuffled_corr = np.corrcoef(score_ranks, outcome_ranks)[0, 1]
        if abs(shuffled_corr) >= abs(real_corr):
            count += 1
    return real_corr, (count + 1) / (n + 1)


def report(events_df):
    print("\n" + "=" * 70)
    print("MACD_CROSS SIGNAL ENHANCER VALIDATION REPORT")
    print("=" * 70)

    print(f"\nTotal events: {len(events_df)}")
    if len(events_df) == 0:
        print("No events detected -- nothing to report.")
        return
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
