"""Estructura (spring confirmado) vs 'alts golpeadas' el mismo dia. Criterio en spec.md, fijado antes."""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
HOLD, STOP, FEE, MIN_DVOL = 18, 10.0, 0.1, 20e6
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
K = 2
LO, HI = 100 * (0.05 / K / 2), 100 * (1 - 0.05 / K / 2)
rng = np.random.default_rng(49)
idx = pd.date_range('2021-12-01', '2026-09-22', freq='4h', tz='UTC')

series = {}
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    series[os.path.basename(p).split('_USDT_USDT')[0]] = pd.read_feather(p).set_index('date').sort_index()
for p in glob.glob(f'{DELISTED}/*.pkl'):
    d = pd.read_pickle(p)
    if len(d) > 100:
        series['D_' + os.path.basename(p)[:-8]] = d
cols = list(series.keys())
def wide(c):
    return pd.DataFrame({k: series[k][c].reindex(idx) for k in cols})
O, H, L, C, V = wide('open'), wide('high'), wide('low'), wide('close'), wide('volume')
n = len(idx)
sma = V.rolling(20, min_periods=20).mean()
rv = (V / sma).values
minL20 = L.rolling(20, min_periods=20).min().shift(1).values
dvol = (V * C).rolling(6, min_periods=6).sum()
elig = ((dvol >= MIN_DVOL) & V.notna()).values
r24 = (C / C.shift(6) - 1).values
Ol, Ll, Cl, Lv = O.values, L.values, C.values, L.values

RL = np.full(O.shape, np.nan)
for e in range(1, n - HOLD):
    entry = Ol[e]
    lo_ = np.nanmin(np.where(np.isnan(Ll[e:e + HOLD]), np.inf, Ll[e:e + HOLD]), axis=0)
    last = Cl[e + HOLD - 1]
    ok = np.isfinite(entry) & np.isfinite(last)
    r = np.where(lo_ <= entry * (1 - STOP / 100), -STOP, (last / entry - 1) * 100) - FEE
    r[~ok] = np.nan
    RL[e] = r

SP = np.zeros(O.shape, dtype=bool)     # spring confirmado en la vela j
BRK = np.zeros(O.shape, dtype=bool)    # ruptura con volumen >= 2.5x en la vela i (sin exigir recuperacion)
for c in range(len(cols)):
    for i in range(25, n - 1):
        lvl = minL20[i, c]
        if np.isnan(lvl) or not (Lv[i, c] < lvl) or np.isnan(rv[i, c]) or rv[i, c] < 2.5:
            continue
        BRK[i, c] = True
        for j in range(i + 1, min(i + 4, n)):
            if Cl[j, c] > lvl:
                SP[j, c] = True
                break
# B2: ruptura con volumen en j-3..j-1 y SIN spring en j, y sin haber recuperado el nivel (cierre de j <= nivel de la ruptura mas reciente)
pending = np.zeros(O.shape, dtype=bool)
lvl_at = np.where(BRK, minL20, np.nan)
for j in range(4, n):
    recent = lvl_at[j - 3:j]                                  # niveles de rupturas recientes (nan si no)
    has = np.isfinite(recent).any(axis=0)
    lvl_last = np.nanmax(np.where(np.isfinite(recent), recent, -np.inf), axis=0)
    pending[j] = has & (Cl[j] <= lvl_last) & ~SP[j]

nel = elig.sum(axis=1)
nsp = (SP & elig).sum(axis=1)
frac = np.where(nel > 0, nsp / np.maximum(nel, 1), 0)

rows = []
for j in range(30, n - HOLD - 1):
    e = j + 1
    if not (T0 <= idx[e] <= T1) or nsp[j] == 0:
        continue
    el = elig[j]
    a = np.where(SP[j] & el)[0]
    b1 = np.where(el & ~SP[j] & (r24[j] <= -0.05))[0]
    b2 = np.where(el & pending[j])[0]
    ra, rb1, rb2 = RL[e, a], RL[e, b1], RL[e, b2]
    ra, rb1, rb2 = ra[np.isfinite(ra)], rb1[np.isfinite(rb1)], rb2[np.isfinite(rb2)]
    if len(ra) == 0:
        continue
    rows.append(dict(t=idx[e], day=idx[e].normalize(), frac=frac[j], nA=len(ra), A=ra.mean(),
                     B1=rb1.mean() if len(rb1) else np.nan, nB1=len(rb1), B2=rb2.mean() if len(rb2) else np.nan, nB2=len(rb2)))
d = pd.DataFrame(rows)
d['period'] = np.where(d.t < SPLIT, 'IS', 'OOS')
print(f'velas con al menos un spring: {len(d)} | velas de capitulacion amplia (>= 20%): {(d.frac >= 0.20).sum()}')


def boot(x, col, n_=3000):
    days = x.day.unique(); g = {k: v for k, v in x.groupby('day')}
    res = [pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])[col].mean() for _ in range(n_)]
    return np.percentile(res, [LO, HI])


def report(x, label):
    print(f'\n{label}')
    print(f"  {'comparacion':16s} {'per':5s} {'velas':>5s} {'dias':>4s} | {'A (spring)':>10s} {'B':>8s} | {'dif A-B':>8s}")
    out = {}
    for name, col in (('A - B1 golpeadas', 'B1'), ('A - B2 ruptura sin recup.', 'B2')):
        y = x.dropna(subset=[col]).copy()
        y['diff'] = y.A - y[col]
        res = {}
        for per in ('IS', 'OOS', 'AMBOS'):
            z = y if per == 'AMBOS' else y[y.period == per]
            extra = ''
            if per == 'AMBOS' and len(z) > 5:
                lo, hi = boot(z, 'diff')
                res['ci'] = (lo, hi)
                extra = f"  IC{100 - 2 * LO:.1f}% [{lo:+.2f}, {hi:+.2f}]"
            res[per] = z['diff'].mean() if len(z) else np.nan
            print(f"  {name:16s} {per:5s} {len(z):5d} {z.day.nunique():4d} | {z.A.mean():+10.2f} {z[col].mean():+8.2f} | {z['diff'].mean():+8.2f}{extra}")
        out[name] = (res.get('IS', np.nan) >= 0.5 and res.get('OOS', np.nan) >= 0.5 and 'ci' in res and res['ci'][0] > 0)
    return out


v_wide = report(d[d.frac >= 0.20], 'CAPITULACION AMPLIA (>= 20% de los pares con spring)  [criterio pre-registrado]')
report(d, 'TODAS LAS VELAS CON SPRING (control)')
print('\nVEREDICTO (estructura aporta mas alla de "alts golpeadas"):', {k: ('SI' if v else 'NO') for k, v in v_wide.items()})
