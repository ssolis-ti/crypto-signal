"""
audit/05_senales_nuevas.py
Evaluacion cuantitativa de las 3 senales nuevas propuestas:
1. Wyckoff Spring + Caida previa fuerte 24h (>= 7%, >= 10% - Capitulacion confluente)
2. Profundidad de penetracion del Spring bajo el soporte ((support - low) / support)
3. Wyckoff Spring + Funding Rate de Futuros (tasa de financiacion negativa / short squeeze)

Reporta para cada una en IS y OOS:
- n
- Win rate (%)
- Retorno medio (%)
- Comparacion vs baseline
- Criterio de aceptacion / descarte pre-registrado
"""

import os
import zipfile
import json
import pandas as pd
import numpy as np
import talib
import ccxt

LOOKBACK = 20
CONFIRM_WINDOW = 3
VOLUME_PERIOD = 20
CACHE_DIR = 'audit/data_cache'
FEE = 0.0005

def load_data():
    df_feat = pd.read_pickle('audit/enriched_trades.pkl')
    return df_feat

def analyze_penetration_depth(df_feat):
    print("\n=======================================================")
    print(" SENAL 1: PROFUNDIDAD DE PENETRACION DEL SPRING")
    print(" Hipotesis: Barredas reales (1% a 4%) tienen mas edge que ruidos (<1%) o rupturas graves (>5%)")
    print("=======================================================")
    
    # Calcular penetracion con las velas 4h
    pair_dfs = {}
    for f in os.listdir(CACHE_DIR):
        if f.endswith('_4h.pkl') and not f.startswith('BTC_USDT_USDT'):
            parts = f.replace('_4h.pkl', '').split('_')
            full_pair = f"{parts[0]}/{parts[1]}:{parts[2]}"
            df_4h = pd.read_pickle(os.path.join(CACHE_DIR, f))
            # Calcular support y breakout depth
            df_4h['support'] = df_4h['low'].astype(float).rolling(LOOKBACK).min().shift(1)
            pair_dfs[full_pair] = df_4h

    depths = []
    for idx, row in df_feat.iterrows():
        pair = row['pair']
        open_ts = pd.to_datetime(row['open_date']).value // 10**6
        conf_ts = open_ts - 4 * 3600 * 1000
        df_p = pair_dfs[pair]
        c_rows = df_p[df_p['timestamp'] == conf_ts]
        if len(c_rows) == 0:
            depths.append(np.nan)
            continue
        c_i = c_rows.index[0]
        # Buscar la vela de ruptura en las 3 velas previas
        found_depth = np.nan
        for look_back in range(1, CONFIRM_WINDOW + 1):
            b_i = c_i - look_back
            if b_i < 0:
                break
            sup = df_p.loc[b_i, 'support']
            low_b = df_p.loc[b_i, 'low']
            if low_b < sup:
                depth_pct = (sup - low_b) / sup * 100.0
                found_depth = depth_pct
                break
        depths.append(found_depth)

    df_feat['penetration_pct'] = depths
    
    # Evaluar cortes de penetracion
    df_is = df_feat[df_feat['dataset'] == 'IS']
    df_oos = df_feat[df_feat['dataset'] == 'OOS']

    cuts = [
        ("Penetracion Superficial (< 1.0%)", lambda d: d['penetration_pct'] < 1.0),
        ("Penetracion Moderada (1.0% - 3.5%)", lambda d: (d['penetration_pct'] >= 1.0) & (d['penetration_pct'] < 3.5)),
        ("Penetracion Profunda (>= 3.5%)", lambda d: d['penetration_pct'] >= 3.5),
        ("Zona Optima Wyckoff (1.0% - 5.0%)", lambda d: (d['penetration_pct'] >= 1.0) & (d['penetration_pct'] <= 5.0)),
    ]

    print(f"{'Corte de Penetracion':<35} | {'IS n':<6} {'IS win%':<8} {'IS media%':<10} | {'OOS n':<6} {'OOS win%':<8} {'OOS media%':<10} | {'Candidato?':<12}")
    print("-" * 95)
    for name, mask_fn in cuts:
        sub_is = df_is[mask_fn(df_is)]
        sub_oos = df_oos[mask_fn(df_oos)]
        n_is = len(sub_is)
        win_is = sub_is['win'].mean() * 100 if n_is > 0 else 0
        mean_is = sub_is['profit_ratio'].mean() if n_is > 0 else 0
        n_oos = len(sub_oos)
        win_oos = sub_oos['win'].mean() * 100 if n_oos > 0 else 0
        mean_oos = sub_oos['profit_ratio'].mean() if n_oos > 0 else 0
        is_cand = (n_is >= 30 and n_oos >= 30 and mean_is > 1.52 and mean_oos > 1.76)
        cand_str = "SI (VALIDO)" if is_cand else "NO"
        print(f"{name:<35} | {n_is:<6} {win_is:6.1f}% {mean_is:+8.2f}% | {n_oos:<6} {win_oos:6.1f}% {mean_oos:+8.2f}% | {cand_str:<12}")

def analyze_confluent_capitulation(df_feat):
    print("\n=======================================================")
    print(" SENAL 2: WYCKOFF SPRING TRAS CAIDA PREVIA FUERTE")
    print(" Hipotesis: Confluencia entre Wyckoff Spring (absorcion) y Mean Reversion (sobreventa extrema)")
    print("=======================================================")
    df_is = df_feat[df_feat['dataset'] == 'IS']
    df_oos = df_feat[df_feat['dataset'] == 'OOS']

    cuts = [
        ("Baseline (Todos los Springs)", lambda d: d['chg24h'] == d['chg24h']),
        ("Spring + Caida 24h <= -5%", lambda d: d['chg24h'] <= -5.0),
        ("Spring + Caida 24h <= -8%", lambda d: d['chg24h'] <= -8.0),
        ("Spring + Caida 24h <= -10%", lambda d: d['chg24h'] <= -10.0),
        ("Spring + Caida 24h <= -12%", lambda d: d['chg24h'] <= -12.0),
        ("Spring + Caida 7d <= -15%", lambda d: d['chg7d'] <= -15.0),
        ("Spring + Caida 7d <= -20%", lambda d: d['chg7d'] <= -20.0),
    ]

    print(f"{'Filtro de Capitulacion':<35} | {'IS n':<6} {'IS win%':<8} {'IS media%':<10} | {'OOS n':<6} {'OOS win%':<8} {'OOS media%':<10} | {'Candidato?':<12}")
    print("-" * 95)
    for name, mask_fn in cuts:
        sub_is = df_is[mask_fn(df_is)]
        sub_oos = df_oos[mask_fn(df_oos)]
        n_is = len(sub_is)
        win_is = sub_is['win'].mean() * 100 if n_is > 0 else 0
        mean_is = sub_is['profit_ratio'].mean() if n_is > 0 else 0
        n_oos = len(sub_oos)
        win_oos = sub_oos['win'].mean() * 100 if n_oos > 0 else 0
        mean_oos = sub_oos['profit_ratio'].mean() if n_oos > 0 else 0
        is_cand = (n_is >= 30 and n_oos >= 30 and mean_is > 1.52 and mean_oos > 1.76)
        cand_str = "SI (VALIDO)" if is_cand else "NO"
        print(f"{name:<35} | {n_is:<6} {win_is:6.1f}% {mean_is:+8.2f}% | {n_oos:<6} {win_oos:6.1f}% {mean_oos:+8.2f}% | {cand_str:<12}")

def analyze_funding_rate():
    print("\n=======================================================")
    print(" SENAL 3: WYCKOFF SPRING + FUNDING RATE DE FUTUROS")
    print(" Hipotesis: Tasa de financiacion fuertemente negativa (crowded shorts) amplifica el rebote")
    print("=======================================================")
    # Descargar o revisar funding rate historico de BTC para ver la distribucion
    btc_fr_path = os.path.join(CACHE_DIR, 'BTC_funding_rate.pkl')
    exchange = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
    
    if not os.path.exists(btc_fr_path):
        print("Descargando historial de funding rate de BTC...")
        all_fr = []
        cur_ts = 1640995200000 # 2022-01-01
        for _ in range(10):
            try:
                frs = exchange.fetch_funding_rate_history('BTC/USDT:USDT', since=cur_ts, limit=1000)
                if not frs:
                    break
                all_fr.extend(frs)
                if len(frs) < 1000:
                    break
                cur_ts = frs[-1]['timestamp'] + 8 * 3600 * 1000
            except Exception as e:
                print("Error fetch funding:", e)
                break
        df_fr = pd.DataFrame(all_fr)
        df_fr.to_pickle(btc_fr_path)
    else:
        df_fr = pd.read_pickle(btc_fr_path)
    
    print(f"Historial de funding rate BTC descargado: {len(df_fr)} registros.")
    if len(df_fr) > 0:
        df_fr['fundingRate'] = df_fr['fundingRate'].astype(float)
        print("Estadisticas Funding Rate BTC:")
        print(df_fr['fundingRate'].describe().to_string())
        
        # Mapear funding rate al dataframe enriquecido
        df_feat = pd.read_pickle('audit/enriched_trades.pkl')
        # Emparejar cada trade con el funding rate de BTC mas cercano anterior a la confirmacion
        df_fr = df_fr.sort_values('timestamp').reset_index(drop=True)
        fr_ts = df_fr['timestamp'].values
        fr_vals = df_fr['fundingRate'].values

        trade_frs = []
        for idx, row in df_feat.iterrows():
            open_ts = pd.to_datetime(row['open_date']).value // 10**6
            # Buscar ultimo funding anterior a open_ts
            idx_fr = np.searchsorted(fr_ts, open_ts, side='right') - 1
            if idx_fr >= 0:
                trade_frs.append(fr_vals[idx_fr])
            else:
                trade_frs.append(np.nan)

        df_feat['btc_funding'] = trade_frs
        df_is = df_feat[df_feat['dataset'] == 'IS']
        df_oos = df_feat[df_feat['dataset'] == 'OOS']

        cuts = [
            ("Funding Negativo (< 0.0)", lambda d: d['btc_funding'] < 0.0),
            ("Funding Neutral / Positivo (>= 0.0)", lambda d: d['btc_funding'] >= 0.0),
            ("Funding Fuertemente Negativo (< -0.005%)", lambda d: d['btc_funding'] < -0.00005),
        ]

        print(f"\n{'Corte Funding BTC':<40} | {'IS n':<6} {'IS win%':<8} {'IS media%':<10} | {'OOS n':<6} {'OOS win%':<8} {'OOS media%':<10} | {'Candidato?':<12}")
        print("-" * 100)
        for name, mask_fn in cuts:
            sub_is = df_is[mask_fn(df_is)]
            sub_oos = df_oos[mask_fn(df_oos)]
            n_is = len(sub_is)
            win_is = sub_is['win'].mean() * 100 if n_is > 0 else 0
            mean_is = sub_is['profit_ratio'].mean() if n_is > 0 else 0
            n_oos = len(sub_oos)
            win_oos = sub_oos['win'].mean() * 100 if n_oos > 0 else 0
            mean_oos = sub_oos['profit_ratio'].mean() if n_oos > 0 else 0
            is_cand = (n_is >= 30 and n_oos >= 30 and mean_is > 1.52 and mean_oos > 1.76)
            cand_str = "SI (VALIDO)" if is_cand else "NO"
            print(f"{name:<40} | {n_is:<6} {win_is:6.1f}% {mean_is:+8.2f}% | {n_oos:<6} {win_oos:6.1f}% {mean_oos:+8.2f}% | {cand_str:<12}")

if __name__ == '__main__':
    df_feat = load_data()
    analyze_penetration_depth(df_feat)
    analyze_confluent_capitulation(df_feat)
    analyze_funding_rate()
