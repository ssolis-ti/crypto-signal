"""OI y long/short historicos como contexto del spring (criterio en spec.md, fijado antes)."""
import os
import numpy as np
import pandas as pd

MET = '/exp044/metrics'
rng = np.random.default_rng(47)
SPLIT = pd.Timestamp('2025-01-01', tz='UTC')
K = 2
LO, HI = 100 * (0.05 / K / 2), 100 * (1 - 0.05 / K / 2)
ev = pd.read_csv('/exp044/events_universo.csv', parse_dates=['conf', 't'])
ev['conf'] = pd.to_datetime(ev.conf, utc=True)
ev['t'] = pd.to_datetime(ev.t, utc=True)
cache = {}


def day_frame(sym, day):
    key = (sym, day)
    if key not in cache:
        p = f'{MET}/{sym}_{day}.pkl'
        cache[key] = pd.read_pickle(p) if os.path.exists(p) else None
    return cache[key]


def latest(sym, ts):
    """Ultima fila de metricas con create_time <= ts (busca en el dia de ts y en el anterior)."""
    for dd in (ts.normalize(), ts.normalize() - pd.Timedelta(days=1)):
        f = day_frame(sym, dd.strftime('%Y-%m-%d'))
        if f is not None:
            f = f[f.index <= ts]
            if len(f):
                return f.iloc[-1]
    return None


rows = []
for r in ev.itertuples():
    sym = (r.sym[2:] if r.sym.startswith('D_') else r.sym) + 'USDT'
    now, ago = latest(sym, r.t), latest(sym, r.t - pd.Timedelta(hours=24))
    oi_chg = ls = np.nan
    if now is not None:
        ls = now['count_long_short_ratio']
        if ago is not None and ago['sum_open_interest_value'] > 0:
            oi_chg = (now['sum_open_interest_value'] / ago['sum_open_interest_value'] - 1) * 100
    rows.append(dict(sym=r.sym, t=r.t, ret=r.ret, day=r.t.normalize(), oi_chg=oi_chg, ls=ls,
                     period='IS' if r.t < SPLIT else 'OOS'))
d = pd.DataFrame(rows)
print(f"springs: {len(d)} | con OI 24h: {d.oi_chg.notna().mean()*100:.0f}% | con long/short: {d.ls.notna().mean()*100:.0f}%")
print(f"  por periodo (cobertura OI): IS {d[d.period=='IS'].oi_chg.notna().mean()*100:.0f}%  OOS {d[d.period=='OOS'].oi_chg.notna().mean()*100:.0f}%")
print(f"  OI 24h (%): p5 {d.oi_chg.quantile(.05):+.1f}  p25 {d.oi_chg.quantile(.25):+.1f}  mediana {d.oi_chg.median():+.1f}  p75 {d.oi_chg.quantile(.75):+.1f}  p95 {d.oi_chg.quantile(.95):+.1f}")
print(f"  long/short: p5 {d.ls.quantile(.05):.2f}  mediana {d.ls.median():.2f}  p95 {d.ls.quantile(.95):.2f}")

IS = d[d.period == 'IS']
cuts = {'oi_chg': IS.oi_chg.quantile([1 / 3, 2 / 3]).values, 'ls': IS.ls.quantile([1 / 3, 2 / 3]).values}
print(f"cortes de tercil (solo 2022-24): OI {cuts['oi_chg'].round(2)}, long/short {cuts['ls'].round(3)}")


def boot(x, m):
    days = x['day'].unique()
    g = {k: v for k, v in x.assign(_m=m).groupby('day')}
    res = []
    for _ in range(3000):
        s = pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])
        a, b = s.loc[s._m, 'ret'], s.loc[~s._m, 'ret']
        if len(a) and len(b):
            res.append(a.mean() - b.mean())
    return np.percentile(res, [LO, HI])


H = {
    'H1 OI 24h en tercil inferior (limpieza)': ('oi_chg', lambda x: x.oi_chg <= cuts['oi_chg'][0], +1),
    'H2 long/short en tercil inferior (cortos)': ('ls', lambda x: x.ls <= cuts['ls'][0], +1),
    'placebo: OI 24h en tercil superior': ('oi_chg', lambda x: x.oi_chg >= cuts['oi_chg'][1], 0),
}
print(f"\n{'hipotesis':42s} {'per':5s} {'n A':>5s} {'media':>7s} {'acierto':>7s} {'dias':>4s} | {'n B':>5s} {'media':>7s} {'acierto':>7s} | dif(A-B)")
verdict = {}
for name, (col, cell, sign) in H.items():
    res = {}
    for per in ('IS', 'OOS', 'AMBOS'):
        x = (d if per == 'AMBOS' else d[d.period == per]).dropna(subset=[col]).reset_index(drop=True)
        m = cell(x).astype(bool)
        a, b = x[m], x[~m]
        dif = a.ret.mean() - b.ret.mean()
        extra = ''
        if per == 'AMBOS':
            lo, hi = boot(x, m)
            res['ci'] = (lo, hi)
            extra = f"  IC{100 - 2 * LO:.1f}% [{lo:+.2f}, {hi:+.2f}]"
        res[per] = (dif, a.day.nunique(), b.day.nunique())
        print(f"{name:42s} {per:5s} {len(a):5d} {a.ret.mean():+7.2f} {(a.ret > 0).mean()*100:6.0f}% {a.day.nunique():4d} | {len(b):5d} {b.ret.mean():+7.2f} {(b.ret > 0).mean()*100:6.0f}% | {dif:+5.2f}{extra}")
    if sign:
        lo, hi = res['ci']
        ok = (res['IS'][0] > 0 and res['OOS'][0] > 0 and lo > 0 and res['AMBOS'][0] >= 0.5
              and min(res['IS'][1], res['IS'][2], res['OOS'][1], res['OOS'][2]) >= 30)
        verdict[name] = ok
print('\nVEREDICTO:', {k: ('APRUEBA' if v else 'NO aprueba') for k, v in verdict.items()})
