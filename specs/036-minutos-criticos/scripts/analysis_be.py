"""
Ideas de gestion: break-even, toma parcial en spike y fin de semana. Solo ESPRING (long) y UPTHRUST (short) por separado.
BE: usa velas de 1h de las 72h completas (datos del laboratorio). Trigger = un high/low de 1h alcanza +X% a favor; despues,
si alguna vela de 1h posterior toca el precio de entrada (P0), sale en P0 (0%, sin contar comisiones extra); si no, sale como siempre.
Es CONSERVADOR: no cuenta lo que ocurre dentro de la misma vela horaria que activa el BE.
"""
import pickle, sys
import numpy as np
import pandas as pd

rng = np.random.default_rng(3)
DATA = '/freqtrade/user_data/data/binance/futures'
ev = pickle.load(open(sys.argv[1], 'rb'))
cache = {}


def h1(pair):
    if pair not in cache:
        base = pair.replace('/USDT:USDT', '')
        cache[pair] = pd.read_feather(f'{DATA}/{base}_USDT_USDT-1h-futures.feather').set_index('date').sort_index()
    return cache[pair]


rows = []
for e in ev:
    d = -1.0 if e['is_short'] else 1.0
    P0 = e['m1'][0][1]
    fin0 = d * (e['close_rate'] / P0 - 1) * 100
    r = dict(side='upthrust' if e['is_short'] else 'spring', period='IS' if e['open_date'] < pd.Timestamp('2025-01-01', tz='UTC') else 'OOS',
             day=e['open_date'].normalize(), dow=e['open_date'].dayofweek, fin0=fin0)
    df = h1(e['pair'])
    w = df.loc[e['open_date']: e['open_date'] + pd.Timedelta(hours=72)]
    hi, lo = w['high'].values, w['low'].values
    fav = (hi / P0 - 1) * 100 if d > 0 else -(lo / P0 - 1) * 100          # mejor excursion a favor por vela
    adv = (lo / P0 - 1) * 100 if d > 0 else -(hi / P0 - 1) * 100          # peor excursion (negativa) por vela
    for X in (1.0, 2.0, 3.0):
        idx = np.where(fav >= X)[0]
        if len(idx) and idx[0] + 1 < len(w):
            back = np.where(adv[idx[0] + 1:] <= 0)[0]
            r[f'be{X}'] = 0.0 if len(back) else fin0
            r[f'be{X}_trig'] = True
            r[f'be{X}_hit'] = bool(len(back))
        else:
            r[f'be{X}'] = fin0
            r[f'be{X}_trig'] = bool(len(idx))
            r[f'be{X}_hit'] = False
    # toma parcial 50% al alcanzar +3.5% en los primeros 60 min (1m)
    m = np.array(e['m1'], dtype=float)
    fav1 = ((m[:60, 2] / P0 - 1) * 100) if d > 0 else (-(m[:60, 3] / P0 - 1) * 100)
    hit = (fav1 >= 3.5).any()
    r['tp_hit'] = bool(hit)
    r['tp'] = 0.5 * 3.5 + 0.5 * fin0 if hit else fin0
    rows.append(r)
df = pd.DataFrame(rows)


def boot_diff(a, b, days, n=1500):
    s = pd.DataFrame({'d': (a - b).values, 'day': days.values})
    g = {k: v['d'].values for k, v in s.groupby('day')}
    keys = list(g)
    out = [np.concatenate([g[keys[i]] for i in rng.choice(len(keys), len(keys), replace=True)]).mean() for _ in range(n)]
    return np.percentile(out, 2.5), np.percentile(out, 97.5)


f = lambda v: f'{v:+6.2f}'
for side in ('spring', 'upthrust'):
    print('\n' + '=' * 90 + f'\n{side.upper()}\n' + '=' * 90)
    for per in ('IS', 'OOS'):
        d = df[(df.side == side) & (df.period == per)]
        print(f'\n--- {per} n={len(d)} base (mantener 72h): media {f(d.fin0.mean())} acierto {(d.fin0 > 0).mean()*100:.0f}%')
        print('  BREAK-EVEN tras +X% a favor (72h completas, velas 1h):')
        for X in (1.0, 2.0, 3.0):
            lo, hi = boot_diff(d[f'be{X}'], d.fin0, d['day'])
            print(f'    X={X}%: se activa en {d[f"be{X}_trig"].mean()*100:3.0f}% | de esos, vuelve a P0 y sale en {d[d[f"be{X}_trig"]][f"be{X}_hit"].mean()*100:3.0f}% | media {f(d[f"be{X}"].mean())} vs {f(d.fin0.mean())} | dif {f((d[f"be{X}"]-d.fin0).mean())} [{f(lo)}, {f(hi)}] | acierto {(d[f"be{X}"] > 0).mean()*100:.0f}%')
        lo, hi = boot_diff(d.tp, d.fin0, d['day'])
        print(f'  TOMA PARCIAL 50% al +3.5% dentro de 60 min: se activa en {d.tp_hit.mean()*100:.1f}% | media {f(d.tp.mean())} vs {f(d.fin0.mean())} | dif {f((d.tp-d.fin0).mean())} [{f(lo)}, {f(hi)}]')
        wk = d.dow >= 5
        lo, hi = boot_diff(d[~wk].fin0.reset_index(drop=True).reindex(range(len(d)), fill_value=0) * 0 + 0, d.fin0 * 0, d['day']) if False else (np.nan, np.nan)
        print(f'  FIN DE SEMANA (sab-dom UTC): n={wk.sum():3d} media {f(d[wk].fin0.mean())} acierto {(d[wk].fin0 > 0).mean()*100:.0f}% | lun-vie n={(~wk).sum():3d} media {f(d[~wk].fin0.mean())} acierto {(d[~wk].fin0 > 0).mean()*100:.0f}%')
        dows = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']
        print('  por dia de la semana: ' + ' | '.join(f'{dows[k]} n={int((d.dow == k).sum()):3d} {f(d[d.dow == k].fin0.mean())}' for k in range(7)))
