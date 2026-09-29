"""
Auditoria crypto-signal - Tareas 1 y 2.
Recalcula TODAS las cifras desde los trades crudos de lab_trades/*.zip (no copia el log).
Salida legible + audit/out_t12.json
"""
import zipfile, json, glob, os, statistics, collections

BASE = 'audit_data/lab_trades'
OUT = {}

DATASETS = {
    # etiqueta : archivo zip
    'spring_signal_IS':      'backtest-result-2026-09-29_15-29-59.zip',
    'spring_signal_OOS':     'backtest-result-2026-09-29_15-29-17.zip',
    'springSL10_signal_IS':  'backtest-result-2026-09-29_15-29-54.zip',
    'springSL10_signal_OOS': 'backtest-result-2026-09-29_15-29-19.zip',
    'springSL10_real_IS':    'backtest-result-2026-09-29_15-31-01.zip',
    'springSL10_real_OOS':   'backtest-result-2026-09-29_15-30-46.zip',
    'spring3X_real_IS':      'backtest-result-2026-09-29_15-31-28.zip',
    'spring3X_real_OOS':     'backtest-result-2026-09-29_15-31-18.zip',
    'H72_IS':                'backtest-result-2026-09-29_15-13-33.zip',
    'H72_OOS':               'backtest-result-2026-09-29_15-11-52.zip',
    'H1_IS':                 'backtest-result-2026-09-29_15-08-41.zip',
    'H1_OOS':                'backtest-result-2026-09-29_15-08-35.zip',
    'H2_IS':                 'backtest-result-2026-09-29_15-08-45.zip',
    'H2_OOS':                'backtest-result-2026-09-29_15-08-36.zip',
}


def load(zipname):
    z = zipfile.ZipFile(os.path.join(BASE, zipname))
    name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    d = json.loads(z.read(name))
    strat = list(d['strategy'].keys())[0]
    meta = d['strategy'][strat]
    return strat, meta


def max_drawdown(trades, start):
    """DD maximo % sobre la curva de balance usando profit_abs al cierre de cada trade."""
    eq = start
    peak = start
    mdd = 0.0
    mdd_abs = 0.0
    for t in sorted(trades, key=lambda x: x['close_timestamp']):
        eq += t['profit_abs']
        peak = max(peak, eq)
        dd = (peak - eq)
        if peak > 0 and dd / peak > mdd:
            mdd = dd / peak
            mdd_abs = dd
    return mdd * 100, mdd_abs


def describe(label):
    strat, meta = load(DATASETS[label])
    trades = meta['trades']
    start = meta.get('starting_balance') or 100000.0
    profits = [t['profit_abs'] for t in trades]
    ratios = [t['profit_ratio'] for t in trades]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    n = len(trades)
    winrate = 100.0 * len(wins) / n if n else 0.0
    total = sum(profits)
    dd_pct, dd_abs = max_drawdown(trades, start)
    # exit reasons
    ex = collections.Counter(t['exit_reason'] for t in trades)
    # funding
    fund = sum(t.get('funding_fees') or 0 for t in trades)
    fund_trades = sum(1 for t in trades if (t.get('funding_fees') or 0) != 0)
    # MAE (peor excursion adversa) para longs
    mae = []
    for t in trades:
        if t['is_short']:
            m = (t['max_rate'] - t['open_rate']) / t['open_rate']
        else:
            m = (t['min_rate'] - t['open_rate']) / t['open_rate']
        mae.append(m * 100)
    # daily: lista de [fecha, profit_abs]
    dp = meta.get('daily_profit') or []
    days = sorted(dp, key=lambda x: x[0])
    r = {
        'strategy': strat, 'n': n, 'winrate_pct': round(winrate, 2),
        'mean_ratio_pct': round(100 * sum(ratios) / n, 3) if n else None,
        'median_ratio_pct': round(100 * statistics.median(ratios), 3) if n else None,
        'total_profit_abs': round(total, 3),
        'final_balance': round(start + total, 3),
        'return_pct_on_start': round(100 * total / start, 2),
        'reported_final_balance': meta.get('final_balance'),
        'recalc_dd_pct': round(dd_pct, 2), 'recalc_dd_abs': round(dd_abs, 2),
        'reported_dd_pct': round(100 * (meta.get('max_drawdown_account') or 0), 2),
        'exit_reasons': dict(ex),
        'funding_sum': round(fund, 3), 'funding_trades': fund_trades,
        'mae_min_pct': round(min(mae), 2) if mae else None,
        'mae_median_pct': round(statistics.median(mae), 2) if mae else None,
        'mae_le_minus10_pct': round(100.0 * sum(1 for m in mae if m <= -10.0) / n, 2) if n else None,
        'rejected_signals': meta.get('rejected_signals'),
        'max_open_trades': meta.get('max_open_trades'),
        'stake_amount': meta.get('stake_amount'),
        'leverage': sorted(set(t['leverage'] for t in trades)),
        'avg_stake': round(meta.get('avg_stake_amount', 0), 3),
    }
    return r, trades, meta


# ---------- conciliacion (Tarea 1) ----------
print("=" * 110)
print("TAREA 1/2: METRICAS RECALCULADAS DESDE LOS TRADES CRUDOS")
print("=" * 110)
summary = {}
for label in DATASETS:
    r, trades, meta = describe(label)
    summary[label] = r
    print(f"\n[{label}] {r['strategy']}  n={r['n']}")
    print(f"  winrate={r['winrate_pct']}%  mean={r['mean_ratio_pct']}%  median={r['median_ratio_pct']}%")
    print(f"  total_abs={r['total_profit_abs']}  final={r['final_balance']} (log={r['reported_final_balance']})  "
          f"return={r['return_pct_on_start']}% on start={meta.get('starting_balance')}")
    print(f"  DD recalc={r['recalc_dd_pct']}% ({r['recalc_dd_abs']})  DD log={r['reported_dd_pct']}%")
    print(f"  exits={r['exit_reasons']}")
    print(f"  funding_sum={r['funding_sum']} en {r['funding_trades']} trades | MAE<=-10%: {r['mae_le_minus10_pct']}% "
          f"| MAE mediana={r['mae_median_pct']}% min={r['mae_min_pct']}%")
    print(f"  rejected={r['rejected_signals']} max_open={r['max_open_trades']} stake={r['stake_amount']} lev={r['leverage']}")

OUT['summary'] = summary

# ---------- Tarea 2a: distribucion / concentracion ----------
print("\n" + "=" * 110)
print("TAREA 2a/2b: DISTRIBUCION Y CONCENTRACION")
print("=" * 110)
dist = {}
for label in ['spring_signal_IS', 'spring_signal_OOS', 'springSL10_signal_IS',
              'springSL10_signal_OOS', 'springSL10_real_IS', 'springSL10_real_OOS']:
    strat, meta = load(DATASETS[label])
    trades = meta['trades']
    n = len(trades)
    profits = sorted([t['profit_abs'] for t in trades], reverse=True)
    total = sum(profits)
    gross_win = sum(p for p in profits if p > 0)
    top10 = sum(profits[:10])
    top5 = sum(profits[:5])
    top5_pos = sum(p for p in profits if p > 0)
    # top 5 dias: lista de [fecha, profit_abs]
    dp = meta.get('daily_profit') or []
    days = sorted((row[1] for row in dp), reverse=True)
    top5d = sum(days[:5])
    # por par (beneficio neto)
    by_pair = collections.defaultdict(float)
    for t in trades:
        by_pair[t['pair']] += t['profit_abs']
    best = sorted(by_pair.items(), key=lambda kv: kv[1], reverse=True)
    # por año
    by_year = collections.defaultdict(float)
    for t in trades:
        by_year[t['close_date'][:4]] += t['profit_abs']
    d = {
        'n': n, 'total_abs': round(total, 2), 'gross_win': round(gross_win, 2),
        'top10_abs': round(top10, 2), 'top10_share_of_net_pct': round(100 * top10 / total, 1) if total else None,
        'top10_share_of_gross_pct': round(100 * top10 / gross_win, 1) if gross_win else None,
        'top5_abs': round(top5, 2), 'top5_share_of_net_pct': round(100 * top5 / total, 1) if total else None,
        'top5_days_abs': round(top5d, 2), 'top5_days_share_of_net_pct': round(100 * top5d / total, 1) if total else None,
        'best_pairs': [(p, round(v, 1)) for p, v in best[:5]],
        'worst_pairs': [(p, round(v, 1)) for p, v in best[-5:]],
        'by_year': {k: round(v, 1) for k, v in sorted(by_year.items())},
    }
    dist[label] = d
    print(f"\n[{label}] n={n} total={d['total_abs']} gross_win={d['gross_win']}")
    print(f"  top10 trades = {d['top10_abs']} -> {d['top10_share_of_net_pct']}% del neto, "
          f"{d['top10_share_of_gross_pct']}% del bruto ganador")
    print(f"  top5 trades  = {d['top5_abs']} -> {d['top5_share_of_net_pct']}% del neto")
    print(f"  top5 dias    = {d['top5_days_abs']} -> {d['top5_days_share_of_net_pct']}% del neto")
    print(f"  mejores pares={d['best_pairs']}")
    print(f"  peores pares ={d['worst_pairs']}")
    print(f"  por anio     ={d['by_year']}")

OUT['distribution'] = dist

# ---------- Tarea 2c: clustering ----------
print("\n" + "=" * 110)
print("TAREA 2c: CLUSTERING (varios pares en la misma vela/dia)")
print("=" * 110)
cl = {}
for label in ['spring_signal_IS', 'spring_signal_OOS']:
    strat, meta = load(DATASETS[label])
    trades = meta['trades']
    by_ts = collections.defaultdict(list)
    for t in trades:
        by_ts[t['open_timestamp']].append(t['profit_ratio'] * 100)
    clusters = {ts: v for ts, v in by_ts.items() if len(v) > 1}
    multi = [p for v in clusters.values() for p in v]
    solo = [v[0] for ts, v in by_ts.items() if len(v) == 1]
    cl[label] = {
        'eventos': len(trades), 'timestamps_distintos': len(by_ts),
        'timestamps_con_>=2_pares': len(clusters),
        'eventos_en_cluster': len(multi),
        'pct_eventos_en_cluster': round(100 * len(multi) / len(trades), 1),
        'mean_cluster_pct': round(sum(multi) / len(multi), 3) if multi else None,
        'mean_solo_pct': round(sum(solo) / len(solo), 3) if solo else None,
        'winrate_cluster_pct': round(100 * sum(1 for p in multi if p > 0) / len(multi), 1) if multi else None,
        'winrate_solo_pct': round(100 * sum(1 for p in solo if p > 0) / len(solo), 1) if solo else None,
        'max_pares_misma_vela': max((len(v) for v in by_ts.values()), default=0),
    }
    print(f"[{label}] {cl[label]}")
OUT['clustering'] = cl

# ---------- Tarea 2e: profundidad de caida (MAE) y stop vs tiempo ----------
print("\n" + "=" * 110)
print("TAREA 2e: MAE ANTES DE RESOLVER, STOP vs TIEMPO")
print("=" * 110)
mae = {}
for label in ['springSL10_signal_IS', 'springSL10_signal_OOS', 'spring_signal_IS', 'spring_signal_OOS']:
    strat, meta = load(DATASETS[label])
    trades = meta['trades']
    n = len(trades)
    def mae_of(t):
        return ((t['min_rate'] - t['open_rate']) / t['open_rate']) * 100
    mae_all = sorted(mae_of(t) for t in trades)
    stop = [t for t in trades if t['exit_reason'] == 'stop_loss']
    time_exit = [t for t in trades if t['exit_reason'] == 'time_72h']
    touch10 = sum(1 for m in mae_all if m <= -10.0)
    # peor MAE de los que cerraron por tiempo
    mae_time = [mae_of(t) for t in time_exit]
    d = {
        'n': n, 'stop_loss_n': len(stop), 'stop_loss_pct': round(100 * len(stop) / n, 1),
        'time_n': len(time_exit), 'time_pct': round(100 * len(time_exit) / n, 1),
        'cuenta_mae<=-10': touch10, 'pct_mae<=-10': round(100 * touch10 / n, 1),
        'mae_p10': round(mae_all[int(0.10 * (n - 1))], 2),
        'mae_p25': round(mae_all[int(0.25 * (n - 1))], 2),
        'mae_median': round(mae_all[n // 2], 2),
        'peor_mae': round(mae_all[0], 2),
        'mae_mediana_ganadores_por_tiempo': round(statistics.median([mae_of(t) for t in time_exit if t['profit_abs'] > 0]), 2) if [t for t in time_exit if t['profit_abs'] > 0] else None,
    }
    mae[label] = d
    print(f"[{label}] {d}")
OUT['mae'] = mae

with open('audit/out_t12.json', 'w', encoding='utf-8') as f:
    json.dump(OUT, f, indent=1, ensure_ascii=False, default=str)
print("\n-> audit/out_t12.json escrito")
