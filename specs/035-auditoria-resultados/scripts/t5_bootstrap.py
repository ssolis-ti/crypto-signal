"""
Auditoria crypto-signal - Tarea 5c (riesgo esperado con 100 USDT) y Tarea 2f (tamano vs minimos Binance).
- Bootstrap de la secuencia real de trades (modo real 1x y 3x) para distribucion de retorno, DD y racha perdedora.
- ccxt load_markets para minimos de orden del futuro USDT-M.
Salida: audit/out_t5.json
"""
import json, zipfile, os, random, statistics
from datetime import datetime, timezone
import ccxt

random.seed(7)
OUT = {}

ZIPS = {
    'real_1x_IS': 'backtest-result-2026-09-29_15-31-01.zip',
    'real_1x_OOS': 'backtest-result-2026-09-29_15-30-46.zip',
    'real_3x_IS': 'backtest-result-2026-09-29_15-31-28.zip',
    'real_3x_OOS': 'backtest-result-2026-09-29_15-31-18.zip',
}


def trades_of(z):
    zz = zipfile.ZipFile(os.path.join('audit_data/lab_trades', z))
    n = [x for x in zz.namelist() if x.endswith('.json') and 'meta' not in x and 'config' not in x][0]
    d = json.loads(zz.read(n))
    return d['strategy'][list(d['strategy'])[0]]['trades']


def path_metrics(profits, start=100.0):
    eq = start; peak = start; mdd = 0.0
    streak = 0; worst = 0
    for p in profits:
        eq += p
        peak = max(peak, eq)
        if peak > 0:
            mdd = max(mdd, (peak - eq) / peak)
        if p < 0:
            streak += 1; worst = max(worst, streak)
        else:
            streak = 0
    return eq - start, mdd * 100, worst


def boot(profits, iters=5000):
    n = len(profits)
    rets, dds, streaks = [], [], []
    for _ in range(iters):
        s = [profits[random.randrange(n)] for _ in range(n)]
        random.shuffle(s)
        r, dd, st = path_metrics(s)
        rets.append(r); dds.append(dd); streaks.append(st)
    def pct(a, q):
        a = sorted(a); return a[int(q * (len(a) - 1))]
    return {
        'n': n, 'iters': iters,
        'ret_p5': round(pct(rets, .05), 1), 'ret_p50': round(pct(rets, .50), 1), 'ret_p95': round(pct(rets, .95), 1),
        'ret_min': round(min(rets), 1),
        'dd_p50': round(pct(dds, .50), 1), 'dd_p95': round(pct(dds, .95), 1), 'dd_max': round(max(dds), 1),
        'streak_p50': pct(streaks, .50), 'streak_p95': pct(streaks, .95), 'streak_max': max(streaks),
        'p_ret_negativo': round(100 * sum(1 for r in rets if r < 0) / iters, 1),
    }


boots = {}
for label, z in ZIPS.items():
    tr = trades_of(z)
    profits = [t['profit_abs'] for t in tr]
    obs = path_metrics(profits)
    b = boot(profits)
    b['observado_retorno_abs'] = round(obs[0], 1)
    b['observado_dd_pct'] = round(obs[1], 1)
    b['observado_racha_perdedora'] = obs[2]
    b['pct_perdedores'] = round(100 * sum(1 for p in profits if p < 0) / len(profits), 1)
    boots[label] = b
    print(f"[{label}] n={b['n']} perdedores={b['pct_perdedores']}%")
    print(f"   observado: ret={b['observado_retorno_abs']} DD={b['observado_dd_pct']}% racha={b['observado_racha_perdedora']}")
    print(f"   bootstrap: ret p5/p50/p95={b['ret_p5']}/{b['ret_p50']}/{b['ret_p95']} min={b['ret_min']} P(neg)={b['p_ret_negativo']}%")
    print(f"              DD p50/p95/max={b['dd_p50']}/{b['dd_p95']}/{b['dd_max']}%  racha p50/p95/max={b['streak_p50']}/{b['streak_p95']}/{b['streak_max']}")
OUT['bootstrap'] = boots

# ---- Tarea 2f: minimos Binance ----
cfg = json.load(open('audit_data/strategies/config_wyckoff_lab.json', encoding='utf-8'))
wl = cfg['exchange']['pair_whitelist']
ex = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
mk = ex.load_markets()
rows = []
for p in wl:
    m = mk.get(p)
    if not m:
        rows.append({'pair': p, 'error': 'market no existe'})
        continue
    try:
        px = ex.fetch_ticker(p)['last']
    except Exception as e:
        px = None
    amin = (m.get('limits', {}).get('amount', {}) or {}).get('min')
    cmin = (m.get('limits', {}).get('cost', {}) or {}).get('min')
    cs = m.get('contractSize')
    for lev in (1, 3):
        notional = 30.0 * lev
        amt = notional / px if px else None
        rows.append({
            'pair': p, 'price': px, 'leverage': lev, 'notional_usdt': notional,
            'amount': round(amt, 8) if amt else None,
            'min_amount': amin, 'min_cost_usdt': cmin, 'contract_size': cs,
            'cumple_min_amount': (amt is None or amin is None or amt >= amin),
            'cumple_min_cost': (cmin is None or notional >= cmin),
        })
OUT['minimos_binance'] = rows
print("\n[2f] minimos Binance (muestra):")
for r in rows[:6] + rows[-4:]:
    print("  ", json.dumps(r, ensure_ascii=False))
fails = [r for r in rows if ('error' in r) or (not r.get('cumple_min_amount', True)) or (not r.get('cumple_min_cost', True))]
print("  pares/lev con problema de minimo:", len(fails), [ (r['pair'], r.get('leverage'), r.get('error')) for r in fails])
mincosts = sorted(set(r['min_cost_usdt'] for r in rows if r.get('min_cost_usdt') is not None))
print("  min_cost_usdt distintos:", mincosts)

json.dump(OUT, open('audit/out_t5.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False, default=str)
print("\n-> audit/out_t5.json escrito")
