"""Tarea 2d: por que el modo real difiere del modo senal (seleccion de subset por tope de 3 posiciones)."""
import zipfile, json, statistics

def load(z):
    zz = zipfile.ZipFile('audit_data/lab_trades/' + z)
    n = [x for x in zz.namelist() if x.endswith('.json') and 'meta' not in x and 'config' not in x][0]
    d = json.loads(zz.read(n))
    return d['strategy'][list(d['strategy'])[0]]['trades']

for per, sig, sigz, realz in [
    ('IS', 'signalSL10_IS', 'backtest-result-2026-09-29_15-29-54.zip', 'backtest-result-2026-09-29_15-31-01.zip'),
    ('OOS', 'signalSL10_OOS', 'backtest-result-2026-09-29_15-29-19.zip', 'backtest-result-2026-09-29_15-30-46.zip'),
]:
    s = load(sigz); r = load(realz)
    key = lambda t: (t['pair'], t['open_timestamp'])
    sset = {key(t): t for t in s}
    rkeys = set(key(t) for t in r)
    common = [sset[k] for k in rkeys if k in sset]
    onlysig = [t for t in s if key(t) not in rkeys]
    def mean(a): return 100 * sum(t['profit_ratio'] for t in a) / len(a)
    def wr(a): return 100 * sum(1 for t in a if t['profit_abs'] > 0) / len(a)
    print(f"[{per}] signal n={len(s)} mean={mean(s):+.3f}% wr={wr(s):.1f}% | real n={len(r)} mean={mean(r):+.3f}% wr={wr(r):.1f}%")
    print(f"     real trades dentro de signal: {len(common)}/{len(r)} | mean subset={mean(common):+.3f}% wr={wr(common):.1f}%")
    print(f"     eventos que signal SI tomo y real NO: n={len(onlysig)} mean={mean(onlysig):+.3f}% wr={wr(onlysig):.1f}%")
