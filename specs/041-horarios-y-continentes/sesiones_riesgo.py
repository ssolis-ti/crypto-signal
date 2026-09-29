"""
Seguimiento de spec 041 (pregunta del operador: dia/noche por continente). Bloques definidos ANTES de mirar:
por hora UTC de ENTRADA (= cierre de la vela de confirmacion):
  Asia/madrugada UTC: 00:00 y 04:00 | Europa: 08:00 y 12:00 | EEUU/tarde: 16:00 y 20:00
Metricas: cantidad de senales (frecuencia), acierto, tasa de stop -10%, media. Bootstrap por DIA.
Es exploratorio (no cuenta como filtro): sirve para saber si la sesion cambia el RIESGO o la FRECUENCIA.
"""
import json, sys, zipfile
import numpy as np
import pandas as pd

rng = np.random.default_rng(33)
rows = []
for period, zf in (('IS', sys.argv[1]), ('OOS', sys.argv[2])):
    z = zipfile.ZipFile(zf)
    name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    strat = next(iter(json.loads(z.read(name))['strategy'].values()))
    for t in strat['trades']:
        od = pd.Timestamp(t['open_date'])
        rows.append(dict(period=period, open=od, day=od.normalize(), ret=t['profit_ratio'] * 100,
                         hour=od.hour, days_span=(t['close_date'] and 1)))
ev = pd.DataFrame(rows)
block = {0: 'Asia', 4: 'Asia', 8: 'Europa', 12: 'Europa', 16: 'EEUU', 20: 'EEUU'}
ev['block'] = ev.hour.map(block)
ev['stop'] = ev.ret <= -9.8
ev['win'] = ev.ret > 0
print('FRECUENCIA: senales por hora UTC de cierre (IS + OOS) y por bloque')
print('  ', ev.hour.value_counts().sort_index().to_dict())
print('  ', ev.block.value_counts().to_dict(), '| dias distintos con senal por bloque:', ev.groupby('block').day.nunique().to_dict())
n_days = ev.day.nunique()
print(f'  (dias totales con alguna senal: {n_days}; si fuera uniforme cada hora tendria ~{len(ev)/6:.0f})')

print('\nRIESGO Y RESULTADO por bloque (IS / OOS)')
for b in ('Asia', 'Europa', 'EEUU'):
    line = f'  {b:7s}'
    for per in ('IS', 'OOS'):
        d = ev[(ev.block == b) & (ev.period == per)]
        line += f" | {per} n={len(d):3d} acierto={d.win.mean()*100:3.0f}% stop={d.stop.mean()*100:4.1f}% media={d.ret.mean():+5.2f}%"
    print(line)


def boot(d, col, mask, n=3000):
    days = d.day.unique(); g = {k: v for k, v in d.assign(_m=mask).groupby('day')}
    out = []
    for _ in range(n):
        s = pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])
        a, b = s.loc[s._m, col], s.loc[~s._m, col]
        if len(a) and len(b):
            out.append((a.mean() - b.mean()) * 100)
    return np.percentile(out, [2.5, 97.5])


print('\nDIFERENCIA de cada bloque vs el resto (puntos porcentuales, IC95 por dia, IS+OOS unidos)')
for b in ('Asia', 'Europa', 'EEUU'):
    m = ev.block == b
    for col, label in (('win', 'acierto'), ('stop', 'tasa de stop')):
        lo, hi = boot(ev, col, m)
        dif = (ev.loc[m, col].mean() - ev.loc[~m, col].mean()) * 100
        print(f'  {b:7s} {label:13s} {dif:+5.1f} pp [{lo:+5.1f}, {hi:+5.1f}]')

print('\nPODER: con estos n, que diferencia de media se puede detectar (IC95 por dia de "Asia vs resto")')
m = ev.block == 'Asia'
lo, hi = boot(ev, 'ret', m)
lo, hi = lo / 100, hi / 100  # boot() devuelve x100 (pensado para tasas); el retorno ya esta en pp
print(f'  Asia vs resto en retorno medio: dif {ev.loc[m,"ret"].mean()-ev.loc[~m,"ret"].mean():+.2f} pp, IC95 [{lo:+.2f}, {hi:+.2f}] -> ancho ~{hi-lo:.1f} pp')
