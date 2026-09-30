"""Predictores de estructura sobre todos los springs (criterio en spec.md, fijado antes)."""
import glob, os, warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor

warnings.filterwarnings('ignore')
DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
LOOKBACK, CONFIRM, VOL_N, THRESH, HOLD, STOP, FEE = 20, 3, 20, 2.5, 18, -10.0, 0.1
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
K = 4
LO, HI = 100 * (0.05 / K / 2), 100 * (1 - 0.05 / K / 2)
rng = np.random.default_rng(50)

btc = pd.read_feather(f'{DATA}/BTC_USDT_USDT-4h-futures.feather').set_index('date').sort_index()
btc_c = btc['close']


def features(df, name):
    v = df['volume'].astype(float).values
    sma = pd.Series(v).rolling(VOL_N).mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        rv = np.where(sma > 0, v / sma, np.nan)
    o, h, l, c = df['open'].values, df['high'].values, df['low'].values, df['close'].values
    dv24 = (df['volume'] * df['close']).rolling(6).sum().values
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr = pd.Series(tr).rolling(14).mean().values
    support = df['low'].rolling(LOOKBACK).min().shift(1).values
    ix, n, out, seen = df.index, len(df), [], set()
    bc = btc_c.reindex(ix).values
    for i in range(190, n - 1):
        lvl = support[i]
        if np.isnan(lvl) or not l[i] < lvl:
            continue
        for j in range(i + 1, min(i + 1 + CONFIRM, n)):
            if c[j] > lvl:
                e = j + 1
                if j not in seen and not np.isnan(rv[i]) and rv[i] >= THRESH and e + HOLD <= n and dv24[j] >= 20e6 and T0 <= ix[e] <= T1:
                    seen.add(j)
                    entry = o[e]
                    ret = (STOP if (l[e:e + HOLD] <= entry * (1 + STOP / 100)).any() else (c[e + HOLD - 1] / entry - 1) * 100) - FEE
                    # H1: residuo de Huber ln(rango/cierre) ~ ln(volumen USD) + ln(ATR/cierre) sobre las 100 velas previas a i
                    w = slice(i - 100, i)
                    rng_w = np.log(np.maximum((h[w] - l[w]) / c[w], 1e-9))
                    X = np.column_stack([np.log(np.maximum(v[w] * c[w], 1.0)), np.log(np.maximum(atr[w] / c[w], 1e-9))])
                    z = np.nan
                    if np.isfinite(X).all() and np.isfinite(rng_w).all():
                        m = HuberRegressor(max_iter=200).fit(X, rng_w)
                        res = rng_w - m.predict(X)
                        mad = np.median(np.abs(res - np.median(res))) * 1.4826
                        xi = np.array([[np.log(max(v[i] * c[i], 1.0)), np.log(max(atr[i - 1] / c[i - 1], 1e-9))]])
                        yi = np.log(max((h[i] - l[i]) / c[i], 1e-9))
                        if mad > 0:
                            z = (yi - m.predict(xi)[0]) / mad
                    # H2: KER30 de las 30 velas previas a i
                    seg = c[i - 31:i]
                    ker = abs(seg[-1] - seg[0]) / max(np.abs(np.diff(seg)).sum(), 1e-12)
                    # H3 / H4: fuerza relativa 12 velas y momentum 180 velas vs BTC (en la vela de confirmacion j)
                    rs = (c[j] / c[j - 12] - 1 - (bc[j] / bc[j - 12] - 1)) * 100 if np.isfinite(bc[j]) and np.isfinite(bc[j - 12]) else np.nan
                    mom = (c[j] / c[j - 180] - 1 - (bc[j] / bc[j - 180] - 1)) * 100 if np.isfinite(bc[j]) and np.isfinite(bc[j - 180]) else np.nan
                    out.append(dict(sym=name, t=ix[e], ret=ret, z=z, ker=ker, rs=rs, mom=mom))
                break
    return out


rows = []
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    rows += features(pd.read_feather(p).set_index('date').sort_index(), os.path.basename(p).split('_USDT_USDT')[0])
for p in glob.glob(f'{DELISTED}/*.pkl'):
    d = pd.read_pickle(p)
    if len(d) > 300:
        rows += features(d, 'D_' + os.path.basename(p)[:-8])
ev = pd.DataFrame(rows)
ev['day'] = ev.t.dt.normalize()
ev['period'] = np.where(ev.t < SPLIT, 'IS', 'OOS')
print(f'springs con variables: {len(ev)} | z: {ev.z.notna().mean()*100:.0f}% | KER: {ev.ker.notna().mean()*100:.0f}% | RS: {ev.rs.notna().mean()*100:.0f}% | mom: {ev.mom.notna().mean()*100:.0f}%')
IS = ev[ev.period == 'IS']
q = {c: IS[c].quantile([1 / 3, 2 / 3]).values for c in ('z', 'ker', 'rs', 'mom')}
print('terciles (solo 2022-24):', {c: np.round(v, 3).tolist() for c, v in q.items()})

# cada hipotesis: (variable, direccion: +1 = tercil ALTO mejor, -1 = tercil BAJO mejor)
H = {'H1 esfuerzo-resultado (z bajo mejor)': ('z', -1), 'H2 causa/rango (KER bajo mejor)': ('ker', -1),
     'H3 fuerza relativa 48h (alta mejor)': ('rs', +1), 'H4 momentum 30d (alto mejor)': ('mom', +1)}


def boot(x, m_a, m_b, n_=3000):
    days = x.day.unique(); g = {k: v for k, v in x.assign(_a=m_a, _b=m_b).groupby('day')}
    res = []
    for _ in range(n_):
        s = pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])
        a, b = s.loc[s._a, 'ret'], s.loc[s._b, 'ret']
        if len(a) and len(b):
            res.append(a.mean() - b.mean())
    return np.percentile(res, [LO, HI])


print(f"\n{'hipotesis':38s} {'per':5s} {'n mejor':>7s} {'media':>7s} {'dias':>4s} | {'n peor':>6s} {'media':>7s} {'dias':>4s} | dif (mejor - peor)")
verdict = {}
for name, (col, sign) in H.items():
    lo_c, hi_c = q[col]
    res = {}
    for per in ('IS', 'OOS', 'AMBOS'):
        x = (ev if per == 'AMBOS' else ev[ev.period == per]).dropna(subset=[col]).reset_index(drop=True)
        top, bot = (x[col] >= hi_c), (x[col] <= lo_c)
        better, worse = (top, bot) if sign > 0 else (bot, top)
        a, b = x[better], x[worse]
        dif = a.ret.mean() - b.ret.mean()
        extra = ''
        if per == 'AMBOS':
            lo, hi = boot(x, better, worse)
            res['ci'] = (lo, hi)
            extra = f"  IC{100 - 2 * LO:.2f}% [{lo:+.2f}, {hi:+.2f}]"
        res[per] = (dif, a.day.nunique(), b.day.nunique())
        print(f"{name:38s} {per:5s} {len(a):7d} {a.ret.mean():+7.2f} {a.day.nunique():4d} | {len(b):6d} {b.ret.mean():+7.2f} {b.day.nunique():4d} | {dif:+6.2f}{extra}")
    lo, hi = res['ci']
    verdict[name] = bool(res['IS'][0] > 0 and res['OOS'][0] > 0 and lo > 0 and res['AMBOS'][0] >= 0.5
                         and min(res['IS'][1], res['IS'][2], res['OOS'][1], res['OOS'][2]) >= 30)
print('\nCorrelacion de rangos (Spearman) de cada variable con el retorno a 72h:')
for col in ('z', 'ker', 'rs', 'mom'):
    x = ev.dropna(subset=[col])
    print(f"  {col:4s} todos {x[col].corr(x.ret, method='spearman'):+.3f} | 2022-24 {x[x.period=='IS'][col].corr(x[x.period=='IS'].ret, method='spearman'):+.3f} | 2025-26 {x[x.period=='OOS'][col].corr(x[x.period=='OOS'].ret, method='spearman'):+.3f}")
print('\nVEREDICTO (criterio pre-registrado):')
for k, v in verdict.items():
    print(f"  {k}: {'APRUEBA' if v else 'NO aprueba'}")
