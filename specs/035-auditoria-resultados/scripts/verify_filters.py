"""
Verificacion independiente de los filtros propuestos por la auditoria de estrategia (AUDIT_MEJORAS).
Une los trades de WyckoffLab_SpringH72 (IS/OOS, modo senal) con caracteristicas recalculadas desde
los datos de futuros del laboratorio, y mide cada filtro con un bootstrap por DIA (los eventos se
agrupan en velas compartidas por muchos pares: no son independientes).
"""
import glob, json, sys, zipfile
import numpy as np
import pandas as pd
import talib

DATA = '/freqtrade/user_data/data/binance/futures'
ZIPS = {'IS': sys.argv[1], 'OOS': sys.argv[2]}
rng = np.random.default_rng(7)


def load(pair, tf='4h'):
    base = pair.replace('/USDT:USDT', '')
    df = pd.read_feather(f'{DATA}/{base}_USDT_USDT-{tf}-futures.feather')
    return df.set_index('date').sort_index()


cache = {}
def data(pair):
    if pair not in cache:
        cache[pair] = load(pair)
    return cache[pair]


btc_d = load('BTC/USDT:USDT', '1d')
btc_d['ema200'] = talib.EMA(btc_d['close'].values, 200)


def features(pair, open_date):
    df = data(pair)
    conf_ts = open_date - pd.Timedelta(hours=4)
    if conf_ts not in df.index:
        return None
    k = df.index.get_loc(conf_ts)
    if k < 30:
        return None
    lows, closes = df['low'].values, df['close'].values
    support = df['low'].rolling(20).min().shift(1).values
    depth = np.nan
    for i in range(k - 3, k):                     # ultima vela de ruptura que confirma en k (igual que la deteccion)
        if not np.isnan(support[i]) and lows[i] < support[i]:
            if any(closes[j] > support[i] for j in range(i + 1, k + 1) if j == k):
                depth = (support[i] - lows[i]) / support[i] * 100
    chg24 = (closes[k] / closes[k - 6] - 1) * 100
    day = conf_ts.normalize() - pd.Timedelta(days=1)   # ultimo dia CERRADO antes de la confirmacion
    btc_bull = np.nan
    if day in btc_d.index and not np.isnan(btc_d.loc[day, 'ema200']):
        btc_bull = float(btc_d.loc[day, 'close'] > btc_d.loc[day, 'ema200'])
    return depth, chg24, btc_bull


rows = []
for period, zf in ZIPS.items():
    z = zipfile.ZipFile(zf)
    name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    for t in json.loads(z.read(name))['strategy']['WyckoffLab_SpringH72']['trades']:
        od = pd.Timestamp(t['open_date'])
        f = features(t['pair'], od)
        if f is None:
            continue
        rows.append(dict(period=period, pair=t['pair'], day=od.normalize(), ret=t['profit_ratio'] * 100,
                         depth=f[0], chg24=f[1], btc_bull=f[2]))
ev = pd.DataFrame(rows)
print('eventos con features:', ev.groupby('period').size().to_dict(), '| depth NaN:', int(ev.depth.isna().sum()))

CUTS = {
    'baseline': lambda d: pd.Series(True, index=d.index),
    'sweep >= 1.0%': lambda d: d.depth >= 1.0,
    'sweep >= 1.5%': lambda d: d.depth >= 1.5,
    'caida24h <= -8%': lambda d: d.chg24 <= -8,
    'caida24h <= -5%': lambda d: d.chg24 <= -5,
    'BTC > EMA200': lambda d: d.btc_bull == 1.0,
}


def boot_diff(d, mask, n=2000):
    """Diferencia de medias (filtrado - excluido) con bootstrap por dia. Devuelve (dif, ic95_lo, ic95_hi)."""
    days = d['day'].unique()
    groups = {k: g for k, g in d.groupby('day')}
    diffs = []
    for _ in range(n):
        pick = rng.choice(len(days), size=len(days), replace=True)
        s = pd.concat([groups[days[i]] for i in pick])
        m = mask.loc[s.index] if s.index.is_unique else None
        if m is None:
            s = s.reset_index(drop=True)
            m = s['_m']
        a, b = s.loc[m, 'ret'], s.loc[~m, 'ret']
        if len(a) and len(b):
            diffs.append(a.mean() - b.mean())
    a, b = d.loc[mask, 'ret'], d.loc[~mask, 'ret']
    return a.mean() - b.mean(), np.percentile(diffs, 2.5), np.percentile(diffs, 97.5)


print(f"\n{'filtro':18s} {'periodo':4s} {'n filtr':>7s} {'media':>7s} {'acierto':>7s} | {'n resto':>7s} {'media':>7s} | dif medias [IC95 por dia]")
for name, fn in CUTS.items():
    for period in ('IS', 'OOS'):
        d = ev[ev.period == period].copy().reset_index(drop=True)
        d = d[~d.depth.isna()] if 'sweep' in name else d
        d = d[~d.btc_bull.isna()] if 'BTC' in name else d
        d = d.reset_index(drop=True)
        m = fn(d).fillna(False)
        d['_m'] = m
        a, b = d.loc[m, 'ret'], d.loc[~m, 'ret']
        if name == 'baseline':
            print(f"{name:18s} {period:4s} {len(a):7d} {a.mean():+7.2f} {(a>0).mean()*100:6.0f}% |")
            continue
        dif, lo, hi = boot_diff(d, m)
        print(f"{name:18s} {period:4s} {len(a):7d} {a.mean():+7.2f} {(a>0).mean()*100:6.0f}% | {len(b):7d} {b.mean():+7.2f} | {dif:+5.2f} [{lo:+5.2f}, {hi:+5.2f}]")
