"""Tarea 1: verificacion del bloque Upthrust y del bloque 1-2h, recalculado desde trades."""
import zipfile, json, statistics, collections

def load(z):
    zz = zipfile.ZipFile('audit_data/lab_trades/' + z)
    n = [x for x in zz.namelist() if x.endswith('.json') and 'meta' not in x and 'config' not in x][0]
    d = json.loads(zz.read(n))
    return d['strategy'][list(d['strategy'])[0]]['trades']

def split(trades, tag):
    return [t for t in trades if t['enter_tag'] == tag]

for label, z in [('H72_IS', 'backtest-result-2026-09-29_15-13-33.zip'),
                 ('H72_OOS', 'backtest-result-2026-09-29_15-11-52.zip')]:
    tr = load(z)
    print(f"\n[{label}] n={len(tr)}")
    for tag in ('spring', 'upthrust'):
        s = split(tr, tag)
        if not s:
            continue
        wr = 100 * sum(1 for t in s if t['profit_abs'] > 0) / len(s)
        mean = 100 * sum(t['profit_ratio'] for t in s) / len(s)
        med = 100 * statistics.median([t['profit_ratio'] for t in s])
        print(f"  {tag:9} n={len(s):4} winrate={wr:5.1f}%  media={mean:+.3f}%  mediana={med:+.3f}%")
