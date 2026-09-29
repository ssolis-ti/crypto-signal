"""Experimento de funding sobre los springs del laboratorio (criterio en spec.md, fijado antes)."""
import json, sys, zipfile
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
ZIPS = {'IS': sys.argv[1], 'OOS': sys.argv[2]}
rng = np.random.default_rng(11)
N_HYP, N_BOOT = 3, 3000
LO, HI = 100 * (0.05 / N_HYP / 2), 100 * (1 - 0.05 / N_HYP / 2)

cache = {}
def funding(pair):
    if pair not in cache:
        d = pd.read_feather(f"{DATA}/{pair.replace('/USDT:USDT', '')}_USDT_USDT-1h-funding_rate.feather")
        cache[pair] = d.set_index('date').sort_index()['funding_rate']
    return cache[pair]

def feats(pair, open_date):
    f = funding(pair)
    past = f[f.index <= open_date]                 # solo lo ya publicado
    if len(past) < 3 * 90:
        return None
    last = past.iloc[-1]
    hist = past.iloc[-3 * 90:]                     # 90 dias de pagos (3 por dia)
    return dict(f_last=last, f_low_q=last <= hist.quantile(0.25), f_cum24=past.iloc[-3:].sum())

rows = []
for period, zf in ZIPS.items():
    z = zipfile.ZipFile(zf)
    name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    strat = next(iter(json.loads(z.read(name))['strategy'].values()))
    for t in strat['trades']:
        od = pd.Timestamp(t['open_date'])
        try:
            fe = feats(t['pair'], od)
        except FileNotFoundError:
            fe = None
        if fe:
            rows.append(dict(period=period, day=od.normalize(), ret=t['profit_ratio'] * 100, **fe))
ev = pd.DataFrame(rows)
print('eventos con funding:', ev.groupby('period').size().to_dict())
print('funding medio al entrar (%):', (ev.groupby('period').f_last.mean() * 100).round(4).to_dict())

H = {
    'H1 funding < 0': lambda d: d.f_last < 0,
    'H2 cuartil bajo 90d': lambda d: d.f_low_q.astype(bool),
    'H3 acum. 24h < 0': lambda d: d.f_cum24 < 0,
}

def boot(d, m):
    days = d['day'].unique()
    groups = {k: g for k, g in d.assign(_m=m).groupby('day')}
    out = []
    for _ in range(N_BOOT):
        s = pd.concat([groups[days[i]] for i in rng.integers(0, len(days), len(days))])
        a, b = s.loc[s._m, 'ret'], s.loc[~s._m, 'ret']
        if len(a) and len(b):
            out.append(a.mean() - b.mean())
    return np.percentile(out, [LO, HI])

print(f"\n{'hipotesis':22s} {'periodo':6s} {'n filt':>6s} {'media':>7s} {'acierto':>7s} | {'n resto':>7s} {'media':>7s} {'acierto':>7s} | dif")
verdict = {}
for name, fn in H.items():
    difs = {}
    for period in ('IS', 'OOS', 'AMBOS'):
        d = (ev if period == 'AMBOS' else ev[ev.period == period]).reset_index(drop=True)
        m = fn(d).fillna(False).astype(bool)
        a, b = d.loc[m, 'ret'], d.loc[~m, 'ret']
        dif = a.mean() - b.mean()
        difs[period] = dif
        extra = ''
        if period == 'AMBOS':
            lo, hi = boot(d, m)
            difs['ci'] = (lo, hi)
            extra = f" IC{100-2*LO:.1f}% por dia [{lo:+.2f}, {hi:+.2f}]"
        print(f"{name:22s} {period:6s} {len(a):6d} {a.mean():+7.2f} {(a>0).mean()*100:6.0f}% | {len(b):7d} {b.mean():+7.2f} {(b>0).mean()*100:6.0f}% | {dif:+5.2f}{extra}")
    ok = difs['IS'] > 0 and difs['OOS'] > 0 and difs['ci'][0] > 0
    verdict[name] = ok
print('\nVEREDICTO (criterio pre-registrado):')
for k, v in verdict.items():
    print(f"  {k}: {'APRUEBA' if v else 'NO aprueba'}")
