"""Spec 053: la correlacion entre pares como variable de estado del edge del Spring. Definido ANTES de ver resultados.

Variable: rho = correlacion media entre pares (retornos log de 1h, ultimos 7 dias, 49 pares del laboratorio) medida al
CIERRE de la vela de confirmacion (solo datos anteriores a la entrada). Tambien disp = desviacion estandar entre pares del
retorno de las ultimas 24 h.
Terciles de rho fijados con la muestra IS (2022-24) y aplicados igual a OOS (2025-26).
Unidad de analisis: el DIA-VELA (canasta equiponderada de todos los springs entrados en la misma vela), 72 h, stop -10%.
Criterio de aprobacion: tercil alto menos tercil bajo >= 0.5 pp, IC95 bootstrap por dia sin 0, mismo signo en IS y OOS.
Segunda pregunta (contagio): dado un spring aislado (k<=2), rho alto predice que la vela se vuelva amplia (frac>=0.2)?
"""
import glob
import os

import numpy as np
import pandas as pd

D = '/freqtrade/user_data/data/binance/futures'
ev = pd.read_csv('/freqtrade/user_data/events_universo.csv', parse_dates=['conf', 't'])
ev['t'] = pd.to_datetime(ev['t'], utc=True)
ev['conf'] = pd.to_datetime(ev['conf'], utc=True)

closes = {}
for f in sorted(glob.glob(f'{D}/*-1h-futures.feather')):
    name = os.path.basename(f).split('_USDT')[0]
    df = pd.read_feather(f)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    closes[name] = df.set_index('date')['close']
px = pd.DataFrame(closes).sort_index()
r = np.log(px).diff()

# vela: conf es el open de la vela de confirmacion; cierra a conf+4h = t (entrada). Estado medido a t (cierre 1h anterior a t)
times = sorted(ev['t'].unique())
rows = {}
for t in times:
    t = pd.Timestamp(t)
    w = r.loc[t - pd.Timedelta(hours=168):t - pd.Timedelta(hours=1)].dropna(axis=1, thresh=120)
    if w.shape[1] < 15:
        continue
    c = w.corr().values
    rho = np.nanmean(c[np.triu_indices_from(c, 1)])
    last24 = r.loc[t - pd.Timedelta(hours=24):t - pd.Timedelta(hours=1)].sum()
    rows[t] = (rho, last24.std(), last24.mean())
st = pd.DataFrame(rows, index=['rho', 'disp', 'mkt24']).T
st.index.name = 't'

# canasta por vela
g = ev.groupby('t').agg(ret=('ret', 'mean'), k=('k', 'max'), frac=('frac', 'max'), n=('ret', 'size')).join(st, how='inner').reset_index()
g['day'] = g['t'].dt.floor('D')
split = pd.Timestamp('2025-01-01', tz='UTC')
IS, OOS = g[g.t < split], g[g.t >= split]
rng = np.random.default_rng(53)


def boot(a, b, n=5000):
    a, b = a.values, b.values
    if len(a) < 5 or len(b) < 5:
        return np.nan, np.nan
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return np.percentile(d, [2.5, 97.5])


def report(name, col):
    q1, q2 = IS[col].quantile([1 / 3, 2 / 3])
    print(f'\n### {name}: cortes IS terciles {q1:.3f} / {q2:.3f}')
    for lab, part in (('IS 2022-24', IS), ('OOS 2025-26', OOS)):
        lo, hi = part[part[col] <= q1], part[part[col] >= q2]
        d = hi['ret'].mean() - lo['ret'].mean()
        ci = boot(hi['ret'], lo['ret'])
        print(f'{lab}: bajo n={len(lo):3d} media {lo.ret.mean():5.2f}% | alto n={len(hi):3d} media {hi.ret.mean():5.2f}% | alto-bajo {d:5.2f} pp IC[{ci[0]:5.2f},{ci[1]:5.2f}]')
    for lab, part in (('IS', IS), ('OOS', OOS)):
        print(f'  corr(estado, ret) {lab}: {part[col].corr(part.ret):.3f} (n={len(part)}); corr con k: {part[col].corr(part.k):.3f}')


print(f'velas con springs: {len(g)} (IS {len(IS)}, OOS {len(OOS)})')
report('correlacion media 7d (rho)', 'rho')
report('dispersion entre pares 24h', 'disp')
report('retorno medio del mercado 24h', 'mkt24')

print('\n### Contagio: springs aislados (k<=2): ¿rho alto -> vela amplia (frac>=0.2)?')
for lab, part in (('IS', IS), ('OOS', OOS)):
    iso = part[part.k <= 2]
    q = IS['rho'].quantile([1 / 3, 2 / 3]).values
    for nm, sub in (('rho bajo', iso[iso.rho <= q[0]]), ('rho alto', iso[iso.rho >= q[1]])):
        print(f'{lab} {nm}: n={len(sub)}, frac amplia {100 * (sub.frac >= 0.2).mean():4.1f}%, media {sub.ret.mean():5.2f}%')
print('\nRetorno por vela ancha vs no (todas):')
for lab, part in (('IS', IS), ('OOS', OOS)):
    w = part[part.frac >= 0.2]
    print(f'{lab}: anchas n={len(w)} media {w.ret.mean():5.2f}% rho medio {w.rho.mean():.3f} | resto n={len(part) - len(w)} media {part[part.frac < 0.2].ret.mean():5.2f}% rho medio {part[part.frac < 0.2].rho.mean():.3f}')
