"""Entrada secundaria (retest) vs entrada original. Criterio en spec.md, fijado antes."""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
LOOKBACK, CONFIRM, VOL_N, THRESH, HOLD, FEE = 20, 3, 20, 2.5, 18, 0.1
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
rng = np.random.default_rng(49)


def trade(o, l, c, e, stop):
    end = min(e + HOLD, len(o))
    if e >= len(o) or (e + HOLD) > len(o):
        return None
    entry = o[e]
    hit = (l[e:end] <= entry * (1 + stop / 100)).any()
    return (stop if hit else (c[end - 1] / entry - 1) * 100) - FEE, bool(hit)


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
                if j not in seen and not np.isnan(rv[i]) and rv[i] >= THRESH and j + 1 < n and dv24[j] >= 20e6 and T0 <= ix[j + 1] <= T1:
                    seen.add(j)
                    orig = trade(o, l, c, j + 1, -10.0)
                    if orig is None:
                        break
                    rec = dict(sym=name, t=ix[j + 1], orig=orig[0], orig_stop=orig[1], has_retest=False)
                    ref = l[i] * 1.015
                    for r in range(j + 1, min(j + 1 + 8, n - 1)):
                        if l[r] <= ref and not np.isnan(sma[r]) and v[r] <= 0.85 * sma[r] and c[r] > o[r]:
                            sec = trade(o, l, c, r + 1, -5.0)
                            if sec is not None:
                                rec.update(has_retest=True, sec=sec[0], sec_stop=sec[1], wait=r + 1 - (j + 1))
                            break
                    out.append(rec)
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
print(f'springs: {len(ev)} | con retest (1-8 velas despues): {int(ev.has_retest.sum())} ({ev.has_retest.mean()*100:.0f}%) | espera media {ev[ev.has_retest].wait.mean():.1f} velas')
r = ev[ev.has_retest].copy()
r['diff'] = r.sec - r.orig
print(f"\n{'':10s} | {'n':>5s} {'orig media':>10s} {'stop':>5s} | {'secundaria':>10s} {'acierto':>7s} {'stop':>5s} | {'dif pareada':>11s} {'dias':>4s}")
for per in ('IS', 'OOS', 'AMBOS'):
    x = r if per == 'AMBOS' else r[r.period == per]
    print(f"{per:10s} | {len(x):5d} {x.orig.mean():+10.2f} {x.orig_stop.mean()*100:4.0f}% | {x.sec.mean():+10.2f} {(x.sec > 0).mean()*100:6.0f}% {x.sec_stop.mean()*100:4.0f}% | {x['diff'].mean():+11.2f} {x.day.nunique():4d}")
no = ev[~ev.has_retest]
print(f"springs SIN retest (se pierden): n={len(no)}, media de su entrada original {no.orig.mean():+.2f}% (acierto {(no.orig > 0).mean()*100:.0f}%) | con retest, entrada original {r.orig.mean():+.2f}%")
days = r.day.unique(); g = {k: v for k, v in r.groupby('day')}
res = [pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])['diff'].mean() for _ in range(3000)]
lo, hi = np.percentile(res, [2.5, 97.5])
print(f"diferencia pareada unida (secundaria - original): {r['diff'].mean():+.2f} pp  IC95 por dia [{lo:+.2f}, {hi:+.2f}]")
a, b = r[r.period == 'IS'], r[r.period == 'OOS']
ok1 = a.sec.mean() >= 1.5 and b.sec.mean() >= 1.5
ok2 = a['diff'].mean() > 0 and b['diff'].mean() > 0 and lo > 0
ok3 = r.sec_stop.mean() <= 0.28
ok4 = a.day.nunique() >= 30 and b.day.nunique() >= 30
print(f'criterios: (1) media secundaria >= +1.5% en IS y OOS: {ok1} | (2) dif pareada > 0 en ambos y IC excluye 0: {ok2} | (3) stop <= 28%: {ok3} | (4) >= 30 dias por periodo: {ok4}')
print('VEREDICTO:', 'APRUEBA' if (ok1 and ok2 and ok3 and ok4) else 'NO aprueba')
