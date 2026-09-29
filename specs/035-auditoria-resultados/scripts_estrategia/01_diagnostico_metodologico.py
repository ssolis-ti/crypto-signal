"""
audit/01_diagnostico_metodologico.py
Auditoria cuantitativa del edge Wyckoff Spring: diagnostico metodologico.
Analiza:
1. Comparaciones multiples y p-hacking entre slices
2. Eleccion del corte IS / OOS y desempeno ano por ano
3. Solapamiento de trades en la misma fecha / vela (clustering)
4. Correlacion efectiva entre trades simultaneos
5. Tamano de muestra por celda / par
6. Modos senal vs modo real (100 USDT, max 3 trades)
"""

import zipfile
import json
import os
import pandas as pd
import numpy as np

def load_trades_from_zip(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        json_names = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n]
        if not json_names:
            raise ValueError(f"No json found in {zip_path}")
        d = json.loads(z.read(json_names[0]))
        strat_name = list(d['strategy'].keys())[0]
        trades = d['strategy'][strat_name]['trades']
        df = pd.DataFrame(trades)
        df['open_date'] = pd.to_datetime(df['open_date'])
        df['close_date'] = pd.to_datetime(df['close_date'])
        df['year'] = df['open_date'].dt.year
        df['open_candle'] = df['open_date']
        return df, strat_name

def analyze_dataset(df_is, df_oos, name):
    print(f"\n==================================================")
    print(f" ANALISIS METODOLOGICO: {name}")
    print(f"==================================================")
    
    # 1. Tamano y metricas basicas
    for period, df in [('IS (2022-2024)', df_is), ('OOS (2025-2026)', df_oos)]:
        n = len(df)
        wins = (df['profit_ratio'] > 0).sum()
        win_rate = wins / n if n > 0 else 0
        mean_ret = df['profit_ratio'].mean() * 100
        median_ret = df['profit_ratio'].median() * 100
        std_ret = df['profit_ratio'].std() * 100
        print(f"[{period}] N={n}, WinRate={win_rate*100:.2f}%, Media={mean_ret:+.2f}%, Mediana={median_ret:+.2f}%, Std={std_ret:.2f}%")
        
    # 2. Desempeno Ano por Ano
    df_all = pd.concat([df_is.assign(period='IS'), df_oos.assign(period='OOS')])
    print("\n--- Desglose por Ano ---")
    by_year = df_all.groupby('year').agg(
        n=('profit_ratio', 'count'),
        win_rate=('profit_ratio', lambda x: (x > 0).mean() * 100),
        mean_ret=('profit_ratio', lambda x: x.mean() * 100),
        sum_ret=('profit_ratio', lambda x: x.sum() * 100),
        loss_max=('profit_ratio', lambda x: x.min() * 100)
    )
    print(by_year.to_string())

    # 3. Solapamiento / Clustering de trades
    print("\n--- Analisis de Clusters / Solapamiento de trades ---")
    for period, df in [('IS', df_is), ('OOS', df_oos)]:
        # Conteo de senales por misma vela de apertura
        trades_per_candle = df.groupby('open_date').size()
        clusters = trades_per_candle[trades_per_candle > 1]
        cluster_trades_count = trades_per_candle[trades_per_candle > 1].sum()
        pct_in_cluster = (cluster_trades_count / len(df)) * 100
        max_simultaneous = trades_per_candle.max()
        unique_candles = len(trades_per_candle)
        print(f"[{period}] Total velas con senal: {unique_candles} (de {len(df)} trades totales)")
        print(f"  Trades en cluster (misma vela >1 par): {cluster_trades_count} ({pct_in_cluster:.1f}% de todos los trades)")
        print(f"  Max senales simultaneas en una sola vela: {max_simultaneous}")
        print(f"  Velas con >= 3 senales simultaneas: {(trades_per_candle >= 3).sum()}")
        print(f"  Velas con >= 5 senales simultaneas: {(trades_per_candle >= 5).sum()}")

    # 4. Correlacion de retornos en eventos simultaneos
    print("\n--- Correlacion en eventos simultaneos ---")
    for period, df in [('IS', df_is), ('OOS', df_oos)]:
        grouped = df.groupby('open_date')
        pairwise_corrs = []
        same_direction = []
        for dt, g in grouped:
            if len(g) >= 2:
                rets = g['profit_ratio'].values
                # Chequear si todos ganan o todos pierden
                all_pos = (rets > 0).all()
                all_neg = (rets < 0).all()
                same_direction.append(all_pos or all_neg)
        if same_direction:
            pct_same_dir = (sum(same_direction) / len(same_direction)) * 100
            print(f"[{period}] Clusters con >= 2 trades: {len(same_direction)}")
            print(f"  Clusters donde TODOS ganan o TODOS pierden: {sum(same_direction)} ({pct_same_dir:.1f}%)")

    # 5. Concentracion por par
    print("\n--- Concentracion por par (Top 5 y Bottom 5 en OOS) ---")
    pair_perf_oos = df_oos.groupby('pair').agg(
        n=('profit_ratio', 'count'),
        win_rate=('profit_ratio', lambda x: (x > 0).mean() * 100),
        mean_ret=('profit_ratio', lambda x: x.mean() * 100)
    ).sort_values(by='n', ascending=False)
    print("Muestra por par en OOS:")
    print(f"  Pares con n < 10 en OOS: {(pair_perf_oos['n'] < 10).sum()} de {len(pair_perf_oos)}")
    print(f"  Pares con n < 20 en OOS: {(pair_perf_oos['n'] < 20).sum()} de {len(pair_perf_oos)}")
    print(f"  Pares con n >= 30 en OOS: {(pair_perf_oos['n'] >= 30).sum()} de {len(pair_perf_oos)}")

if __name__ == '__main__':
    # Analizar WyckoffLab_SpringH72 (modo senal)
    df_is_sig, _ = load_trades_from_zip('audit_data/lab_trades/backtest-result-2026-09-29_15-29-59.zip')
    df_oos_sig, _ = load_trades_from_zip('audit_data/lab_trades/backtest-result-2026-09-29_15-29-17.zip')
    analyze_dataset(df_is_sig, df_oos_sig, "WyckoffLab_SpringH72 (Modo Senal, Sin Stop)")

    # Analizar WyckoffLab_SpringH72_SL10 (modo senal)
    df_is_sl, _ = load_trades_from_zip('audit_data/lab_trades/backtest-result-2026-09-29_15-29-54.zip')
    df_oos_sl, _ = load_trades_from_zip('audit_data/lab_trades/backtest-result-2026-09-29_15-29-19.zip')
    analyze_dataset(df_is_sl, df_oos_sl, "WyckoffLab_SpringH72_SL10 (Modo Senal, Stop -10%)")

    # Analizar WyckoffLab_SpringH72_SL10 (modo real 100 USDT)
    df_is_real, _ = load_trades_from_zip('audit_data/lab_trades/backtest-result-2026-09-29_15-31-01.zip')
    df_oos_real, _ = load_trades_from_zip('audit_data/lab_trades/backtest-result-2026-09-29_15-30-46.zip')
    analyze_dataset(df_is_real, df_oos_real, "WyckoffLab_SpringH72_SL10 (Modo Real 100 USDT, max 3 trades)")
