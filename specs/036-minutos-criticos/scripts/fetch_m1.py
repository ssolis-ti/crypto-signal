"""
Baja velas de 1 minuto (futuros USDT-M de Binance, endpoint publico, sin claves) para los ~2.700 eventos
Wyckoff del laboratorio: desde el CIERRE de la vela de 4h de confirmacion (= apertura del trade) hasta +125 min.
Incluye taker_buy_volume (klines crudas). Guarda audit_data/m1_events.pkl.
"""
import json, pickle, sys, time, zipfile
import ccxt
import pandas as pd

zips = sys.argv[1:]
ex = ccxt.binanceusdm({'enableRateLimit': True})
ex.load_markets()

events = []
for z in zips:
    zf = zipfile.ZipFile(z)
    name = [n for n in zf.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    d = json.loads(zf.read(name))
    for strat, r in d['strategy'].items():
        for t in r['trades']:
            events.append(dict(pair=t['pair'], open_date=pd.Timestamp(t['open_date']), tag=t.get('enter_tag'),
                               is_short=bool(t['is_short']), open_rate=t['open_rate'], close_rate=t['close_rate'],
                               profit_ratio=t['profit_ratio']))
print('eventos:', len(events), flush=True)

out, fails = [], 0
t0 = time.time()
for n, e in enumerate(events):
    sym = ex.market(e['pair'])['id']
    start = int(e['open_date'].timestamp() * 1000)
    rows = None
    for attempt in range(3):
        try:
            rows = ex.fapiPublicGetKlines({'symbol': sym, 'interval': '1m', 'startTime': start, 'limit': 125})
            break
        except Exception as err:
            time.sleep(1 + attempt * 2)
    if not rows or int(rows[0][0]) != start:
        fails += 1
        continue
    e['m1'] = [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[9])] for r in rows]
    out.append(e)
    if n % 200 == 0:
        print(f'{n}/{len(events)} ok={len(out)} fails={fails} {time.time()-t0:.0f}s', flush=True)

with open('/audit/m1_events.pkl', 'wb') as f:
    pickle.dump(out, f)
print('guardado', len(out), 'eventos; fallidos', fails, flush=True)
