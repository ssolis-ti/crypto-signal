"""
Que pasa en los minutos criticos despues del cierre de la vela de 4h de un evento Wyckoff.
Todo relativo a P0 = precio en el cierre de la vela de confirmacion (apertura de la siguiente).
Retornos ajustados por direccion (spring = long, upthrust = short). Bootstrap por DIA (clusters).
Salida final de referencia: precio de cierre del trade a las 72h (close_rate del laboratorio).
"""
import pickle, sys
import numpy as np
import pandas as pd

rng = np.random.default_rng(11)
K = [1, 3, 5, 10, 15, 30, 60, 120]
ev = pickle.load(open(sys.argv[1], 'rb'))


def period(ts):
    return 'IS' if ts < pd.Timestamp('2025-01-01', tz='UTC') else 'OOS'


rows = []
for e in ev:
    m = np.array(e['m1'], dtype=float)          # ts, o, h, l, c, v, taker_buy
    if len(m) < 120:
        continue
    d = -1.0 if e['is_short'] else 1.0
    P0 = m[0, 1]
    r = dict(pair=e['pair'], side='upthrust' if e['is_short'] else 'spring', period=period(e['open_date']),
             day=e['open_date'].normalize(), hour=e['open_date'].hour, d=d, P0=P0,
             fin0=d * (e['close_rate'] / P0 - 1) * 100)
    for k in K:
        c = m[k - 1, 4]
        r[f'ret{k}'] = d * (c / P0 - 1) * 100
        lo, hi = m[:k, 3].min(), m[:k, 2].max()
        r[f'mae{k}'] = (d * ((lo if d > 0 else hi) / P0 - 1)) * 100    # peor excursion adversa (<=0)
        r[f'mfe{k}'] = (d * ((hi if d > 0 else lo) / P0 - 1)) * 100    # mejor excursion favorable (>=0)
        r[f'fin{k}'] = d * (e['close_rate'] / c - 1) * 100              # entrar a mercado en el minuto k
    # flujo taker en los primeros 5 min
    vol5, tb5 = m[:5, 5].sum(), m[:5, 6].sum()
    r['tbr5'] = tb5 / vol5 if vol5 > 0 else np.nan
    r['vol_first5_vs_next'] = vol5 / max(m[5:30, 5].mean() * 5, 1e-9)
    # entrada limite retrocediendo
    for dd in (0.3, 0.5, 1.0, 2.0):
        lim = P0 * (1 - d * dd / 100)
        hit = (m[:120, 3] <= lim) if d > 0 else (m[:120, 2] >= lim)
        r[f'lim{dd}_fill'] = bool(hit.any())
        r[f'lim{dd}_fin'] = d * (e['close_rate'] / lim - 1) * 100 if hit.any() else np.nan
        r[f'lim{dd}_fb'] = d * (e['close_rate'] / m[119, 4] - 1) * 100   # si no llena: entrar a mercado a los 120 min
    # invalidacion temprana: salir si la excursion adversa alcanza x% dentro de los primeros W min
    for x in (0.5, 1.0, 2.0):
        adverse = -(d * ((m[:, 3] if d > 0 else m[:, 2]) / P0 - 1) * 100)   # positivo = en contra
        for W in (15, 30, 120):
            idx = np.where(adverse[:W] >= x)[0]
            r[f'inv{x}_{W}'] = -x if len(idx) else r['fin0']
            r[f'inv{x}_{W}_hit'] = bool(len(idx))
    rows.append(r)
df = pd.DataFrame(rows)
print('eventos analizados:', df.groupby(['side', 'period']).size().to_dict())


def boot(values, days, n=1500):
    """IC95 de la media con bootstrap por dia."""
    s = pd.Series(values.values, index=days.values)
    g = {k: v.values for k, v in s.groupby(level=0)}
    keys = list(g.keys())
    out = []
    for _ in range(n):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        out.append(np.concatenate([g[keys[i]] for i in pick]).mean())
    return np.percentile(out, 2.5), np.percentile(out, 97.5)


def fmt(v):
    return f'{v:+6.2f}'


for side in ('spring', 'upthrust'):
    print('\n' + '=' * 100)
    print(f'{side.upper()}  ({"long" if side == "spring" else "short"})')
    print('=' * 100)
    for per in ('IS', 'OOS'):
        d = df[(df.side == side) & (df.period == per)]
        print(f'\n--- {per}  n={len(d)}  (retorno final de referencia a 72h, entrando en P0: media {d.fin0.mean():+.2f}%, acierto {(d.fin0 > 0).mean()*100:.0f}%)')

        print('\n1) RECORRIDO del precio tras el cierre (a favor de la direccion). ret = deriva; mae/mfe = peor/mejor excursion acumulada')
        print('   min |  ret media | ret mediana | % a favor | mae mediana | mae p10 | mfe mediana')
        for k in K:
            print(f'   {k:3d} |   {fmt(d[f"ret{k}"].mean())}   |   {fmt(d[f"ret{k}"].median())}   |   {(d[f"ret{k}"] > 0).mean()*100:4.0f}%   |'
                  f'   {fmt(d[f"mae{k}"].median())}   | {fmt(d[f"mae{k}"].quantile(0.1))} |   {fmt(d[f"mfe{k}"].median())}')

        print('\n2) COSTO/BENEFICIO de entrar a mercado k minutos despues del cierre (retorno final a 72h desde ese precio; dif vs entrar en P0)')
        print('   min |  media fin | dif vs P0 [IC95 por dia]')
        for k in K:
            diff = d[f'fin{k}'] - d['fin0']
            lo, hi = boot(diff, d['day'])
            print(f'   {k:3d} |   {fmt(d[f"fin{k}"].mean())}  | {fmt(diff.mean())} [{fmt(lo)}, {fmt(hi)}]')

        print('\n3) ESPERAR CONFIRMACION: entrar a los k min SOLO si la deriva ya es a favor (ret_k > 0). Compara contra entrar siempre en P0')
        for k in (5, 15, 30, 60):
            up = d[d[f'ret{k}'] > 0]
            dn = d[d[f'ret{k}'] <= 0]
            print(f'   k={k:3d} | deriva a favor: n={len(up):4d} fin desde k={fmt(up[f"fin{k}"].mean())} (fin0 de esos={fmt(up.fin0.mean())}) | '
                  f'deriva en contra: n={len(dn):4d} fin desde k={fmt(dn[f"fin{k}"].mean())} (fin0 de esos={fmt(dn.fin0.mean())})')

        print('\n4) ORDEN LIMITE retrocediendo x% desde P0 (2h de ventana). EV por senal: si no llena = 0 (te la perdes) o entrar a mercado a los 120 min')
        print('   x%  | %llena | media si llena (limite) | esas mismas entrando en P0 | EV/senal limite (no llena=0) | EV/senal limite+mercado120 | EV/senal baseline P0')
        for dd in (0.3, 0.5, 1.0, 2.0):
            f = d[f'lim{dd}_fill']
            filled = d[f]
            ev0 = np.where(f, d[f'lim{dd}_fin'], 0.0).mean()
            ev1 = np.where(f, d[f'lim{dd}_fin'], d[f'lim{dd}_fb']).mean()
            print(f'   {dd:3.1f} | {f.mean()*100:5.0f}% |        {fmt(filled[f"lim{dd}_fin"].mean())}        |        {fmt(filled.fin0.mean())}        |'
                  f'           {fmt(ev0)}            |          {fmt(ev1)}           |      {fmt(d.fin0.mean())}')

        print('\n5) INVALIDACION TEMPRANA: salir si la excursion en contra llega a x% dentro de los primeros W min (asume salida al -x%)')
        print('   x%  ventana | % dispara | media con regla | baseline (mantener 72h) | acierto regla / base')
        for x in (0.5, 1.0, 2.0):
            for W in (15, 30, 120):
                col = f'inv{x}_{W}'
                print(f'   {x:3.1f}  {W:4d}m | {d[col+"_hit"].mean()*100:6.0f}% |     {fmt(d[col].mean())}      |        {fmt(d.fin0.mean())}          | {(d[col] > 0).mean()*100:.0f}% / {(d.fin0 > 0).mean()*100:.0f}%')

        print('\n6) FLUJO TAKER en los primeros 5 min (proporcion de volumen comprador) por terciles vs retorno final entrando a los 5 min')
        dd_ = d.dropna(subset=['tbr5']).copy()
        dd_['t'] = pd.qcut(dd_.tbr5, 3, labels=['bajo', 'medio', 'alto'])
        for t, g in dd_.groupby('t', observed=True):
            print(f'   taker-buy {t:5s} (rango {g.tbr5.min():.2f}-{g.tbr5.max():.2f}) n={len(g):4d} | fin5={fmt(g.fin5.mean())} acierto={(g.fin5 > 0).mean()*100:.0f}% | ret5={fmt(g.ret5.mean())}')

    print('\n7) HORA UTC del cierre (retorno final entrando en P0 / deriva a 15 min) — IS y OOS lado a lado')
    for h in sorted(df.hour.unique()):
        a = df[(df.side == side) & (df.period == 'IS') & (df.hour == h)]
        b = df[(df.side == side) & (df.period == 'OOS') & (df.hour == h)]
        print(f'   {h:02d}h UTC | IS n={len(a):3d} fin0={fmt(a.fin0.mean())} ret15={fmt(a.ret15.mean())} | OOS n={len(b):3d} fin0={fmt(b.fin0.mean())} ret15={fmt(b.ret15.mean())}')
