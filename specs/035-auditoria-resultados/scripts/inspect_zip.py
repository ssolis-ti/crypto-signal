"""Inspeccion estructural de un zip de trades del laboratorio. Solo lectura."""
import zipfile, json, glob, os

ZIPS = sorted(glob.glob('audit_data/lab_trades/*.zip'))
print("total zips:", len(ZIPS))
z = zipfile.ZipFile('audit_data/lab_trades/backtest-result-2026-09-29_15-30-46.zip')  # SpringH72_SL10 OOS real
print("namelist:", z.namelist())
name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
d = json.loads(z.read(name))
print("top keys:", list(d.keys()))
strat = d['strategy']
print("strategies:", list(strat.keys()))
for k, v in strat.items():
    print("strategy", k, "keys:", list(v.keys()))
    tr = v['trades']
    print("n trades:", len(tr))
    print("sample trade keys:", list(tr[0].keys()))
    print("sample trade:", json.dumps(tr[0], indent=1, default=str)[:2000])
    break
