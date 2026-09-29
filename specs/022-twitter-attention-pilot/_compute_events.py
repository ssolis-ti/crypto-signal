import sys, time
from datetime import datetime, timezone, timedelta
import ccxt, pandas as pd, numpy as np
sys.path.insert(0, '/work/app')
from analyzers.indicators.wyckoff import WyckoffPrimitives

exchange = ccxt.binance({'enableRateLimit': True})
now = datetime.now(timezone.utc)
since_ms = int((now - timedelta(days=300)).timestamp()*1000)
now_ms = int(now.timestamp()*1000)

all_rows = []
since = since_ms
while True:
    batch = exchange.fetch_ohlcv('BTC/USDT', timeframe='4h', since=since, limit=1000)
    if not batch: break
    all_rows.extend(batch)
    last_ts = batch[-1][0]
    time.sleep(exchange.rateLimit/1000)
    if last_ts >= now_ms or len(batch) < 1000: break
    since = last_ts + 1

df = pd.DataFrame(all_rows, columns=['timestamp','open','high','low','close','volume'])
df = df.drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)
df = df[df['timestamp'] <= now_ms].reset_index(drop=True)
print(f"candles: {len(df)}", file=sys.stderr)

LOOKBACK=20; CONFIRM_WINDOW=3; EXTREME=2.5; HORIZON=84
springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)
upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)
closes = df['close'].values.astype(float)
timestamps = df['timestamp'].values

events = []
for i in range(len(df)):
    direction, flags = None, None
    if bool(springs['is_spring'].iloc[i]):
        direction, flags = 'hot', springs
    elif bool(upthrusts['is_upthrust'].iloc[i]):
        direction, flags = 'cold', upthrusts
    else:
        continue
    brv = flags['break_relative_volume'].iloc[i]
    if pd.isna(brv) or brv < EXTREME:
        continue
    j = i + HORIZON
    if j >= len(closes):
        continue
    fwd = (closes[j]-closes[i])/closes[i]
    edr = fwd if direction=='hot' else -fwd
    events.append({'timestamp': int(timestamps[i]), 'direction': direction, 'expected_dir_return': edr})

out = pd.DataFrame(events)
out.to_csv('/work/specs/022-twitter-attention-pilot/btc_events.csv', index=False)
print(out.to_string())
print(f"\ntotal: {len(out)}")
