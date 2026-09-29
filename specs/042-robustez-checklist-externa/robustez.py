"""Robustez del spring 72h/stop -10% (criterios en spec.md, fijados antes)."""
import json, sys, zipfile
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
rows = []
for period, zf in (('IS', sys.argv[1]), ('OOS', sys.argv[2])):
    z = zipfile.ZipFile(zf)
    name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    strat = next(iter(json.loads(z.read(name))['strategy'].values()))
    for t in strat['trades']:
        rows.append(dict(open=pd.Timestamp(t['open_date']), close=pd.Timestamp(t['close_date']),
                         ret=t['profit_ratio'] * 100))
ev = pd.DataFrame(rows).sort_values('open').reset_index(drop=True)
ev['year'] = ev.open.dt.year
ev['stop'] = ev.ret <= -9.8

print('1) ROBUSTEZ POR AÑO (todas las senales, 1x, neto)')
by = ev.groupby('year').agg(n=('ret', 'size'), media=('ret', 'mean'), acierto=('ret', lambda s: (s > 0).mean() * 100),
                            stop=('stop', lambda s: s.mean() * 100))
print(by.round(2).to_string())
pos_years = int((by.media > 0).sum())
print(f'   años con media > 0: {pos_years} de {len(by)} -> {"CUMPLE" if pos_years >= 4 else "NO CUMPLE"} (criterio: >= 4 de 5)')

print('\n2) ESTRES DE FRICCION (media por trade; base sin estres = %+.2f%%)' % ev.ret.mean())
print(f"   {'costo extra/trade':>18s} | " + ' | '.join(f'peor stop +{s}pp' for s in (0, 1, 2, 3)))
for c in (0.0, 0.1, 0.3, 0.5):
    cells = []
    for s in (0, 1, 2, 3):
        r = ev.ret - c - np.where(ev.stop, s, 0.0)
        cells.append(f'{r.mean():+6.2f}%  win {(r > 0).mean()*100:3.0f}%')
    print(f'   {"+%.1f pp" % c:>18s} | ' + ' | '.join(cells))
worst = (ev.ret - 0.3 - np.where(ev.stop, 2, 0.0)).mean()
print(f'   con +0.3 pp de costo y +2 pp en stops: media {worst:+.2f}% -> {"CUMPLE" if worst > 0 else "NO CUMPLE"}')

print('\n3) MONTE CARLO: cartera con tope de 3 posiciones simultaneas (orden cronologico real)')
taken, open_until = [], []
for _, t in ev.iterrows():
    open_until = [c for c in open_until if c > t.open]
    if len(open_until) < 3:
        taken.append(t.ret)
        open_until.append(t.close)
taken = np.array(taken)
years = (ev.open.max() - ev.open.min()).days / 365.25
per_year = len(taken) / years
print(f'   trades tomados con tope 3: {len(taken)} en {years:.1f} años (~{per_year:.0f}/año), media {taken.mean():+.2f}%, acierto {(taken>0).mean()*100:.0f}%')
N = int(per_year)
print(f'   1 año simulado = {N} trades, 5000 remuestreos; f = % del capital por posicion (sin asumir capital)')
print(f"   {'f':>5s} | {'DD max p50':>10s} {'DD max p95':>10s} | {'retorno anual p5':>16s} {'p50':>7s} | {'P(anio negativo)':>16s} | racha perdedora p50/p95")
for f in (0.05, 0.10, 0.20, 0.33):
    dds, rets, streaks = [], [], []
    for _ in range(5000):
        r = rng.choice(taken, N, replace=True) / 100 * f
        eq = np.cumprod(1 + r)
        dds.append((1 - eq / np.maximum.accumulate(eq)).max() * 100)
        rets.append((eq[-1] - 1) * 100)
        loss = (r < 0).astype(int); run = best = 0
        for x in loss:
            run = run + 1 if x else 0
            best = max(best, run)
        streaks.append(best)
    print(f'   {f*100:4.0f}% | {np.percentile(dds,50):9.1f}% {np.percentile(dds,95):9.1f}% | '
          f'{np.percentile(rets,5):+15.1f}% {np.percentile(rets,50):+6.1f}% | {np.mean(np.array(rets)<0)*100:15.0f}% | '
          f'{np.percentile(streaks,50):.0f} / {np.percentile(streaks,95):.0f}')
print('   (con remuestreo independiente; los trades reales estan agrupados en dias de capitulacion, asi que el riesgo real puede ser MAYOR)')
