"""EQL (minimos iguales) como filtro del spring. Criterio en spec.md (fijado antes)."""
import json, sys, zipfile
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
LOOKBACK, CONFIRM = 20, 3
TOLS = {'H1 tol 0.3%': 0.003, 'H2 tol 0.6%': 0.006}
rng = np.random.default_rng(9)
LO, HI = 100 * (0.05 / 2 / 2), 100 * (1 - 0.05 / 2 / 2)
cache = {}
def d4(pair):
    if pair not in cache:
        cache[pair] = pd.read_feather(f"{DATA}/{pair.replace('/USDT:USDT','')}_USDT_USDT-4h-futures.feather").set_index('date').sort_index()
    return cache[pair]

def touches(pair, open_date):
    """Toques del nivel (min de 20 velas) por velas del rango, para el spring confirmado justo antes de open_date."""
    df = d4(pair)
    conf = open_date - pd.Timedelta(hours=4)
    if conf not in df.index:
        return None
    j = df.index.get_loc(conf)
    lows, closes = df['low'].values, df['close'].values
    support = df['low'].rolling(LOOKBACK).min().shift(1).values
    out = None
    for i in range(j - CONFIRM, j):                       # misma semantica que la deteccion
        if i < LOOKBACK or np.isnan(support[i]) or not lows[i] < support[i]:
            continue
        first_ret = next((k for k in range(i + 1, min(i + 1 + CONFIRM, len(df))) if closes[k] > support[i]), None)
        if first_ret == j:
            lvl = support[i]
            window = lows[i - LOOKBACK:i]
            out = {name: int((window <= lvl * (1 + tol)).sum()) for name, tol in TOLS.items()}
    return out

rows = []
for period, zf in (('IS', sys.argv[1]), ('OOS', sys.argv[2])):
    z = zipfile.ZipFile(zf)
    name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    strat = next(iter(json.loads(z.read(name))['strategy'].values()))
    for t in strat['trades']:
        od = pd.Timestamp(t['open_date'])
        tc = touches(t['pair'], od)
        if tc:
            rows.append(dict(period=period, day=od.normalize(), ret=t['profit_ratio'] * 100, **{k: v for k, v in tc.items()}))
ev = pd.DataFrame(rows)
print('eventos con toques:', ev.groupby('period').size().to_dict())
for h in TOLS:
    print(f"toques medianos ({h}):", ev[h].median(), '| distribucion:', ev[h].clip(upper=5).value_counts().sort_index().to_dict())

def boot(d, m):
    days = d['day'].unique(); groups = {k: g for k, g in d.assign(_m=m).groupby('day')}
    res = []
    for _ in range(3000):
        s = pd.concat([groups[days[i]] for i in rng.integers(0, len(days), len(days))])
        a, b = s.loc[s._m, 'ret'], s.loc[~s._m, 'ret']
        if len(a) and len(b):
            res.append(a.mean() - b.mean())
    return np.percentile(res, [LO, HI])

print(f"\n{'hipotesis':14s} {'periodo':6s} {'n EQL':>6s} {'media':>7s} {'acierto':>7s} | {'n resto':>7s} {'media':>7s} {'acierto':>7s} | dif")
verdict = {}
for h in TOLS:
    difs = {}
    for period in ('IS', 'OOS', 'AMBOS'):
        d = (ev if period == 'AMBOS' else ev[ev.period == period]).reset_index(drop=True)
        m = d[h] >= 2
        a, b = d.loc[m, 'ret'], d.loc[~m, 'ret']
        difs[period] = a.mean() - b.mean()
        extra = ''
        if period == 'AMBOS':
            lo, hi = boot(d, m); difs['ci'] = lo
            extra = f" IC{100-2*LO:.1f}% por dia [{lo:+.2f}, {hi:+.2f}]"
        print(f"{h:14s} {period:6s} {len(a):6d} {a.mean():+7.2f} {(a>0).mean()*100:6.0f}% | {len(b):7d} {b.mean():+7.2f} {(b>0).mean()*100:6.0f}% | {difs[period]:+5.2f}{extra}")
    verdict[h] = difs['IS'] > 0 and difs['OOS'] > 0 and difs['ci'] > 0
print('\nVEREDICTO:', {k: ('APRUEBA' if v else 'NO aprueba') for k, v in verdict.items()})
