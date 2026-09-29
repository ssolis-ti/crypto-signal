"""
Prueba de sesgo de supervivencia (spec 043). Mismo spring que el laboratorio (lookback 20, confirmacion 3,
volumen de ruptura >= 2.5x SMA20), entrada a la apertura de la vela siguiente, mantener 72h (18 velas de 4h),
stop -10% sobre minimos, 0.1% de comision ida y vuelta. Sin funding (simulador simple).
- Sobrevivientes: los 29 pares del laboratorio (velas de Freqtrade).
- Deslistados: perpetuos cripto que ya no cotizan (archivo publico de Binance).
Si los datos de un deslistado terminan antes de las 72h (deslistado en medio de la operacion), se cierra a
su ultimo precio conocido (liquidacion forzada).
"""
import glob, os, sys
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/exp/data_delisted'
SURVIVORS = """BTC ETH SOL XRP ADA DOGE AVAX DOT LINK LTC ATOM NEAR UNI AAVE FIL ETC TRX XLM ALGO SAND MANA AXS GALA EOS BCH ICP CRV
CHZ DYDX APE""".split()
LOOKBACK, CONFIRM, VOL_N, THRESH = 20, 3, 20, 2.5
HOLD, STOP, FEE = 18, -10.0, 0.1
T0, T1, SPLIT = pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2026-09-22', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')
rng = np.random.default_rng(7)


def spring_indices(df):
    v = df['volume'].astype(float).values
    sma = pd.Series(v).rolling(VOL_N).mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        rv = np.where(sma > 0, v / sma, np.nan)
    lows, closes = df['low'].values, df['close'].values
    support = df['low'].rolling(LOOKBACK).min().shift(1).values
    found = {}
    for i in range(len(df)):
        lvl = support[i]
        if np.isnan(lvl) or not lows[i] < lvl:
            continue
        for j in range(i + 1, min(i + 1 + CONFIRM, len(df))):
            if closes[j] > lvl:
                found[j] = rv[i]
                break
    return [j for j, r in found.items() if not np.isnan(r) and r >= THRESH]


def simulate(df, name, group):
    out = []
    o, h, l, c = df['open'].values, df['high'].values, df['low'].values, df['close'].values
    dv24 = (df['volume'] * df['close']).rolling(6).sum().values   # volumen en USD de las ultimas 24h
    idx = df.index
    n = len(df)
    for j in spring_indices(df):
        e = j + 1
        if e >= n:
            continue
        t_entry = idx[e]
        if not (T0 <= t_entry <= T1):
            continue
        entry = o[e]
        end = min(e + HOLD, n)                       # velas e .. e+HOLD-1
        truncated = (e + HOLD) > n
        if truncated and group == 'sobrevivientes':  # sigue abierta al cierre de los datos: se omite
            continue
        seg_low = l[e:end]
        if (seg_low <= entry * (1 + STOP / 100)).any():
            ret, how = STOP, 'stop'
        else:
            ret, how = (c[end - 1] / entry - 1) * 100, ('truncada' if truncated else 'tiempo')
        out.append(dict(group=group, sym=name, dvol=dv24[j], open=t_entry, day=t_entry.normalize(), ret=ret - FEE, how=how,
                        period='IS' if t_entry < SPLIT else 'OOS'))
    return out


rows = []
for b in SURVIVORS:
    p = f'{DATA}/{b}_USDT_USDT-4h-futures.feather'
    if os.path.exists(p):
        d = pd.read_feather(p).set_index('date').sort_index()
        rows += simulate(d, b, 'sobrevivientes')
n_del = 0
for p in sorted(glob.glob(f'{DELISTED}/*.pkl')):
    d = pd.read_pickle(p)
    if len(d) < LOOKBACK + HOLD + 10:
        continue
    n_del += 1
    rows += simulate(d, os.path.basename(p)[:-8], 'deslistados')
ev = pd.DataFrame(rows)
print(f'simbolos: {len(SURVIVORS)} sobrevivientes, {n_del} deslistados con datos suficientes')


def stats(d):
    return f"n={len(d):4d} media={d.ret.mean():+6.2f}% acierto={(d.ret > 0).mean()*100:3.0f}% stop={(d.how == 'stop').mean()*100:4.1f}% peor={d.ret.min():+7.2f}%"


def boot(d, fn, n=3000):
    days = d.day.unique()
    g = {k: v for k, v in d.groupby('day')}
    res = [fn(pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])) for _ in range(n)]
    return np.percentile([r for r in res if r is not None and not np.isnan(r)], [2.5, 97.5])


A, B = ev[ev.group == 'sobrevivientes'], ev[ev.group == 'deslistados']
print('\nRESULTADOS (simulador simple, sin funding; referencia del laboratorio con funding: +1.69% / 56% acierto sobre los 29)')
for name, d in (('sobrevivientes (29)', A), ('deslistados', B), ('AMBOS', ev)):
    print(f'  {name:20s} {stats(d)}')
    for per in ('IS', 'OOS'):
        print(f'      {per:3s} {stats(d[d.period == per])}')
print('  deslistados: cierres por delisting en medio de la operacion:', int((B.how == "truncada").sum()),
      '| media de esas:', f'{B[B.how == "truncada"].ret.mean():+.2f}%' if (B.how == 'truncada').any() else 'n/a')

lo, hi = boot(B, lambda s: s.ret.mean())
print(f'\nMedia de los deslistados: {B.ret.mean():+.2f}%  IC95 por dia [{lo:+.2f}, {hi:+.2f}]')
both = ev.assign(_g=(ev.group == 'deslistados'))
lo, hi = boot(both, lambda s: s.loc[s._g, 'ret'].mean() - s.loc[~s._g, 'ret'].mean() if s._g.any() and (~s._g).any() else np.nan)
print(f'Diferencia deslistados - sobrevivientes: {B.ret.mean() - A.ret.mean():+.2f} pp  IC95 por dia [{lo:+.2f}, {hi:+.2f}]')
print(f'Efecto de incluir los deslistados en el universo: media {A.ret.mean():+.2f}% -> {ev.ret.mean():+.2f}%')

print('\nPeores 12 operaciones de deslistados:')
print(B.sort_values('ret').head(12)[['sym', 'open', 'ret', 'how']].to_string(index=False))
print('\nPor año, deslistados vs sobrevivientes (media, n):')
for y in range(2022, 2027):
    a, b = A[A.open.dt.year == y], B[B.open.dt.year == y]
    print(f'  {y}: sobrevivientes {a.ret.mean():+5.2f}% (n={len(a)}) | deslistados {b.ret.mean():+5.2f}% (n={len(b)})')


print('POR LIQUIDEZ (volumen en USD de las 24h previas a la senal; el bot opera el top 30 por volumen con minimo 3M):')
bins = [(0, 3e6, '< 3M'), (3e6, 20e6, '3M-20M'), (20e6, 100e6, '20M-100M'), (100e6, 1e15, '>= 100M')]
for lo_, hi_, lab in bins:
    line = f'  {lab:9s}'
    for name, d in (('sobrevivientes', A), ('deslistados', B)):
        x = d[(d.dvol >= lo_) & (d.dvol < hi_)]
        line += f" | {name[:5]}: n={len(x):4d} media={x.ret.mean():+5.2f}% acierto={(x.ret > 0).mean()*100:3.0f}% stop={(x.how == 'stop').mean()*100:4.1f}%" if len(x) else f' | {name[:5]}: n=0'
    print(line)
liq = ev[ev.dvol >= 3e6]
print('SOLO senales con >= 3M USD/24h (lo que el bot podria ver):')
for name, d in (('sobrevivientes', liq[liq.group == 'sobrevivientes']), ('deslistados', liq[liq.group == 'deslistados']), ('AMBOS', liq)):
    print(f'  {name:15s} {stats(d)}')
    for per in ('IS', 'OOS'):
        print(f'      {per:3s} {stats(d[d.period == per])}')
lb = liq[liq.group == 'deslistados']
for per in ('IS', 'OOS'):
    both = liq[liq.period == per].assign(_g=lambda x: x.group == 'deslistados')
    lo, hi = boot(both, lambda s_: s_.loc[s_._g, 'ret'].mean() - s_.loc[~s_._g, 'ret'].mean() if s_._g.any() and (~s_._g).any() else np.nan)
    d = both.loc[both._g, 'ret'].mean() - both.loc[~both._g, 'ret'].mean()
    print(f'  deslistados - sobrevivientes ({per}, >=3M): {d:+.2f} pp  IC95 por dia [{lo:+.2f}, {hi:+.2f}]')
