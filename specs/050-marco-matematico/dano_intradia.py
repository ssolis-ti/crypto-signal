"""Elasticidad de dano intra-dia (criterio en spec.md, fijado antes)."""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
rng = np.random.default_rng(53)
SPLIT = pd.Timestamp('2025-01-01', tz='UTC')
ev = pd.read_csv('/exp044/events_universo.csv', parse_dates=['conf', 't'])
ev['conf'] = pd.to_datetime(ev.conf, utc=True)
ev['t'] = pd.to_datetime(ev.t, utc=True)
series = {}
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    series[os.path.basename(p).split('_USDT_USDT')[0]] = pd.read_feather(p).set_index('date').sort_index()
for p in glob.glob(f'{DELISTED}/*.pkl'):
    series['D_' + os.path.basename(p)[:-8]] = pd.read_pickle(p)
btc = series['BTC']['close']
rows = []
for r in ev.itertuples():
    df = series.get(r.sym)
    if df is None or r.conf not in df.index or r.conf not in btc.index:
        continue
    j = df.index.get_loc(r.conf)
    jb = btc.index.get_loc(r.conf)
    if j < 12 or jb < 12:
        continue
    d_alt = df['close'].iloc[j] / df['close'].iloc[j - 12] - 1
    d_btc = btc.iloc[jb] / btc.iloc[jb - 12] - 1
    rows.append(dict(sym=r.sym, conf=r.conf, t=r.t, ret=r.ret, D=-(d_alt - d_btc) * 100, frac=r.frac, k=r.k))
d = pd.DataFrame(rows)
d['day'] = d.t.dt.normalize()
d['period'] = np.where(d.t < SPLIT, 'IS', 'OOS')
print(f'springs con D: {len(d)}')


def within(x):
    x = x.copy()
    g = x.groupby('conf')
    x['ret_dm'] = x.ret - g.ret.transform('mean')
    sd = g.D.transform('std')
    x['z'] = (x.D - g.D.transform('mean')) / sd.replace(0, np.nan)
    return x.dropna(subset=['z'])


def beta(x):
    return float((x.z * x.ret_dm).sum() / (x.z ** 2).sum())


def boot_beta(x, n_=3000):
    days = x.day.unique(); g = {k: v for k, v in x.groupby('day')}
    res = [beta(pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])) for _ in range(n_)]
    return np.percentile(res, [2.5, 97.5])


def analyse(x, label):
    x = within(x[x.groupby('conf').conf.transform('count') >= 2])
    print(f'\n{label}: {len(x)} springs, {x.conf.nunique()} velas, {x.day.nunique()} dias')
    out = {}
    for per in ('IS', 'OOS', 'AMBOS'):
        y = x if per == 'AMBOS' else x[x.period == per]
        b = beta(y)
        lo, hi = boot_beta(y)
        out[per] = (b, lo, hi)
        print(f'  {per:5s} beta = {b:+.2f} pp por desvio estandar de dano | IC95 por dia [{lo:+.2f}, {hi:+.2f}] | dias {y.day.nunique()}')
    ok = out['IS'][0] >= 0.5 and out['OOS'][0] >= 0.5 and out['AMBOS'][1] > 0
    # placebo: permutar D dentro de cada vela
    perm = []
    for _ in range(500):
        y = x.copy()
        y['z'] = y.groupby('conf').z.transform(lambda s: rng.permutation(s.values))
        perm.append(beta(y))
    print(f'  placebo (D permutado dentro de la vela): beta medio {np.mean(perm):+.3f}, p95 {np.percentile(perm, 95):+.2f}, p(beta_perm >= observado) = {np.mean(np.array(perm) >= out["AMBOS"][0]):.3f}')
    return ok


ok_wide = analyse(d[d.frac >= 0.20], 'DIAS DE CAPITULACION AMPLIA (>= 20% de los pares)')
ok_5 = analyse(d[d.k >= 5], 'TODAS LAS VELAS CON >= 5 SPRINGS')
print('\nVEREDICTO (criterio pre-registrado, beta >= +0.5 pp/sd en IS y OOS con IC95 > 0):', {'amplia': 'APRUEBA' if ok_wide else 'NO aprueba', '>=5 springs': 'APRUEBA' if ok_5 else 'NO aprueba'})
