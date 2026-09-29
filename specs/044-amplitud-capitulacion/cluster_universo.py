"""
Seguimiento de spec 044 (exploratorio, definido despues de ver que la amplitud de minimos NO funciona):
¿el efecto "5+ springs confirmados en la misma vela rinden mas" sobrevive con el universo completo (49 pares del
laboratorio + deslistados, solo pares con >= 20M USD/24h)? Mismo simulador que la spec 043.
"""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
LOOKBACK, CONFIRM, VOL_N, THRESH, HOLD, STOP, FEE = 20, 3, 20, 2.5, 18, -10.0, 0.1
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
rng = np.random.default_rng(45)


def events(df, name, group):
    v = df['volume'].astype(float).values
    sma = pd.Series(v).rolling(VOL_N).mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        rv = np.where(sma > 0, v / sma, np.nan)
    o, l, c = df['open'].values, df['low'].values, df['close'].values
    dv24 = (df['volume'] * df['close']).rolling(6).sum().values
    support = df['low'].rolling(LOOKBACK).min().shift(1).values
    idx, n, out, seen = df.index, len(df), [], set()
    for i in range(n):
        lvl = support[i]
        if np.isnan(lvl) or not l[i] < lvl:
            continue
        for j in range(i + 1, min(i + 1 + CONFIRM, n)):
            if c[j] > lvl:
                if j not in seen and not np.isnan(rv[i]) and rv[i] >= THRESH and j + 1 < n and T0 <= idx[j + 1] <= T1:
                    seen.add(j)
                    e = j + 1
                    end = min(e + HOLD, n)
                    if (e + HOLD) > n and group == 'lab':
                        break
                    entry = o[e]
                    ret = STOP if (l[e:end] <= entry * (1 + STOP / 100)).any() else (c[end - 1] / entry - 1) * 100
                    out.append(dict(group=group, sym=name, t=idx[e], dvol=dv24[j], ret=ret - FEE))
                break
    return out


rows = []
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    d = pd.read_feather(p).set_index('date').sort_index()
    rows += events(d, os.path.basename(p).split('_USDT_USDT')[0], 'lab')
for p in glob.glob(f'{DELISTED}/*.pkl'):
    d = pd.read_pickle(p)
    if len(d) > LOOKBACK + HOLD + 10:
        rows += events(d, os.path.basename(p)[:-8], 'deslistado')
ev = pd.DataFrame(rows)
ev = ev[ev.dvol >= 20e6].copy()
ev['day'] = ev.t.dt.normalize()
ev['period'] = np.where(ev.t < SPLIT, 'IS', 'OOS')
print('senales con >= 20M USD/24h:', len(ev), '| lab:', int((ev.group == 'lab').sum()), '| deslistados:', int((ev.group == 'deslistado').sum()))


def buckets(d, label):
    d = d.copy()
    d['k'] = d.groupby('t').t.transform('count')
    d['bucket'] = pd.cut(d.k, [0, 1, 4, 9, 1000], labels=['1 (aislado)', '2-4', '5-9', '10+'])
    print(f'\n{label}')
    print(f"  {'pares simultaneos':18s} | {'n':>5s} {'media':>7s} {'acierto':>7s} {'dias':>4s} | {'IS n':>5s} {'media':>7s} | {'OOS n':>5s} {'media':>7s}")
    for b in ['1 (aislado)', '2-4', '5-9', '10+']:
        x = d[d.bucket == b]
        if not len(x):
            continue
        a, o = x[x.period == 'IS'], x[x.period == 'OOS']
        print(f"  {b:18s} | {len(x):5d} {x.ret.mean():+7.2f} {(x.ret > 0).mean()*100:6.0f}% {x.day.nunique():4d} | {len(a):5d} {a.ret.mean():+7.2f} | {len(o):5d} {o.ret.mean():+7.2f}")
    big = d[d.k >= 5]
    small = d[d.k < 5]
    days = d.day.unique(); g = {k: v for k, v in d.groupby('day')}
    res = []
    for _ in range(3000):
        s = pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])
        a, b = s[s.k >= 5].ret, s[s.k < 5].ret
        if len(a) and len(b):
            res.append(a.mean() - b.mean())
    lo, hi = np.percentile(res, [2.5, 97.5])
    print(f'  5+ vs <5: {big.ret.mean() - small.ret.mean():+.2f} pp  IC95 por dia [{lo:+.2f}, {hi:+.2f}]  (5+: n={len(big)}, media {big.ret.mean():+.2f}%, acierto {(big.ret>0).mean()*100:.0f}%)')


buckets(ev[ev.group == 'lab'], 'SOLO LOS 49 PARES DEL LABORATORIO (sobrevivientes), >= 20M USD/24h')
buckets(ev, 'UNIVERSO COMPLETO (laboratorio + deslistados), >= 20M USD/24h')
