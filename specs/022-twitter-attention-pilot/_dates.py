import pandas as pd
from datetime import datetime, timezone, timedelta
df = pd.read_csv('specs/022-twitter-attention-pilot/btc_events.csv')
for _, r in df.iterrows():
    ts = datetime.fromtimestamp(r['timestamp']/1000, tz=timezone.utc)
    sig_day = ts.date()
    base_day = (ts - timedelta(days=7)).date()
    print(f"{sig_day}|{sig_day + timedelta(days=1)}|{base_day}|{base_day + timedelta(days=1)}|{r['direction']}|{r['expected_dir_return']:+.4f}")
