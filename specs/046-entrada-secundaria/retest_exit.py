"""Salir en el retest (hipotesis pre-registrada en spec.md). Reusa la deteccion de retest.py."""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
LOOKBACK, CONFIRM, VOL_N, THRESH, HOLD, FEE, STOP = 20, 3, 20, 2.5, 18, 0.1, -10.0
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
rng = np.random.default_rng(50)


def events(df, name):
    v = df['volume'].astype(float).values
    sma = pd.Series(v).rolling(VOL_N).mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        rv = np.where(sma > 0, v / sma, np.nan)
    o, l, c = df['open'].values, df['low'].values, df['close'].values
    dv24 = (df['volume'] * df['close']).rolling(6).sum().values
    support = df['low'].rolling(LOOKBACK).min().shift(1).values
    ix, n, out, seen = df.index, len(df), [], set()
    for i in range(n):
        lvl = support[i]
        if np.isnan(lvl) or not l[i] < lvl:
            continue
        for j in range(i + 1, min(i + 1 + CONFIRM, n)):
            if c[j] > lvl:
                e = j + 1
                if j not in seen and not np.isnan(rv[i]) and rv[i] >= THRESH and e + HOLD <= n and dv24[j] >= 20e6 and T0 <= ix[e] <= T1:
                    seen.add(j)
                    entry = o[e]
                    stop_px = entry * (1 + STOP / 100)
                    # retest: primera vela r (1..8 despues de la confirmacion) con las condiciones de la spec
                    r_idx = None
                    for r in range(j + 1, min(j + 1 + 8, n - 1)):
                        if l[r] <= l[i] * 1.015 and not np.isnan(sma[r]) and v[r] <= 0.85 * sma[r] and c[r] > o[r]:
                            r_idx = r
                            break
                    hold_hit = (l[e:e + HOLD] <= stop_px).any()
                    hold_ret = (STOP if hold_hit else (c[e + HOLD - 1] / entry - 1) * 100) - FEE
                    rule_ret = hold_ret
                    if r_idx is not None and r_idx >= e:
                        hit_before = (l[e:r_idx + 1] <= stop_px).any()
                        rule_ret = (STOP if hit_before else (c[r_idx] / entry - 1) * 100) - FEE
                    out.append(dict(sym=name, t=ix[e], hold=hold_ret, rule=rule_ret, retest=r_idx is not None))
                break
    return out


rows = []
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    rows += events(pd.read_feather(p).set_index('date').sort_index(), os.path.basename(p).split('_USDT_USDT')[0])
for p in glob.glob(f'{DELISTED}/*.pkl'):
    d = pd.read_pickle(p)
    if len(d) > LOOKBACK + HOLD + 10:
        rows += events(d, 'D_' + os.path.basename(p)[:-8])
ev = pd.DataFrame(rows)
ev['day'] = ev.t.dt.normalize()
ev['period'] = np.where(ev.t < SPLIT, 'IS', 'OOS')
ev['diff'] = ev.rule - ev.hold
print(f'springs: {len(ev)} | con retest: {int(ev.retest.sum())} ({ev.retest.mean()*100:.0f}%)')
print(f"{'':6s} | {'n':>5s} {'mantener 72h':>12s} {'acierto':>7s} | {'salir en retest':>15s} {'acierto':>7s} | {'mejora':>7s}")
for per in ('IS', 'OOS', 'AMBOS'):
    x = ev if per == 'AMBOS' else ev[ev.period == per]
    print(f"{per:6s} | {len(x):5d} {x.hold.mean():+12.2f} {(x.hold > 0).mean()*100:6.0f}% | {x.rule.mean():+15.2f} {(x.rule > 0).mean()*100:6.0f}% | {x['diff'].mean():+7.2f}")
rt = ev[ev.retest]
print(f"solo los {len(rt)} con retest: mantener {rt.hold.mean():+.2f}% (acierto {(rt.hold > 0).mean()*100:.0f}%) -> salir en el retest {rt.rule.mean():+.2f}% (acierto {(rt.rule > 0).mean()*100:.0f}%)")
days = ev.day.unique(); g = {k: v for k, v in ev.groupby('day')}
res = [pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])['diff'].mean() for _ in range(3000)]
lo, hi = np.percentile(res, [2.5, 97.5])
a, b = ev[ev.period == 'IS'], ev[ev.period == 'OOS']
print(f"mejora general unida: {ev['diff'].mean():+.2f} pp  IC95 por dia [{lo:+.2f}, {hi:+.2f}]")
ok = a['diff'].mean() >= 0.5 and b['diff'].mean() >= 0.5 and lo > 0 and (ev.rule > 0).mean() >= (ev.hold > 0).mean()
print('VEREDICTO (criterio pre-registrado):', 'APRUEBA' if ok else 'NO aprueba')
