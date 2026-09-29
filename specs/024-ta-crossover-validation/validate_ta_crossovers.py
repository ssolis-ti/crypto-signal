"""
Validacion de cruces TA no probados (specs/024-ta-crossover-validation/),
continuacion del arco de investigacion Wyckoff (specs/007-023).

Prueba 2 indicadores ya presentes en el codigo pero nunca conectados a alertas
en produccion -- ma_crossover.py (golden/death cross EMA) y sqzmom.py (Squeeze
Momentum) -- como candidatos para complementar la baja frecuencia de alertas
Wyckoff. Mismo estandar de rigor que specs/017: split cronologico 70/30
in-sample/out-of-sample, win_rate>=60%, p<0.05, n>=30 para "confirmed".

No conecta nada a codigo de produccion (FR-006).

Uso:
    PYTHONPATH=/work/app python specs/024-ta-crossover-validation/validate_ta_crossovers.py
"""
import sys
import time
import math
from datetime import datetime, timezone, timedelta

import ccxt
import numpy as np
import pandas as pd
import talib


BASKET = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT',
    'BCH/USDT', 'ATOM/USDT', 'NEAR/USDT', 'MATIC/USDT',
]
TIMEFRAME = '4h'
MONTHS_BACK = 10
HORIZONS = {'24h': 6, '72h': 18, '7d': 42, '14d': 84}
EXTREME_VOLUME_THRESHOLD = 2.5
VOLUME_PERIOD = 20
IN_SAMPLE_FRACTION = 0.7
MIN_SAMPLE = 30
ACTIONABLE_WIN_RATE = 0.60

# ma_crossover params (matches app/analyzers/indicators/ma_crossover.py defaults)
MA_FAST, MA_SLOW = 10, 50

# sqzmom params (matches app/analyzers/indicators/sqzmom.py defaults)
SQZ_LENGTH, SQZ_MULT, SQZ_LENGTH_KC, SQZ_MULT_KC = 20, 2, 20, 1.5


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


def relative_volume(df, period=VOLUME_PERIOD):
    avg_vol = talib.SMA(df['volume'].values.astype(float), timeperiod=period)
    with np.errstate(divide='ignore', invalid='ignore'):
        rv = df['volume'].values.astype(float) / avg_vol
    return rv


def detect_ma_crossover_events(df, fast=MA_FAST, slow=MA_SLOW):
    """Vectorized golden/death cross over the WHOLE series (not just last candle)."""
    closes = df['close'].values.astype(float)
    ema_fast = talib.EMA(closes, timeperiod=fast)
    ema_slow = talib.EMA(closes, timeperiod=slow)

    is_hot = np.zeros(len(df), dtype=bool)
    is_cold = np.zeros(len(df), dtype=bool)
    for i in range(1, len(df)):
        if np.isnan(ema_fast[i - 1]) or np.isnan(ema_slow[i - 1]):
            continue
        prev_fast, prev_slow = ema_fast[i - 1], ema_slow[i - 1]
        cur_fast, cur_slow = ema_fast[i], ema_slow[i]
        is_hot[i] = prev_fast < prev_slow and cur_fast > cur_slow
        is_cold[i] = prev_fast > prev_slow and cur_fast < cur_slow
    return is_hot, is_cold


def detect_sqzmom_events(df, length=SQZ_LENGTH, mult=SQZ_MULT,
                          length_kc=SQZ_LENGTH_KC, mult_kc=SQZ_MULT_KC):
    """Vectorized squeeze-release-with-momentum over the WHOLE series."""
    close, high, low = df['close'], df['high'], df['low']

    m_avg = close.rolling(window=length).mean()
    m_std = close.rolling(window=length).std(ddof=0)
    upper_bb = m_avg + mult * m_std
    lower_bb = m_avg - mult * m_std

    tr0 = (high - low).abs()
    tr1 = (high - close.shift()).abs()
    tr2 = (low - close.shift()).abs()
    tr = pd.concat([tr0, tr1, tr2], axis=1).max(axis=1)
    range_ma = tr.rolling(window=length_kc).mean()
    upper_kc = m_avg + range_ma * mult_kc
    lower_kc = m_avg - range_ma * mult_kc

    squeeze_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)

    highest = high.rolling(window=length_kc).max()
    lowest = low.rolling(window=length_kc).min()
    m1 = (highest + lowest) / 2
    raw_value = close - (m1 + m_avg) / 2
    fit_y = np.arange(length_kc)

    def _linreg_endpoint(x):
        coeffs = np.polyfit(fit_y, x, 1)
        return coeffs[0] * (length_kc - 1) + coeffs[1]

    value = raw_value.rolling(window=length_kc).apply(_linreg_endpoint, raw=True)

    squeeze_off_prev = squeeze_off.shift(1)
    released = (squeeze_off_prev == False) & (squeeze_off == True)  # noqa: E712

    is_hot = (released & (value > 0)).fillna(False).values
    is_cold = (released & (value < 0)).fillna(False).values
    return is_hot, is_cold


def collect_events(basket_4h, detector_fn, label):
    records = []
    max_horizon = max(HORIZONS.values())
    min_history = max(SQZ_LENGTH, SQZ_LENGTH_KC, MA_SLOW) + max_horizon + 5

    for pair, df in basket_4h.items():
        if len(df) < min_history:
            print(f"Skipping {pair} ({label}): insufficient history ({len(df)} candles)", file=sys.stderr)
            continue

        closes = df['close'].values.astype(float)
        timestamps = df['timestamp'].values
        rel_vol = relative_volume(df)

        is_hot, is_cold = detector_fn(df)

        for i in range(len(df)):
            direction = None
            if is_hot[i]:
                direction = 'hot'
            elif is_cold[i]:
                direction = 'cold'
            else:
                continue

            rv = rel_vol[i]
            row = {
                'pair': pair, 'timestamp': timestamps[i], 'direction': direction,
                'extreme_volume': bool(rv >= EXTREME_VOLUME_THRESHOLD) if not np.isnan(rv) else False,
            }
            valid = True
            for h_label, h_candles in HORIZONS.items():
                j = i + h_candles
                if j >= len(closes):
                    valid = False
                    break
                fwd = (closes[j] - closes[i]) / closes[i]
                row[f'ret_{h_label}'] = fwd if direction == 'hot' else -fwd
            if not valid:
                continue
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


def evaluate_candidate(name, events, filter_fn):
    events = events.sort_values('timestamp').reset_index(drop=True)
    split_idx = int(len(events) * IN_SAMPLE_FRACTION)
    in_sample, out_sample = events.iloc[:split_idx], events.iloc[split_idx:]

    print(f"\n--- Candidate: {name} ---")
    print(f"    total events: {len(events)} | in-sample: {len(in_sample)} | "
          f"out-of-sample: {len(out_sample)}")

    in_mask = filter_fn(in_sample)
    out_mask = filter_fn(out_sample)

    per_horizon = {}
    any_confirmed = False
    for h_label in HORIZONS:
        ret_col = f'ret_{h_label}'
        in_b = evaluate_bucket(in_sample, in_mask, ret_col, f'in-sample  {h_label}')
        out_b = evaluate_bucket(out_sample, out_mask, ret_col, f'out-sample {h_label}')
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
    return {'name': name, 'per_horizon': per_horizon, 'overall': overall}


def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    basket_4h = fetch_all(exchange, TIMEFRAME, MONTHS_BACK)

    print("\n" + "=" * 78)
    print("TA CROSSOVER VALIDATION -- IN-SAMPLE / OUT-OF-SAMPLE (70/30 chronological)")
    print("=" * 78)

    ma_events = collect_events(basket_4h, detect_ma_crossover_events, 'ma_crossover')
    sqz_events = collect_events(basket_4h, detect_sqzmom_events, 'sqzmom')

    print(f"\nma_crossover total events: {len(ma_events)}", file=sys.stderr)
    print(f"sqzmom total events: {len(sqz_events)}", file=sys.stderr)

    results = []
    results.append(evaluate_candidate(
        "1. ma_crossover (EMA10/EMA50) alone",
        ma_events, lambda d: pd.Series(True, index=d.index)
    ))
    results.append(evaluate_candidate(
        f"2. ma_crossover + extreme volume (>={EXTREME_VOLUME_THRESHOLD}x)",
        ma_events, lambda d: d['extreme_volume'] == True  # noqa: E712
    ))
    results.append(evaluate_candidate(
        "3. sqzmom (squeeze release + momentum) alone",
        sqz_events, lambda d: pd.Series(True, index=d.index)
    ))
    results.append(evaluate_candidate(
        f"4. sqzmom + extreme volume (>={EXTREME_VOLUME_THRESHOLD}x)",
        sqz_events, lambda d: d['extreme_volume'] == True  # noqa: E712
    ))

    print("\n" + "=" * 78)
    print("SUMMARY")
    confirmed = [r for r in results if r['overall'] == 'confirmed']
    if confirmed:
        for r in confirmed:
            print(f"  CONFIRMED (at least one horizon): {r['name']}")
            for h_label, v in r['per_horizon'].items():
                if v['verdict'] == 'confirmed':
                    ob = v['out_of_sample']
                    print(f"      -> {h_label}: win_rate={ob['win_rate']:.1%}, n={ob['n']}, p={ob['p']:.4f}")
    else:
        print("  No candidate confirmed at any horizon "
              f"(bar: win_rate >= {ACTIONABLE_WIN_RATE:.0%}, p<0.05, n>={MIN_SAMPLE}).")
    print("=" * 78)


if __name__ == '__main__':
    main()
