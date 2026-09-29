"""
Amplitud de SPRINGS CONFIRMADOS (seguimiento de spec 044). Variable definida a priori: fraccion = springs confirmados en la
vela t / pares elegibles en t (>= 20M USD/24h). Protocolo: el umbral se ELIGE con 2022-24 (el menor de la grilla con media
>= +2% y >= 15 dias) y se PRUEBA en 2025-26. Se muestra toda la grilla para ver si hay meseta y no un pico.
"""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
LOOKBACK, CONFIRM, VOL_N, THRESH, HOLD, STOP, FEE = 20, 3, 20, 2.5, 18, -10.0, 0.1
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
rng = np.random.default_rng(46)
idx = pd.date_range('2021-12-01', '2026-09-22', freq='4h', tz='UTC')

series = {}
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    series[os.path.basename(p).split('_USDT_USDT')[0]] = pd.read_feather(p).set_index('date').sort_index()
n_lab = len(series)
for p in glob.glob(f'{DELISTED}/*.pkl'):
    d = pd.read_pickle(p)
    if len(d) > LOOKBACK + HOLD + 10:
        series['D_' + os.path.basename(p)[:-8]] = d


def universe_eligible(keys):
    dv = pd.DataFrame({k: (series[k]['volume'] * series[k]['close']).rolling(6).sum().reindex(idx) for k in keys})
    return (dv >= 20e6)


def spring_events(df, name):
    v = df['volume'].astype(float).values
    sma = pd.Series(v).rolling(VOL_N).mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        rv = np.where(sma > 0, v / sma, np.nan)
    o, l, c = df['open'].values, df['low'].values, df['close'].values
    support = df['low'].rolling(LOOKBACK).min().shift(1).values
    ix, n, out, seen = df.index, len(df), [], set()
    for i in range(n):
        lvl = support[i]
        if np.isnan(lvl) or not l[i] < lvl:
            continue
        for j in range(i + 1, min(i + 1 + CONFIRM, n)):
            if c[j] > lvl:
                if j not in seen and not np.isnan(rv[i]) and rv[i] >= THRESH and j + 1 < n:
                    seen.add(j)
                    e = j + 1
                    end = min(e + HOLD, n)
                    if T0 <= ix[e] <= T1 and (e + HOLD) <= n or (T0 <= ix[e] <= T1 and not name.startswith('D_')):
                        if (e + HOLD) > n and not name.startswith('D_'):
                            break
                        entry = o[e]
                        ret = STOP if (l[e:end] <= entry * (1 + STOP / 100)).any() else (c[end - 1] / entry - 1) * 100
                        out.append(dict(sym=name, conf=ix[j], t=ix[e], ret=ret - FEE))
                break
    return out


rows = []
for k, d in series.items():
    rows += spring_events(d, k)
ev = pd.DataFrame(rows)
elig = universe_eligible(list(series.keys()))
n_el = elig.sum(axis=1)
ev['elig_at'] = ev.conf.map(n_el)
d24 = pd.DataFrame({k: (series[k]['volume'] * series[k]['close']).rolling(6).sum().reindex(idx) for k in series.keys()})
ev['ok'] = [bool(d24.at[r.conf, r.sym] >= 20e6) if r.conf in d24.index else False for r in ev.itertuples()]
ev = ev[ev.ok].copy()
ev['k'] = ev.groupby('conf').conf.transform('count')
ev['frac'] = ev.k / ev.elig_at
ev['day'] = ev.t.dt.normalize()
ev[['sym', 'conf', 't', 'ret', 'k', 'frac', 'elig_at']].to_csv('/exp/events_universo.csv', index=False)
ev['period'] = np.where(ev.t < SPLIT, 'IS', 'OOS')
print(f'pares del laboratorio: {n_lab}, deslistados: {len(series) - n_lab}; springs con >= 20M USD/24h: {len(ev)}; pares elegibles por vela: mediana {n_el[n_el > 0].median():.0f}')
print('fraccion de pares con spring: percentiles', ev.frac.quantile([.5, .75, .9, .95]).round(3).to_dict())


def stats(x):
    return f"n={len(x):4d} media={x.ret.mean():+6.2f}% acierto={(x.ret > 0).mean()*100:3.0f}% dias={x.day.nunique():3d}"


print('\nGRILLA (eventos = springs individuales en velas con fraccion >= umbral)')
print(f"{'umbral':>7s} | {'2022-24':45s} | {'2025-26':45s}")
grid = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40)
for thr in grid:
    x = ev[ev.frac >= thr]
    print(f"{thr*100:6.0f}% | {stats(x[x.period == 'IS']):45s} | {stats(x[x.period == 'OOS']):45s}")
print(f"{'< 5%':>7s} | {stats(ev[(ev.frac < 0.05) & (ev.period == 'IS')]):45s} | {stats(ev[(ev.frac < 0.05) & (ev.period == 'OOS')]):45s}")

# umbral elegido con 2022-24: el menor de la grilla con media >= 2% y >= 15 dias
chosen = None
for thr in grid:
    x = ev[(ev.frac >= thr) & (ev.period == 'IS')]
    if len(x) and x.ret.mean() >= 2.0 and x.day.nunique() >= 15:
        chosen = thr
        break
print(f'\numbral elegido con 2022-24: {chosen}')
if chosen:
    d = ev[ev.frac >= chosen]
    o = d[d.period == 'OOS']
    print('  PRUEBA en 2025-26:', stats(o))
    rest = ev[ev.frac < chosen]
    days = ev.day.unique(); g = {k: v for k, v in ev.groupby('day')}
    res = []
    for _ in range(3000):
        s = pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])
        a, b = s[s.frac >= chosen].ret, s[s.frac < chosen].ret
        if len(a) and len(b):
            res.append(a.mean() - b.mean())
    lo, hi = np.percentile(res, [2.5, 97.5])
    print(f'  diferencia unida (>= umbral) - (< umbral): {d.ret.mean() - rest.ret.mean():+.2f} pp  IC95 por dia [{lo:+.2f}, {hi:+.2f}]')
    print('  resto (< umbral):', stats(rest[rest.period == "IS"]), '|', stats(rest[rest.period == "OOS"]))
    b = d.groupby('conf').agg(ret=('ret', 'mean'), k=('k', 'first'), day=('day', 'first'))
    print(f'  a nivel EPISODIO (media de la canasta por vela de senal): n={len(b)}, media {b.ret.mean():+.2f}%, acierto {(b.ret > 0).mean()*100:.0f}%, dias {b.day.nunique()}')
    for per, dd in (('IS', b[b.index < SPLIT]), ('OOS', b[b.index >= SPLIT])):
        print(f'     {per}: n={len(dd)} media {dd.ret.mean():+.2f}% acierto {(dd.ret > 0).mean()*100:.0f}%')


print('TRAMOS SIN SOLAPAR (fraccion de pares elegibles con spring en la misma vela)')
bins = [(0, 0.10, '< 10%'), (0.10, 0.20, '10-20%'), (0.20, 0.35, '20-35%'), (0.35, 1.01, '>= 35%'), (0, 0.20, '< 20% (todo lo no amplio)'), (0.20, 1.01, '>= 20% (amplia)')]
for lo_, hi_, lab in bins:
    x = ev[(ev.frac >= lo_) & (ev.frac < hi_)]
    print(f"  {lab:26s} | 2022-24: {stats(x[x.period == 'IS']):45s} | 2025-26: {stats(x[x.period == 'OOS']):45s}")
wide_ = ev[ev.frac >= 0.20]
narrow = ev[ev.frac < 0.20]
days = ev.day.unique(); g = {k: v for k, v in ev.groupby('day')}
for per in ('IS', 'OOS'):
    e2 = ev[ev.period == per]
    dd = e2.day.unique(); gg = {k: v for k, v in e2.groupby('day')}
    res = []
    for _ in range(3000):
        s_ = pd.concat([gg[dd[i]] for i in rng.integers(0, len(dd), len(dd))])
        a, b = s_[s_.frac >= 0.20].ret, s_[s_.frac < 0.20].ret
        if len(a) and len(b):
            res.append(a.mean() - b.mean())
    lo, hi = np.percentile(res, [2.5, 97.5])
    a, b = e2[e2.frac >= 0.20].ret, e2[e2.frac < 0.20].ret
    print(f'  amplia (>=20%) - no amplia, {per}: {a.mean() - b.mean():+.2f} pp  IC95 por dia [{lo:+.2f}, {hi:+.2f}]')
