"""
Timing y riesgo de drawdown de la señal Wyckoff de volumen extremo
(specs/018-wyckoff-timing-and-drawdown/), continuacion de specs/017-wyckoff-edge-refinement/.

Slice 017 valido que existe un edge real (~60% win-rate a 14 dias) pero solo midio el
retorno en UN punto (14d despues). Este script responde la pregunta real del operador:
¿en que momento, desde que llega la alerta, se materializa el movimiento, y cuanto
drawdown adverso hay que aguantar antes? Usa OHLCV real de 1h (4x mas fino que la
deteccion en 4h) sobre los mismos eventos "confirmados" de slice 017.

Limite de resolucion (ver spec.md FR-005): 1h es el grano mas fino que este script
pide -- NO responde timing de segundos/minutos, que requeriria datos de order book/tick
y trading en papel en vivo, no un backtest de velas historicas.

Uso:
    PYTHONPATH=/work/app python specs/018-wyckoff-timing-and-drawdown/analyze_wyckoff_timing.py
"""
import sys
import time
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
LOOKBACK = 20
CONFIRM_WINDOW = 3
EXTREME_VOLUME_THRESHOLD = 2.5
MONTHS_BACK_4H = 10       # para detectar eventos, igual que slices 015/017
FORWARD_HOURS = 336       # 14 dias en horas, ventana de seguimiento en 1h
CHECKPOINTS_H = [1, 2, 4, 8, 12, 24, 48, 72, 168, 336]  # 1h .. 14d
MAE_THRESHOLDS = [-0.02, -0.05, -0.10]


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


def find_confirmed_extreme_volume_events(basket_4h):
    """Regenera el set de eventos 'confirmed' de slice 017 (volumen extremo en la ruptura)."""
    events = []
    min_history = LOOKBACK + CONFIRM_WINDOW + 5

    for pair, df in basket_4h.items():
        if len(df) < min_history:
            continue
        timestamps = df['timestamp'].values

        springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)

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
                continue

            events.append({'pair': pair, 'timestamp': timestamps[i], 'direction': direction})

    return pd.DataFrame(events)


def analyze_paths(events, basket_1h):
    rows = []
    for _, ev in events.iterrows():
        pair, ts, direction = ev['pair'], ev['timestamp'], ev['direction']
        hourly = basket_1h.get(pair)
        if hourly is None or len(hourly) == 0:
            continue

        hourly_ts = hourly['timestamp'].values
        idx_arr = np.searchsorted(hourly_ts, ts)
        if idx_arr >= len(hourly_ts) or hourly_ts[idx_arr] != ts:
            continue  # la vela 4h de confirmacion no tiene equivalente exacto en la serie 1h
        entry_idx = idx_arr

        closes = hourly['close'].values.astype(float)
        if entry_idx + FORWARD_HOURS >= len(closes):
            continue  # no hay suficiente futuro para la ventana completa de 14d

        entry_close = closes[entry_idx]
        path = (closes[entry_idx + 1: entry_idx + 1 + FORWARD_HOURS] - entry_close) / entry_close
        if direction == 'cold':
            path = -path

        row = {'pair': pair, 'timestamp': ts, 'direction': direction}
        for h in CHECKPOINTS_H:
            row[f'ret_{h}h'] = path[h - 1]
            sub_path = path[:h]
            row[f'mae_{h}h'] = min(0.0, sub_path.min())
            row[f'mfe_{h}h'] = max(0.0, sub_path.max())
        row['peak_hour'] = int(np.argmax(path)) + 1
        rows.append(row)

    return pd.DataFrame(rows)


def report(paths_df):
    print("\n" + "=" * 70)
    print("WYCKOFF EXTREME-VOLUME SIGNAL -- TIMING & DRAWDOWN REPORT")
    print("=" * 70)
    print(f"\nEvents with full 1h path available: {len(paths_df)}")
    if len(paths_df) == 0:
        print("No events with complete data -- nothing to report.")
        return

    print("\n--- Checkpoint curve (cumulative expected-direction return) ---")
    print(f"{'checkpoint':>10} | {'mean':>8} | {'median':>8} | {'win_rate':>8} | "
          f"{'median MAE':>11} | {'median MFE':>11}")
    for h in CHECKPOINTS_H:
        ret = paths_df[f'ret_{h}h']
        mae = paths_df[f'mae_{h}h']
        mfe = paths_df[f'mfe_{h}h']
        label = f"{h}h" if h < 24 else f"{h // 24}d"
        print(f"{label:>10} | {ret.mean():+7.3%} | {ret.median():+7.3%} | "
              f"{(ret > 0).mean():7.1%} | {mae.median():+10.3%} | {mfe.median():+10.3%}")

    print("\n--- Riesgo de drawdown (MAE) a 14 dias -- relevante para apalancamiento ---")
    mae_14d = paths_df['mae_336h']
    for threshold in MAE_THRESHOLDS:
        pct_breached = (mae_14d <= threshold).mean() * 100
        print(f"  % de eventos donde el drawdown adverso alcanzo o supero {threshold:+.0%}: "
              f"{pct_breached:.1f}%")

    print("\n--- ¿Cuándo ocurre el pico favorable? ---")
    print(f"  Hora del pico (MFE), mediana: {paths_df['peak_hour'].median():.0f}h "
          f"({paths_df['peak_hour'].median() / 24:.1f} dias)")
    print(f"  % de eventos cuyo pico ocurrio dentro de las primeras 24h: "
          f"{(paths_df['peak_hour'] <= 24).mean():.1%}")
    print(f"  % de eventos cuyo pico ocurrio dentro de los primeros 3 dias (72h): "
          f"{(paths_df['peak_hour'] <= 72).mean():.1%}")

    print("\n" + "-" * 70)
    print("LIMITE DE RESOLUCION: este analisis usa velas de 1 HORA. No responde timing de")
    print("segundos/minutos -- eso requiere datos de order book/tick y trading en papel en")
    print("vivo, no un backtest de velas historicas.")
    print("=" * 70)


def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    basket_4h = fetch_all(exchange, '4h', MONTHS_BACK_4H)
    events = find_confirmed_extreme_volume_events(basket_4h)
    print(f"\nConfirmed extreme-volume events (from 4h detection): {len(events)}", file=sys.stderr)

    # Solo se necesita 1h para los pares que realmente tuvieron eventos calificados.
    pairs_with_events = events['pair'].unique().tolist()
    basket_1h = {}
    now = datetime.now(timezone.utc)
    since_ms = int((now - timedelta(days=30 * MONTHS_BACK_4H)).timestamp() * 1000)
    now_ms = int(now.timestamp() * 1000)
    for pair in pairs_with_events:
        print(f"Fetching {pair} (1h)...", file=sys.stderr)
        try:
            df = fetch_ohlcv_paginated(exchange, pair, '1h', since_ms, now_ms)
        except Exception as e:
            print(f"  FAILED ({type(e).__name__}: {e}) -- skipping", file=sys.stderr)
            continue
        basket_1h[pair] = df
        print(f"  {len(df)} candles", file=sys.stderr)

    paths_df = analyze_paths(events, basket_1h)
    report(paths_df)


if __name__ == '__main__':
    main()
