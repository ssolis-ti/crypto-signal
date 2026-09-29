"""Costo de entrar tarde a un spring (PC apagada): entrada k velas de 4h despues de la real, mismo plan
(mantener 72h desde LA ENTRADA, stop -10% sobre minimos de vela, 0.1% comision ida y vuelta)."""
import json, sys, zipfile
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
rng = np.random.default_rng(3)
DELAYS = [0, 1, 2, 3, 6]            # velas de 4h: 0h, 4h, 8h, 12h, 24h
cache = {}
def d4(pair):
    if pair not in cache:
        cache[pair] = pd.read_feather(f"{DATA}/{pair.replace('/USDT:USDT','')}_USDT_USDT-4h-futures.feather").set_index('date').sort_index()
    return cache[pair]

def ret(pair, t0, k):
    df = d4(pair)
    if t0 not in df.index:
        return None
    i = df.index.get_loc(t0) + k
    if i + 18 >= len(df):
        return None
    entry = df['open'].iloc[i]
    for j in range(i, i + 18):                       # 18 velas de 4h = 72h
        if df['low'].iloc[j] <= entry * 0.90:
            return (-10.0 - 0.1)
    return (df['close'].iloc[i + 17] / entry - 1) * 100 - 0.1

rows = []
for period, zf in (('IS', sys.argv[1]), ('OOS', sys.argv[2])):
    z = zipfile.ZipFile(zf)
    name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    strat = next(iter(json.loads(z.read(name))['strategy'].values()))
    for t in strat['trades']:
        od = pd.Timestamp(t['open_date'])
        r = {k: ret(t['pair'], od, k) for k in DELAYS}
        if all(v is not None for v in r.values()):
            rows.append(dict(period=period, day=od.normalize(), **{f'k{k}': v for k, v in r.items()}))
ev = pd.DataFrame(rows)
print('eventos:', ev.groupby('period').size().to_dict())
print(f"{'demora':>8s} | {'IS media':>9s} {'acierto':>7s} | {'OOS media':>9s} {'acierto':>7s} | costo vs entrar a tiempo (unido) IC95 por dia")
days = ev['day'].unique(); groups = {k: g for k, g in ev.groupby('day')}
for k in DELAYS:
    a, b = ev[ev.period == 'IS'], ev[ev.period == 'OOS']
    line = f"{k*4:6d}h | {a[f'k{k}'].mean():+9.2f} {(a[f'k{k}']>0).mean()*100:6.0f}% | {b[f'k{k}'].mean():+9.2f} {(b[f'k{k}']>0).mean()*100:6.0f}% |"
    if k:
        diffs = []
        for _ in range(2000):
            s = pd.concat([groups[days[i]] for i in rng.integers(0, len(days), len(days))])
            diffs.append((s[f'k{k}'] - s['k0']).mean())
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        line += f" {(ev[f'k{k}'] - ev['k0']).mean():+5.2f} pp [{lo:+.2f}, {hi:+.2f}]"
    print(line)
