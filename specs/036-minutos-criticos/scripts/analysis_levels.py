"""
Parte 2: ideas que necesitan el NIVEL barrido (extremo de la vela de ruptura) y BTC en los primeros minutos.
  I07 segundo barrido | I02 invalidacion por perder el extremo | I03 orden limite en el soporte/resistencia | I05 BTC 15 min.
Corre en la imagen de Freqtrade (pyarrow + datos 4h + ccxt). Uso: analysis_levels.py m1_events.pkl
"""
import pickle, sys, time
import numpy as np
import pandas as pd
import ccxt

rng = np.random.default_rng(5)
DATA = '/freqtrade/user_data/data/binance/futures'
ev = pickle.load(open(sys.argv[1], 'rb'))
cache4 = {}


def bars4(pair):
    if pair not in cache4:
        base = pair.replace('/USDT:USDT', '')
        cache4[pair] = pd.read_feather(f'{DATA}/{base}_USDT_USDT-4h-futures.feather').set_index('date').sort_index()
    return cache4[pair]


def level_and_extreme(pair, open_date, is_short):
    df = bars4(pair)
    conf = open_date - pd.Timedelta(hours=4)
    if conf not in df.index:
        return None
    k = df.index.get_loc(conf)
    if k < 30:
        return None
    lows, highs, closes = df['low'].values, df['high'].values, df['close'].values
    if not is_short:
        levels = df['low'].rolling(20).min().shift(1).values
    else:
        levels = df['high'].rolling(20).max().shift(1).values
    out = None
    for i0 in range(k - 3, k):
        lv = levels[i0]
        if np.isnan(lv):
            continue
        broke = (highs[i0] > lv) if is_short else (lows[i0] < lv)
        if not broke:
            continue
        first = next((j for j in range(i0 + 1, min(i0 + 4, len(df))) if ((closes[j] < lv) if is_short else (closes[j] > lv))), None)
        if first == k:
            out = (lv, highs[i0] if is_short else lows[i0])
    return out


# BTC 1m para cada vela distinta (una sola consulta por vela)
ex = ccxt.binanceusdm({'enableRateLimit': True})
btc = {}
dates = sorted({e['open_date'] for e in ev})
print('velas distintas:', len(dates), flush=True)
for n, dte in enumerate(dates):
    try:
        rows = ex.fapiPublicGetKlines({'symbol': 'BTCUSDT', 'interval': '1m', 'startTime': int(dte.timestamp() * 1000), 'limit': 20})
        if rows and int(rows[0][0]) == int(dte.timestamp() * 1000) and len(rows) >= 15:
            btc[dte] = float(rows[14][4]) / float(rows[0][1]) - 1
    except Exception:
        pass
print('BTC 1m ok:', len(btc), flush=True)

rows = []
for e in ev:
    m = np.array(e['m1'], dtype=float)
    if len(m) < 120:
        continue
    lv = level_and_extreme(e['pair'], e['open_date'], e['is_short'])
    if lv is None:
        continue
    level, extreme = lv
    d = -1.0 if e['is_short'] else 1.0
    P0 = m[0, 1]
    fin0 = d * (e['close_rate'] / P0 - 1) * 100
    lows, highs = m[:120, 3], m[:120, 2]
    r = dict(side='upthrust' if e['is_short'] else 'spring', period='IS' if e['open_date'] < pd.Timestamp('2025-01-01', tz='UTC') else 'OOS',
             day=e['open_date'].normalize(), pair=e['pair'], d=d, fin0=fin0,
             dist_extreme=abs(P0 / extreme - 1) * 100, dist_level=abs(P0 / level - 1) * 100,
             btc15=btc.get(e['open_date'], np.nan) * 100)
    for W in (15, 30, 60, 120):
        w_lows, w_highs = lows[:W], highs[:W]
        lost = (w_lows.min() < extreme) if d > 0 else (w_highs.max() > extreme)
        touched = (w_lows.min() <= extreme * 1.001) if d > 0 else (w_highs.max() >= extreme * 0.999)
        r[f'lost{W}'] = bool(lost)
        r[f'touch{W}'] = bool(touched)
        r[f'inv_extreme{W}'] = (d * (extreme / P0 - 1) * 100) if lost else fin0   # salir justo en el extremo
    filled = (lows.min() <= level) if d > 0 else (highs.max() >= level)
    r['lvl_fill'] = bool(filled)
    r['lvl_fin'] = d * (e['close_rate'] / level - 1) * 100 if filled else np.nan
    c15 = m[14, 4]
    r['ret15'] = d * (c15 / P0 - 1) * 100
    r['fin15'] = d * (e['close_rate'] / c15 - 1) * 100
    rows.append(r)
df = pd.DataFrame(rows)
print('eventos con nivel:', df.groupby(['side', 'period']).size().to_dict(), flush=True)


def boot(values, days, n=1500):
    s = pd.Series(values.values, index=days.values)
    g = {k: v.values for k, v in s.groupby(level=0)}
    keys = list(g.keys())
    out = [np.concatenate([g[keys[i]] for i in rng.choice(len(keys), len(keys), replace=True)]).mean() for _ in range(n)]
    return np.percentile(out, 2.5), np.percentile(out, 97.5)


f = lambda v: f'{v:+6.2f}'
for side in ('spring', 'upthrust'):
    print('\n' + '=' * 96 + f'\n{side.upper()}\n' + '=' * 96)
    for per in ('IS', 'OOS'):
        d = df[(df.side == side) & (df.period == per)]
        print(f'\n--- {per} n={len(d)} | referencia (entrar en P0 y mantener 72h): media {f(d.fin0.mean())}% acierto {(d.fin0 > 0).mean()*100:.0f}%')
        print(f'   distancia P0 -> extremo barrido: mediana {d.dist_extreme.median():.2f}% (p25 {d.dist_extreme.quantile(.25):.2f}%, p75 {d.dist_extreme.quantile(.75):.2f}%) | P0 -> nivel: mediana {d.dist_level.median():.2f}%')

        print('\n I07) SEGUNDO BARRIDO: el precio vuelve a tocar / pierde el extremo barrido dentro de W minutos')
        print('   W min | vuelve a tocar | pierde el extremo | media final si LO PIERDE | media final si NO | acierto pierde/no')
        for W in (15, 30, 60, 120):
            l, n_ = d[d[f'lost{W}']], d[~d[f'lost{W}']]
            print(f'   {W:4d}  |     {d[f"touch{W}"].mean()*100:4.0f}%     |       {d[f"lost{W}"].mean()*100:4.0f}%       |   {f(l.fin0.mean())} (n={len(l):3d})    |   {f(n_.fin0.mean())} (n={len(n_):3d})   | {((l.fin0 > 0).mean()*100 if len(l) else float("nan")):.0f}% / {(n_.fin0 > 0).mean()*100:.0f}%')

        print('\n I02) INVALIDACION: salir en el extremo barrido si lo pierde en W min (sale al precio del extremo) vs mantener 72h')
        for W in (15, 30, 60, 120):
            diff = d[f'inv_extreme{W}'] - d.fin0
            lo, hi = boot(diff, d['day'])
            print(f'   W={W:3d} | media con regla {f(d[f"inv_extreme{W}"].mean())} vs {f(d.fin0.mean())} | dif {f(diff.mean())} [{f(lo)}, {f(hi)}] | acierto {(d[f"inv_extreme{W}"] > 0).mean()*100:.0f}% vs {(d.fin0 > 0).mean()*100:.0f}%')

        print('\n I03) ORDEN LIMITE en el nivel de soporte/resistencia barrido (2 h de ventana)')
        fl = d[d.lvl_fill]
        ev_lim = np.where(d.lvl_fill, d.lvl_fin, 0.0).mean()
        print(f'   se llena {d.lvl_fill.mean()*100:.0f}% | media si llena {f(fl.lvl_fin.mean())} vs esas mismas entrando en P0 {f(fl.fin0.mean())} | EV/senal (no llena = 0) {f(ev_lim)} vs baseline {f(d.fin0.mean())}')

        print('\n I05) BTC en los primeros 15 min (con entrada a los 15 min: fin15)')
        dd = d.dropna(subset=['btc15'])
        # a favor de la direccion = BTC sube para un long, baja para un short
        fav = (dd.btc15 * dd.d) > 0
        for name, g in (('BTC a favor', dd[fav]), ('BTC en contra', dd[~fav])):
            print(f'   {name:14s} n={len(g):4d} | fin15 {f(g.fin15.mean())} acierto {(g.fin15 > 0).mean()*100:.0f}% | fin0 {f(g.fin0.mean())}')
