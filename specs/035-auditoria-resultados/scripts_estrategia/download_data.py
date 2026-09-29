"""
audit/download_data.py
Descarga y almacena en cache local (pickle) las velas necesarias de Binance Futures via ccxt:
1. BTC/USDT:USDT 1d (para EMA200 diaria)
2. 4h OHLCV para los 28 pares de Wyckoff + BTC desde 2021-11-01 hasta 2026-09-25
3. Historial de funding rate para BTC y pares de muestra
"""

import os
import time
import ccxt
import pandas as pd

PAIRS = [
    'BTC/USDT:USDT',
    'AAVE/USDT:USDT', 'ADA/USDT:USDT', 'ALGO/USDT:USDT', 'APE/USDT:USDT', 'ATOM/USDT:USDT',
    'AVAX/USDT:USDT', 'AXS/USDT:USDT', 'BCH/USDT:USDT', 'CHZ/USDT:USDT', 'CRV/USDT:USDT',
    'DOGE/USDT:USDT', 'DOT/USDT:USDT', 'DYDX/USDT:USDT', 'ETC/USDT:USDT', 'ETH/USDT:USDT',
    'FIL/USDT:USDT', 'GALA/USDT:USDT', 'ICP/USDT:USDT', 'LINK/USDT:USDT', 'LTC/USDT:USDT',
    'MANA/USDT:USDT', 'NEAR/USDT:USDT', 'SAND/USDT:USDT', 'SOL/USDT:USDT', 'TRX/USDT:USDT',
    'UNI/USDT:USDT', 'XLM/USDT:USDT', 'XRP/USDT:USDT'
]

CACHE_DIR = 'audit/data_cache'

def get_exchange():
    return ccxt.binance({
        'options': {'defaultType': 'future'},
        'enableRateLimit': True
    })

def download_ohlcv_series(exchange, symbol, timeframe, start_ts, end_ts=None):
    all_candles = []
    current_ts = start_ts
    while True:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            last_ts = candles[-1][0]
            if len(candles) < 1000 or (end_ts and last_ts >= end_ts):
                break
            current_ts = last_ts + (candles[1][0] - candles[0][0])
            time.sleep(0.05)
        except Exception as e:
            print(f"Error fetching {symbol} {timeframe} at {current_ts}: {e}")
            time.sleep(1)
            # reintentar
            continue
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    return df

def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    exchange = get_exchange()

    # 1. BTC 1d para EMA200
    btc_1d_path = os.path.join(CACHE_DIR, 'BTC_1d.pkl')
    if not os.path.exists(btc_1d_path):
        print("Descargando BTC 1d...")
        # 2021-01-01 = 1609459200000
        df_btc_1d = download_ohlcv_series(exchange, 'BTC/USDT:USDT', '1d', 1609459200000)
        df_btc_1d.to_pickle(btc_1d_path)
        print(f"BTC 1d guardado: {len(df_btc_1d)} velas.")
    else:
        print("BTC 1d ya en cache.")

    # 2. 4h para todos los pares
    # 2021-11-01 = 1635724800000
    start_4h = 1635724800000
    for p in PAIRS:
        safe_name = p.replace('/', '_').replace(':', '_')
        path = os.path.join(CACHE_DIR, f"{safe_name}_4h.pkl")
        if os.path.exists(path):
            print(f"{p} 4h ya en cache.")
            continue
        print(f"Descargando {p} 4h...")
        df = download_ohlcv_series(exchange, p, '4h', start_4h)
        df.to_pickle(path)
        print(f"  Guardado {p}: {len(df)} velas.")
        time.sleep(0.05)

    print("\nDescarga de OHLCV completada exitosamente.")

if __name__ == '__main__':
    main()
