"""Lado corto en espejo (criterios en spec.md, fijados antes)."""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
HOLD, STOP, FEE, MIN_DVOL = 18, 10.0, 0.1, 20e6
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
K = 5
LO, HI = 100 * (0.05 / K / 2), 100 * (1 - 0.05 / K / 2)
rng = np.random.default_rng(48)
idx = pd.date_range('2021-12-01', '2026-09-22', freq='4h', tz='UTC')

series, lab = {}, []
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    b = os.path.basename(p).split('_USDT_USDT')[0]
    series[b] = pd.read_feather(p).set_index('date').sort_index()
    lab.append(b)
for p in glob.glob(f'{DELISTED}/*.pkl'):
    d = pd.read_pickle(p)
    if len(d) > 100:
        series['D_' + os.path.basename(p)[:-8]] = d
cols = list(series.keys())
def wide(c):
    return pd.DataFrame({k: series[k][c].reindex(idx) for k in cols})
O, H, L, C, V = wide('open'), wide('high'), wide('low'), wide('close'), wide('volume')
print(f'universo: {len(cols)} simbolos')

sma = V.rolling(20, min_periods=20).mean()
rv = V / sma
rng_ = H - L
tr = pd.concat([(H - L).stack(), (H - C.shift()).abs().stack(), (L - C.shift()).abs().stack()], axis=1).max(axis=1).unstack()
atr = tr.rolling(14, min_periods=14).mean().shift(1)
maxH20 = H.rolling(20, min_periods=20).max().shift(1)
dvol = (V * C).rolling(6, min_periods=6).sum()
elig = (dvol >= MIN_DVOL) & V.notna()

n = len(idx)
Ol, Hl, Ll, Cl = O.values, H.values, L.values, C.values
RS = np.full(O.shape, np.nan)   # retorno del SHORT por vela de entrada e
for e in range(1, n - HOLD):
    entry = Ol[e]
    hi_ = np.nanmax(np.where(np.isnan(Hl[e:e + HOLD]), -np.inf, Hl[e:e + HOLD]), axis=0)
    last = Cl[e + HOLD - 1]
    ok = np.isfinite(entry) & np.isfinite(last)
    r = np.where(hi_ >= entry * (1 + STOP / 100), -STOP, -(last / entry - 1) * 100) - FEE
    r[~ok] = np.nan
    RS[e] = r
elv = elig.values
m_ = RS[::6]
US = m_[elv[::6] & np.isfinite(m_)].mean()
print(f'media incondicional del SHORT (cualquier vela elegible): {US:+.2f}%')


def tag(d):
    d = d.copy()
    d['day'] = d.t.dt.normalize()
    d['period'] = np.where(d.t < SPLIT, 'IS', 'OOS')
    return d


def boot_excess(d, base, col='ret', n_=3000):
    days = d.day.unique()
    g = {k: v for k, v in d.groupby('day')}
    res = [pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])[col].mean() - base for _ in range(n_)]
    return np.percentile(res, [LO, HI])


def dedup_first(d, hours=72):
    d = d.sort_values(['sym', 't'])
    keep, last = [], {}
    for r in d.itertuples():
        if r.sym not in last or (r.t - last[r.sym]) > pd.Timedelta(hours=hours):
            keep.append(r.Index)
        last[r.sym] = r.t
    return d.loc[keep]


def episodes(times, hours=72):
    out, last = [], None
    for t in sorted(times):
        if last is None or (t - last) > pd.Timedelta(hours=hours):
            out.append(t)
        last = t
    return out


verdict = {}
print(f"\n{'senal':34s} {'n':>5s} {'dias':>4s} | {'2022-24':20s} | {'2025-26':20s} | {'unido':>6s} {'exceso IC99%':>20s}")

def show(name, d, dmin=30, key=None):
    a, b = d[d.period == 'IS'], d[d.period == 'OOS']
    lo, hi = boot_excess(d, US)
    print(f"{name:34s} {len(d):5d} {d.day.nunique():4d} | n={len(a):4d} {a.ret.mean():+6.2f}% {(a.ret > 0).mean()*100:3.0f}% | n={len(b):4d} {b.ret.mean():+6.2f}% {(b.ret > 0).mean()*100:3.0f}% | {d.ret.mean():+6.2f} [{lo:+6.2f},{hi:+6.2f}]")
    verdict[key or name] = bool(a.ret.mean() >= 1.0 and b.ret.mean() >= 1.0 and lo > 0 and a.day.nunique() >= dmin and b.day.nunique() >= dmin)

# --- S3 climax de compra (BC) y S2 subida >= 15% en 24h (un evento por simbolo cada 72h)
def events_from_mask(mask):
    js, cs = np.where(mask.values)
    rows = []
    for j, c in zip(js, cs):
        e = j + 1
        if e < n - HOLD and T0 <= idx[e] <= T1 and np.isfinite(RS[e, c]):
            rows.append(dict(sym=cols[c], t=idx[e], ret=RS[e, c]))
    return dedup_first(pd.DataFrame(rows)) if rows else pd.DataFrame(columns=['sym', 't', 'ret'])


m_bc = (H >= maxH20) & (rv >= 3.0) & (rng_ >= 1.5 * atr) & (C <= L + 0.5 * rng_) & elig
m_pump = ((C / C.shift(6) - 1) >= 0.15) & elig
show('S2 subida >= +15% en 24h', tag(events_from_mask(m_pump)))
show('S3 climax de compra (BC)', tag(events_from_mask(m_bc)))

# --- S5 amplitud de maximos (canasta)
new_hi = (H >= maxH20) & (rv >= 2.0) & elig
frac_hi = new_hi.sum(axis=1) / elig.sum(axis=1).replace(0, np.nan)
sig = frac_hi[(frac_hi >= 0.25) & (elig.sum(axis=1) >= 5) & (frac_hi.index >= T0) & (frac_hi.index <= T1)]
rows = []
for t in episodes(sig.index):
    j = idx.get_loc(t)
    e = j + 1
    if e < n - HOLD:
        cs = np.where(new_hi.values[j])[0]
        vals = RS[e, cs]
        vals = vals[np.isfinite(vals)]
        if len(vals):
            rows.append(dict(sym='basket', t=idx[e], ret=vals.mean()))
show('S5 amplitud de maximos >= 25%', tag(pd.DataFrame(rows)), dmin=20)

# --- S4 funding agregado alto (canasta de todos los elegibles)
fund = {}
for b in lab:
    p = f'{DATA}/{b}_USDT_USDT-1h-funding_rate.feather'
    if os.path.exists(p):
        f = pd.read_feather(p).set_index('date').sort_index()['funding_rate']
        fund[b] = f.reindex(idx, method='ffill')
F = pd.DataFrame(fund)
med = F.median(axis=1)
thr = med[(med.index >= T0) & (med.index < SPLIT)].quantile(0.90)
sig4 = med[(med >= thr) & (med.index >= T0) & (med.index <= T1)]
print(f'funding agregado: umbral decil superior (2022-24) = {thr*100:.4f}% por pago')
rows = []
for t in episodes(sig4.index):
    j = idx.get_loc(t)
    e = j + 1
    if e < n - HOLD:
        vals = RS[e, np.where(elv[j])[0]]
        vals = vals[np.isfinite(vals)]
        if len(vals):
            rows.append(dict(sym='basket', t=idx[e], ret=vals.mean()))
show('S4 funding agregado en decil alto', tag(pd.DataFrame(rows)), dmin=20)

# --- S1 clúster de upthrusts confirmados
minH = maxH20.values
Hv, Cv, rvv = H.values, C.values, rv.values
ev_rows = []
for c in range(len(cols)):
    seen = set()
    for i in range(25, n - 1):
        lvl = minH[i, c]
        if np.isnan(lvl) or not (Hv[i, c] > lvl) or np.isnan(rvv[i, c]):
            continue
        for j in range(i + 1, min(i + 4, n)):
            if Cv[j, c] < lvl:
                e = j + 1
                if j not in seen and rvv[i, c] >= 2.5 and elv[j, c] and e < n - HOLD and T0 <= idx[e] <= T1 and np.isfinite(RS[e, c]):
                    seen.add(j)
                    ev_rows.append(dict(sym=cols[c], conf=idx[j], t=idx[e], ret=RS[e, c]))
                break
u = pd.DataFrame(ev_rows)
u['k'] = u.groupby('conf').conf.transform('count')
u['elig_n'] = u.conf.map(elig.sum(axis=1))
u['frac'] = u.k / u.elig_n
u = tag(u)
print(f"\nS1 upthrusts confirmados: {len(u)} | fraccion de pares con upthrust en la vela: p50 {u.frac.median():.2f}, p90 {u.frac.quantile(.9):.2f}")
print(f"{'tramo (fraccion de pares)':28s} | {'2022-24':38s} | {'2025-26':38s}")
def st(x):
    return f"n={len(x):4d} media={x.ret.mean():+6.2f}% acierto={(x.ret > 0).mean()*100:3.0f}% dias={x.day.nunique():3d}"
for lo_, hi_, lab_ in ((0, 0.10, '< 10%'), (0.10, 0.20, '10-20%'), (0.20, 0.35, '20-35%'), (0.35, 1.01, '>= 35%'), (0, 0.20, '< 20%'), (0.20, 1.01, '>= 20% (amplio)')):
    x = u[(u.frac >= lo_) & (u.frac < hi_)]
    print(f"{lab_:28s} | {st(x[x.period == 'IS']):38s} | {st(x[x.period == 'OOS']):38s}")
res = {}
for per in ('IS', 'OOS', 'AMBOS'):
    x = u if per == 'AMBOS' else u[u.period == per]
    a, b = x[x.frac >= 0.20], x[x.frac < 0.20]
    dif = a.ret.mean() - b.ret.mean()
    if per == 'AMBOS':
        days = x.day.unique(); g = {k: v for k, v in x.groupby('day')}
        rr = []
        for _ in range(3000):
            s_ = pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])
            aa, bb = s_[s_.frac >= 0.20].ret, s_[s_.frac < 0.20].ret
            if len(aa) and len(bb):
                rr.append(aa.mean() - bb.mean())
        res['ci'] = np.percentile(rr, [LO, HI])
    res[per] = (dif, a.ret.mean(), a.day.nunique(), b.day.nunique())
    print(f"  amplio - no amplio, {per}: {dif:+.2f} pp" + (f"  IC{100 - 2 * LO:.0f}% [{res['ci'][0]:+.2f}, {res['ci'][1]:+.2f}]" if per == 'AMBOS' else ''))
verdict['S1 clúster de upthrusts'] = bool(res['IS'][0] > 0 and res['OOS'][0] > 0 and res['ci'][0] > 0 and res['AMBOS'][0] >= 0.5
                                         and res['IS'][1] >= 1.0 and res['OOS'][1] >= 1.0 and min(res['IS'][2], res['OOS'][2]) >= 30)
print('\nVEREDICTO (criterio pre-registrado):')
for k, v in verdict.items():
    print(f"  {k}: {'APRUEBA' if v else 'NO aprueba'}")
