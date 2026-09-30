"""Spec 052: disparador intradia (velas 1h) de 'movimiento propio con volumen'. Regla fijada ANTES de mirar resultados.

Alerta long en el cierre de una vela 1h del par i si:
  z_vol  >= 3.0   (log-volumen 1h vs mediana/MAD de los ultimos 30 dias en la MISMA hora del dia)
  z_res  >= 2.5   (retorno 1h menos beta*BTC, beta rodante 14d, dividido por sigma residual rodante 14d)
  BTC z_vol < 2.5 (si BTC tambien tiene volumen extremo es mercado, no rumor propio)
  cooldown 12h por par. Espejo (z_res <= -2.5) medido aparte.
Resultado: retorno posterior desde la APERTURA de la vela siguiente (sin look-ahead) a +1h/+4h/+24h, bruto y
menos beta*BTC (idiosincratico), menos 0.1% de comision ida y vuelta 0.2% en el bruto.
IS 2022-24, OOS 2025-26. Bootstrap por dia. Base: todos los cierres 1h de los mismos pares (misma medicion).
"""
import glob
import os
import numpy as np
import pandas as pd

D = '/freqtrade/user_data/data/binance/futures'
H = [1, 4, 24]

def load(path):
    df = pd.read_feather(path)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    return df.set_index('date')[['open', 'high', 'low', 'close', 'volume']]

files = sorted(glob.glob(f'{D}/*-1h-futures.feather'))
data = {os.path.basename(f).split('_USDT')[0]: load(f) for f in files}
btc = data['BTC']
btc_ret = np.log(btc['close']).diff()

def robust_z_by_hour(v):
    lv = np.log(v.replace(0, np.nan))
    out = pd.Series(index=lv.index, dtype=float)
    for h in range(24):
        s = lv[lv.index.hour == h]
        med = s.rolling(30, min_periods=20).median().shift(1)
        mad = (s - med).abs().rolling(30, min_periods=20).median().shift(1) * 1.4826
        out[s.index] = (s - med) / mad.replace(0, np.nan)
    return out

btc_z = robust_z_by_hour(btc['volume'])
rows, base = [], []
for name, df in data.items():
    if name == 'BTC' or len(df) < 24 * 60:
        continue
    r = np.log(df['close']).diff()
    b = btc_ret.reindex(df.index)
    beta = (r.rolling(336).cov(b) / b.rolling(336).var()).shift(1)
    res = r - beta * b
    sig = res.rolling(336).std().shift(1)
    z_res = res / sig
    z_vol = robust_z_by_hour(df['volume'])
    nxt = df['open'].shift(-1)  # entrada: apertura de la vela siguiente
    fwd = {}
    for h in H:
        fwd[h] = np.log(df['close'].shift(-h) / nxt)
        fwd[f'i{h}'] = fwd[h] - beta * (np.log(btc['close'].reindex(df.index).shift(-h) / btc['open'].reindex(df.index).shift(-1)))
    frame = pd.DataFrame({'z_vol': z_vol, 'z_res': z_res, 'btc_z': btc_z.reindex(df.index), **{f'r{h}': fwd[h] for h in H},
                          **{f'i{h}': fwd[f'i{h}'] for h in H}}).dropna()
    frame['pair'] = name
    base.append(frame)
    trig = frame[(frame.z_vol >= 3.0) & (frame.btc_z < 2.5)]
    for side, cond in (('long', trig.z_res >= 2.5), ('short', trig.z_res <= -2.5)):
        sel = trig[cond]
        last = None
        for ts, row in sel.iterrows():
            if last is not None and (ts - last) < pd.Timedelta(hours=12):
                continue
            last = ts
            rows.append({'ts': ts, 'side': side, **row.to_dict()})

ev = pd.DataFrame(rows)
allh = pd.concat(base)
allh['day'] = allh.index.floor('D')
ev['day'] = pd.to_datetime(ev['ts']).dt.floor('D')
rng = np.random.default_rng(7)

def boot(x_days, n=4000):
    d = x_days.values
    if len(d) < 5:
        return (np.nan, np.nan)
    m = [rng.choice(d, len(d)).mean() for _ in range(n)]
    return np.percentile(m, [2.5, 97.5])

def summarize(e, label, sign):
    print(f'\n=== {label}: {len(e)} eventos, {e.day.nunique()} dias ===')
    for h in H:
        raw = sign * e[f'r{h}'] * 100 - 0.2
        idio = sign * e[f'i{h}'] * 100
        bl = (sign * allh[f'r{h}']).mean() * 100 - 0.2
        pd_raw = raw.groupby(e.day).mean()
        pd_idio = idio.groupby(e.day).mean()
        lo, hi = boot(pd_raw)
        print(f' +{h:>2}h  bruto neto {raw.mean():6.2f}% (IC dia {lo:5.2f}..{hi:5.2f}) base {bl:5.2f}% | idio {idio.mean():5.2f}% '
              f'| gana {100*(raw>0).mean():4.1f}% | mediana {raw.median():5.2f}%')

for per, a, b in (('IS 2022-24', '2022-01-01', '2025-01-01'), ('OOS 2025-26', '2025-01-01', '2027-01-01')):
    for side, sign in (('long', 1), ('short', -1)):
        e = ev[(ev.side == side) & (ev.ts >= pd.Timestamp(a, tz='UTC')) & (ev.ts < pd.Timestamp(b, tz='UTC'))]
        if len(e):
            summarize(e, f'{per} {side}', sign)
            days = (pd.Timestamp(b if b < '2027' else allh.index.max().strftime('%Y-%m-%d'), tz='UTC') - pd.Timestamp(a, tz='UTC')).days
            print(f' eventos/dia: {len(e)/max(days,1):.2f}  (pares={allh.pair.nunique()})')
