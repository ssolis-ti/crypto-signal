"""Experimento de horarios (criterio en spec.md, fijado antes)."""
import json, sys, zipfile
import numpy as np
import pandas as pd
import pytz

rng = np.random.default_rng(21)
K, N_BOOT = 5, 3000
LO, HI = 100 * (0.05 / K / 2), 100 * (1 - 0.05 / K / 2)
SCL = pytz.timezone('America/Santiago')

rows = []
for period, zf in (('IS', sys.argv[1]), ('OOS', sys.argv[2])):
    z = zipfile.ZipFile(zf)
    name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    strat = next(iter(json.loads(z.read(name))['strategy'].values()))
    for t in strat['trades']:
        od = pd.Timestamp(t['open_date'])
        rows.append(dict(period=period, open=od, day=od.normalize(), ret=t['profit_ratio'] * 100))
ev = pd.DataFrame(rows)
ev['hour'] = ev.open.dt.hour
ev['dow'] = ev.open.dt.dayofweek
ev['concurrent'] = ev.groupby('open').open.transform('count')          # pares con evento en la misma vela
dim = ev.open.dt.days_in_month
ev['dom'] = ev.open.dt.day
ev['turn'] = (ev.dom <= 3) | (ev.dom >= dim - 2)
ev['weekend_pure'] = ((ev.dow == 5) & (ev.hour >= 4)) | ((ev.dow == 6) & (ev.hour <= 16))

print('eventos:', ev.groupby('period').size().to_dict(), '| con >=5 pares simultaneos:', int((ev.concurrent >= 5).sum()))
print('\nDESCRIPTIVO: media por hora UTC de cierre (IS / OOS)')
for h in (0, 4, 8, 12, 16, 20):
    a, b = ev[(ev.hour == h) & (ev.period == 'IS')], ev[(ev.hour == h) & (ev.period == 'OOS')]
    print(f"  {h:02d}:00 UTC  IS n={len(a):3d} {a.ret.mean():+5.2f}%   OOS n={len(b):3d} {b.ret.mean():+5.2f}%")
ev['sant_hour'] = ev.open.apply(lambda t: t.tz_convert(SCL).hour)
print('\nDESCRIPTIVO: hora local de Santiago a la que llega el aviso (share de eventos, ambos periodos)')
print('  ', {int(h): f"{v*100:.0f}%" for h, v in ev.sant_hour.value_counts(normalize=True).sort_index().items()})
asleep = ev.sant_hour.between(0, 6).mean() * 100
print(f'   avisos que caen entre 00:00 y 06:59 hora Santiago: {asleep:.0f}%')
cme = ev[(ev.dow == 0) & (ev.hour == 0)]
print(f"\nDESCRIPTIVO: cierre lunes 00:00 UTC (reapertura CME) n={len(cme)} media {cme.ret.mean():+.2f}%")

H = {
    'H1 funding (00/08/16) peor': (lambda d: d.hour.isin([0, 8, 16]), -1, None),
    'H2 12/16 UTC mejor': (lambda d: d.hour.isin([12, 16]), +1, None),
    'H3 cluster>=5: occidental mejor': (lambda d: d.hour.isin([12, 16, 20, 0]), +1, lambda d: d.concurrent >= 5),
    'H4 fin de semana puro peor': (lambda d: d.weekend_pure, -1, None),
    'H5 inicio/fin de mes mejor': (lambda d: d.turn, +1, None),
}


def boot(d, m):
    days = d['day'].unique()
    groups = {k: g for k, g in d.assign(_m=m).groupby('day')}
    res = []
    for _ in range(N_BOOT):
        s = pd.concat([groups[days[i]] for i in rng.integers(0, len(days), len(days))])
        a, b = s.loc[s._m, 'ret'], s.loc[~s._m, 'ret']
        if len(a) and len(b):
            res.append(a.mean() - b.mean())
    return np.percentile(res, [LO, HI])


print(f"\n{'hipotesis':34s} {'per':5s} {'n A':>5s} {'media':>7s} {'dias':>4s} | {'n B':>5s} {'media':>7s} {'dias':>4s} | dif(A-B)")
verdict = {}
for name, (cell, sign, subset) in H.items():
    res = {}
    for period in ('IS', 'OOS', 'AMBOS'):
        d = ev if period == 'AMBOS' else ev[ev.period == period]
        if subset:
            d = d[subset(d)]
        d = d.reset_index(drop=True)
        m = cell(d).astype(bool)
        a, b = d.loc[m], d.loc[~m]
        dif = a.ret.mean() - b.ret.mean()
        extra = ''
        if period == 'AMBOS':
            lo, hi = boot(d, m)
            res['ci'] = (lo, hi)
            extra = f"  IC{100-2*LO:.0f}% [{lo:+.2f}, {hi:+.2f}]"
        res[period] = (dif, a.day.nunique(), b.day.nunique())
        print(f"{name:34s} {period:5s} {len(a):5d} {a.ret.mean():+7.2f} {a.day.nunique():4d} | {len(b):5d} {b.ret.mean():+7.2f} {b.day.nunique():4d} | {dif:+5.2f}{extra}")
    lo, hi = res['ci']
    ok = (np.sign(res['IS'][0]) == sign and np.sign(res['OOS'][0]) == sign
          and (lo > 0 if sign > 0 else hi < 0) and abs(res['AMBOS'][0]) >= 0.5
          and min(res['IS'][1], res['IS'][2], res['OOS'][1], res['OOS'][2]) >= 30)
    verdict[name] = ok
print('\nVEREDICTO:', {k: ('APRUEBA' if v else 'NO aprueba') for k, v in verdict.items()})
