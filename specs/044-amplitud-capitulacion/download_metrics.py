"""
Baja las METRICAS diarias de Binance (open interest, ratio long/short de cuentas; filas cada 5 min) SOLO para los dias que
hacen falta: el dia de cada spring y el anterior (para el cambio de OI en 24h). Fuente publica: data.binance.vision.
"""
import io, os, sys, zipfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

CDN = "https://data.binance.vision"
OUT = "/exp/metrics"
ev = pd.read_csv('/exp/events_universo.csv', parse_dates=['conf'])
need = set()
for r in ev.itertuples():
    sym = (r.sym[2:] if r.sym.startswith('D_') else r.sym) + 'USDT'
    d = r.conf.tz_convert('UTC').normalize()
    for dd in (d, d - pd.Timedelta(days=1)):
        need.add((sym, dd.strftime('%Y-%m-%d')))
print('archivos diarios a bajar:', len(need), flush=True)
os.makedirs(OUT, exist_ok=True)


def fetch(item):
    sym, day = item
    path = f'{OUT}/{sym}_{day}.pkl'
    if os.path.exists(path):
        return 'ok'
    url = f'{CDN}/data/futures/um/daily/metrics/{sym}/{sym}-metrics-{day}.zip'
    for _ in range(2):
        try:
            data = urllib.request.urlopen(url, timeout=60).read()
            z = zipfile.ZipFile(io.BytesIO(data))
            df = pd.read_csv(z.open(z.namelist()[0]))
            df = df[['create_time', 'sum_open_interest_value', 'count_long_short_ratio']].copy()
            df['create_time'] = pd.to_datetime(df['create_time'], utc=True)
            df = df.drop_duplicates('create_time').set_index('create_time')
            df.to_pickle(path)
            return 'ok'
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 'nofile'
        except Exception:
            continue
    return 'error'


res = {}
with ThreadPoolExecutor(16) as ex:
    for i, r in enumerate(ex.map(fetch, sorted(need))):
        res[r] = res.get(r, 0) + 1
        if (i + 1) % 500 == 0:
            print(f'  {i + 1}/{len(need)} {res}', flush=True)
print('terminado:', res, flush=True)
