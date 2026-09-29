"""Amplitud de capitulacion (criterio en spec.md, fijado antes)."""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
LOOKBACK, VOL_N, HOLD = 20, 20, 18
THR_VOL, MIN_DVOL, MIN_PAIRS = 2.0, 20e6, 5
STOP, FEE = -10.0, 0.1
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
rng = np.random.default_rng(44)

series = {}
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    base = os.path.basename(p).split('_USDT_USDT')[0]
    series[base] = pd.read_feather(p).set_index('date').sort_index()
n_surv = len(series)
for p in glob.glob(f'{DELISTED}/*.pkl'):
    series['D_' + os.path.basename(p)[:-8]] = pd.read_pickle(p)
print(f'universo: {n_surv} pares del laboratorio + {len(series) - n_surv} deslistados')

idx = pd.date_range('2021-12-01', '2026-09-22', freq='4h', tz='UTC')
def wide(col):
    return pd.DataFrame({k: v[col].reindex(idx) for k, v in series.items()})
O, H, L, C, V = wide('open'), wide('high'), wide('low'), wide('close'), wide('volume')

sma = V.rolling(VOL_N, min_periods=VOL_N).mean()
rv = V / sma
prev_min = L.rolling(LOOKBACK, min_periods=LOOKBACK).min().shift(1)
new_low = (L <= prev_min)
dvol = (V * C).rolling(6, min_periods=6).sum()
eligible = (dvol >= MIN_DVOL) & V.notna() & prev_min.notna()
capit = new_low & (rv >= THR_VOL) & eligible

# retorno 72h por par/vela de entrada (t+1): stop -10% sobre minimos, salida al cierre de la 18a vela
n = len(idx)
Ol, Ll, Cl = O.values, L.values, C.values
ret = np.full(O.shape, np.nan)
for i in range(n - HOLD - 1):
    e = i + 1
    entry = Ol[e]
    seg_low = np.nanmin(np.where(np.isnan(Ll[e:e + HOLD]), np.inf, Ll[e:e + HOLD]), axis=0)
    r = (Cl[e + HOLD - 1] / entry - 1) * 100
    r = np.where(seg_low <= entry * (1 + STOP / 100), STOP, r) - FEE
    r[~np.isfinite(entry) | ~np.isfinite(Cl[e + HOLD - 1])] = np.nan
    ret[i] = r
ret = pd.DataFrame(ret, index=idx, columns=O.columns)

breadth = capit.sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)
n_el = eligible.sum(axis=1)
ev_ret_caps = ret.where(capit).mean(axis=1)               # canasta de los pares en capitulacion
ev_ret_all = ret.where(eligible).mean(axis=1)             # canasta de todos los elegibles
btc = ret['BTC'] if 'BTC' in ret else pd.Series(np.nan, index=idx)
uncond = ev_ret_all[(ev_ret_all.index >= T0) & (ev_ret_all.index <= T1)].mean()
print(f'media incondicional (canasta de todos los elegibles, cualquier vela 2022-26): {uncond:+.2f}%; BTC: {btc[(btc.index >= T0)].mean():+.2f}%')
print(f'pares elegibles por vela: mediana {n_el[n_el > 0].median():.0f}, p10 {n_el[n_el > 0].quantile(.1):.0f}, p90 {n_el[n_el > 0].quantile(.9):.0f}')


def episodes(mask):
    """Primera vela de cada grupo de senales dentro de 72h."""
    out, last = [], None
    for t in mask[mask].index:
        if last is None or (t - last) > pd.Timedelta(hours=72):
            out.append(t)
        last = t
    return out


def report(thr, verbose=True):
    sig = (breadth >= thr) & (n_el >= MIN_PAIRS) & (breadth.index >= T0) & (breadth.index <= T1)
    eps = episodes(sig)
    rows = []
    for t in eps:
        rows.append(dict(t=t, day=t.normalize(), period='IS' if t < SPLIT else 'OOS', caps=ev_ret_caps[t], all=ev_ret_all[t],
                         btc=btc[t], n=int(capit.loc[t].sum()), breadth=breadth[t]))
    ev = pd.DataFrame(rows).dropna(subset=['caps'])
    return sig, ev


def boot_excess(ev, col, n=3000):
    days = ev.day.unique(); g = {k: v for k, v in ev.groupby('day')}
    res = [pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])[col].mean() - uncond for _ in range(n)]
    return np.percentile(res, [2.5, 97.5])


print('\nSENSIBILIDAD (episodios = primera vela de cada grupo dentro de 72h)')
print(f"{'umbral':>7s} | {'velas':>5s} {'epis':>4s} {'dias':>4s} | {'IS n':>4s} {'media':>6s} {'acierto':>7s} | {'OOS n':>5s} {'media':>6s} {'acierto':>7s} | {'BTC med':>7s} {'todos med':>9s}")
for thr in (0.15, 0.20, 0.25, 0.30, 0.35):
    sig, ev = report(thr)
    a, b = ev[ev.period == 'IS'], ev[ev.period == 'OOS']
    print(f"{thr*100:6.0f}% | {int(sig.sum()):5d} {len(ev):4d} {ev.day.nunique():4d} | {len(a):4d} {a.caps.mean():+6.2f} {(a.caps > 0).mean()*100:6.0f}% | {len(b):5d} {b.caps.mean():+6.2f} {(b.caps > 0).mean()*100:6.0f}% | {ev.btc.mean():+7.2f} {ev['all'].mean():+9.2f}")

sig, ev = report(0.25)
print('\nPRIMARIO (umbral 25% fijado antes): episodios', len(ev), '| dias distintos', ev.day.nunique())
a, b = ev[ev.period == 'IS'], ev[ev.period == 'OOS']
for name, d in (('IS', a), ('OOS', b), ('UNIDO', ev)):
    print(f"  {name:5s} n={len(d):3d} dias={d.day.nunique():3d} canasta capitulados {d.caps.mean():+6.2f}% acierto {(d.caps > 0).mean()*100:3.0f}% | todos los elegibles {d['all'].mean():+6.2f}% | BTC {d.btc.mean():+6.2f}% | pares medios {d.n.mean():.1f}")
lo, hi = boot_excess(ev, 'caps')
print(f'  exceso vs media incondicional ({uncond:+.2f}%): {ev.caps.mean() - uncond:+.2f} pp  IC95 por dia [{lo:+.2f}, {hi:+.2f}]')
ok1 = a.caps.mean() >= 1.5 and b.caps.mean() >= 1.5
ok2 = lo > 0
ok3 = ev.day.nunique() >= 35 and a.day.nunique() >= 15 and b.day.nunique() >= 15
ok4 = (a.caps > 0).mean() >= 0.55 and (b.caps > 0).mean() >= 0.55
print(f'  criterios: (1) media >= +1.5% en IS y OOS: {ok1} | (2) exceso IC excluye 0: {ok2} | (3) dias >= 35 y >= 15/periodo: {ok3} | (4) acierto >= 55% en ambos: {ok4}')
print('  VEREDICTO:', 'APRUEBA' if (ok1 and ok2 and ok3 and ok4) else 'NO aprueba')
print('\nUltimos 8 episodios:')
print(ev.tail(8)[['t', 'n', 'breadth', 'caps', 'all', 'btc']].round(2).to_string(index=False))
