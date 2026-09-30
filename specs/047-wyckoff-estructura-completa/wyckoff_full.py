"""Estructura completa de Wyckoff (criterios en spec.md, fijados antes)."""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
HOLD, STOP, FEE, MIN_DVOL = 18, 10.0, 0.1, 20e6
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
K = 7
LO, HI = 100 * (0.05 / K / 2), 100 * (1 - 0.05 / K / 2)
rng = np.random.default_rng(47)
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
print(f'universo: {len(cols)} simbolos')

sma = V.rolling(20, min_periods=20).mean()
rv = V / sma
rng_ = H - L
tr = pd.concat([(H - L).stack(), (H - C.shift()).abs().stack(), (L - C.shift()).abs().stack()], axis=1).max(axis=1).unstack()
atr = tr.rolling(14, min_periods=14).mean().shift(1)
minL20, minL30 = L.rolling(20, min_periods=20).min().shift(1), L.rolling(30, min_periods=30).min().shift(1)
maxH30 = H.rolling(30, min_periods=30).max().shift(1)
dvol = (V * C).rolling(6, min_periods=6).sum()
elig = (dvol >= MIN_DVOL) & V.notna()

# retornos por vela de ENTRADA e (apertura de e, 72h despues) para largo y corto, ya netos
n = len(idx)
Ol, Hl, Ll, Cl = O.values, H.values, L.values, C.values
RL = np.full(O.shape, np.nan)
RS = np.full(O.shape, np.nan)
for e in range(1, n - HOLD):
    entry = Ol[e]
    lo_ = np.nanmin(np.where(np.isnan(Ll[e:e + HOLD]), np.inf, Ll[e:e + HOLD]), axis=0)
    hi_ = np.nanmax(np.where(np.isnan(Hl[e:e + HOLD]), -np.inf, Hl[e:e + HOLD]), axis=0)
    last = Cl[e + HOLD - 1]
    ok = np.isfinite(entry) & np.isfinite(last)
    RL[e] = np.where(lo_ <= entry * (1 - STOP / 100), -STOP, (last / entry - 1) * 100) - FEE
    RS[e] = np.where(hi_ >= entry * (1 + STOP / 100), -STOP, -(last / entry - 1) * 100) - FEE
    RL[e][~ok] = np.nan
    RS[e][~ok] = np.nan


def uncond(R):
    m = R[::6]
    e = elig.values[::6]
    v = m[e & np.isfinite(m)]
    return v.mean()


UL, US = uncond(RL), uncond(RS)
print(f'media incondicional (cualquier vela elegible): largo {UL:+.2f}%, corto {US:+.2f}%')

Hv, Lv, Cv, Ov, Vv, smav, rvv = H.values, L.values, C.values, O.values, V.values, sma.values, rv.values
col_ix = {k: i for i, k in enumerate(cols)}


def collect(mask_first, follow, side):
    """mask_first: matriz booleana del evento base (j). follow(i_sym, i) -> indice r de la vela de entrada-1 (o None) para eventos de 2a etapa."""
    rows = []
    R = RL if side == 'long' else RS
    js, cs = np.where(mask_first.values if hasattr(mask_first, 'values') else mask_first)
    for j, c in zip(js, cs):
        t_sig = j
        if follow is not None:
            r = follow(c, j)
            if r is None:
                continue
            t_sig = r
        e = t_sig + 1
        if e >= n - HOLD or not (T0 <= idx[e] <= T1):
            continue
        val = R[e, c]
        if np.isfinite(val):
            rows.append(dict(sym=cols[c], t=idx[e], ret=val))
    d = pd.DataFrame(rows)
    if len(d):
        d['day'] = d.t.dt.normalize()
        d['period'] = np.where(d.t < SPLIT, 'IS', 'OOS')
    return d


# --- E1 SC, E3 SOS, E5 SOW (eventos base)
m_sc = (L <= minL20) & (rv >= 3.0) & (rng_ >= 1.5 * atr) & (C >= L + 0.5 * rng_) & elig
m_sos = (C > maxH30) & (rv >= 2.0) & (C >= L + (2 / 3) * rng_) & elig
m_sow = (C < minL30) & (rv >= 2.0) & (C <= L + (1 / 3) * rng_) & elig


def follow_st(c, i):
    lvl = Lv[i, c]
    for r in range(i + 3, min(i + 16, n - 1)):
        if np.isnan(Lv[r, c]):
            continue
        if abs(Lv[r, c] / lvl - 1) <= 0.03 and Vv[r, c] <= 0.7 * Vv[i, c] and Cv[r, c] > Ov[r, c]:
            return r
    return None


def follow_lps(c, i):
    level = maxH30.values[i, c]
    for r in range(i + 1, min(i + 6, n - 1)):
        if np.isnan(Lv[r, c]) or np.isnan(smav[r, c]):
            continue
        if Lv[r, c] <= level * 1.01 and Cv[r, c] >= level * 0.99 and Vv[r, c] <= smav[r, c] and Cv[r, c] > Ov[r, c]:
            return r
    return None


def follow_lpsy(c, i):
    level = minL30.values[i, c]
    for r in range(i + 1, min(i + 6, n - 1)):
        if np.isnan(Hv[r, c]) or np.isnan(smav[r, c]):
            continue
        if Hv[r, c] >= level * 0.99 and Cv[r, c] <= level * 1.01 and Vv[r, c] <= smav[r, c] and Cv[r, c] < Ov[r, c]:
            return r
    return None


def dedup_first(d, hours=72):
    """Un evento por simbolo dentro de la ventana de 72h (evita contar la misma senal repetida)."""
    if not len(d):
        return d
    d = d.sort_values(['sym', 't'])
    keep, last = [], {}
    for r in d.itertuples():
        if r.sym not in last or (r.t - last[r.sym]) > pd.Timedelta(hours=hours):
            keep.append(r.Index)
            last[r.sym] = r.t
        last[r.sym] = r.t
    return d.loc[keep]


E = {
    'E1 clímax de venta (SC)': (dedup_first(collect(m_sc, None, 'long')), 'long'),
    'E2 test secundario (ST)': (dedup_first(collect(m_sc, follow_st, 'long')), 'long'),
    'E3 signo de fortaleza (SOS)': (dedup_first(collect(m_sos, None, 'long')), 'long'),
    'E4 backup / LPS': (dedup_first(collect(m_sos, follow_lps, 'long')), 'long'),
    'E5 signo de debilidad (SOW)': (dedup_first(collect(m_sow, None, 'short')), 'short'),
    'E6 LPSY': (dedup_first(collect(m_sow, follow_lpsy, 'short')), 'short'),
}


def boot_excess(d, base, n_=3000):
    days = d.day.unique()
    g = {k: v for k, v in d.groupby('day')}
    res = [pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))]).ret.mean() - base for _ in range(n_)]
    return np.percentile(res, [LO, HI])


print(f"\n{'evento':28s} {'n':>5s} {'dias':>4s} | {'2022-24':21s} | {'2025-26':21s} | {'unido':>6s} {'exceso IC' :>22s}")
verdict = {}
for name, (d, side) in E.items():
    base = UL if side == 'long' else US
    a, b = d[d.period == 'IS'], d[d.period == 'OOS']
    lo, hi = boot_excess(d, base) if len(d) > 5 else (np.nan, np.nan)
    print(f"{name:28s} {len(d):5d} {d.day.nunique():4d} | n={len(a):4d} {a.ret.mean():+6.2f}% {(a.ret > 0).mean()*100:3.0f}% | n={len(b):4d} {b.ret.mean():+6.2f}% {(b.ret > 0).mean()*100:3.0f}% | {d.ret.mean():+6.2f} [{lo:+6.2f},{hi:+6.2f}]")
    ok = (a.ret.mean() >= 1.0 and b.ret.mean() >= 1.0 and lo > 0 and a.day.nunique() >= 30 and b.day.nunique() >= 30)
    verdict[name] = ok

# --- E7: spring tras caida previa (fase A)
def spring_events():
    out = []
    lows, closes = Lv, Cv
    minL = minL20.values
    for c in range(len(cols)):
        seen = set()
        for i in range(60, n - 1):
            lvl = minL[i, c]
            if np.isnan(lvl) or not (lows[i, c] < lvl) or np.isnan(rvv[i, c]):
                continue
            for j in range(i + 1, min(i + 4, n)):
                if closes[j, c] > lvl:
                    if j not in seen and rvv[i, c] >= 2.5 and elig.values[j, c]:
                        seen.add(j)
                        e = j + 1
                        if e < n - HOLD and T0 <= idx[e] <= T1 and np.isfinite(RL[e, c]) and np.isfinite(Cv[j - 60, c]):
                            out.append(dict(sym=cols[c], t=idx[e], ret=RL[e, c], prior=(closes[j, c] / Cv[j - 60, c] - 1) * 100))
                    break
    d = pd.DataFrame(out)
    d['day'] = d.t.dt.normalize()
    d['period'] = np.where(d.t < SPLIT, 'IS', 'OOS')
    return d


sp = spring_events()
sp['fase_a'] = sp.prior <= -20
print(f"\nE7 springs: {len(sp)} | con caida previa <= -20% en 60 velas: {int(sp.fase_a.sum())} ({sp.fase_a.mean()*100:.0f}%)")
res = {}
for per in ('IS', 'OOS', 'AMBOS'):
    x = sp if per == 'AMBOS' else sp[sp.period == per]
    a, b = x[x.fase_a], x[~x.fase_a]
    dif = a.ret.mean() - b.ret.mean()
    extra = ''
    if per == 'AMBOS':
        days = x.day.unique(); g = {k: v for k, v in x.groupby('day')}
        rr = []
        for _ in range(3000):
            s_ = pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])
            aa, bb = s_[s_.fase_a].ret, s_[~s_.fase_a].ret
            if len(aa) and len(bb):
                rr.append(aa.mean() - bb.mean())
        lo, hi = np.percentile(rr, [LO, HI]); res['ci'] = (lo, hi)
        extra = f'  IC{100 - 2 * LO:.1f}% [{lo:+.2f}, {hi:+.2f}]'
    res[per] = (dif, a.day.nunique(), b.day.nunique())
    print(f"  {per:5s} con caida previa n={len(a):4d} {a.ret.mean():+6.2f}% ({(a.ret > 0).mean()*100:3.0f}%) | sin n={len(b):4d} {b.ret.mean():+6.2f}% ({(b.ret > 0).mean()*100:3.0f}%) | dif {dif:+5.2f}{extra}")
verdict['E7 spring tras caida previa'] = (res['IS'][0] > 0 and res['OOS'][0] > 0 and res['ci'][0] > 0 and res['AMBOS'][0] >= 0.5
                                          and min(res['IS'][1], res['IS'][2], res['OOS'][1], res['OOS'][2]) >= 30)
print('\nVEREDICTO (criterio pre-registrado):')
for k, v in verdict.items():
    print(f"  {k}: {'APRUEBA' if v else 'NO aprueba'}")
