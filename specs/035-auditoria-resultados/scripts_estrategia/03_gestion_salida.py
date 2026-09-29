"""
audit/03_gestion_salida.py
Modelado cuantitativo de gestion de salidas sobre las MISMAS entradas de Wyckoff Spring:
1. Base: Sin stop (72h)
2. Base validada: Stop -10% fijo (72h)
3. Stop -7% fijo (72h)
4. Stop -5% fijo (72h)
5. Stop por ATR: 2.0 * ATR14 y 2.5 * ATR14
6. Stop estructural: bajo el minimo de la vela de ruptura (low_ruptura * 0.995)
7. Salida a 48h (con stop -10%)
8. Salida a 96h (con stop -10%)

Analisis de path-dependency: explicacion de por que TP parcial y trailing stop
no se pueden aproximar solo con min/max y requieren Freqtrade (audit/experimentos_lab.py).

Metricas reportadas para cada variante en IS y OOS:
- Retorno medio (%)
- Win rate (%)
- Peor racha de perdidas (consecutive losses)
- Max Drawdown (%) de la curva acumulada
- Ratio Retorno Total / Drawdown
"""

import os
import zipfile
import json
import pandas as pd
import numpy as np
import talib

LOOKBACK = 20
CONFIRM_WINDOW = 3
VOLUME_PERIOD = 20
CACHE_DIR = 'audit/data_cache'
FEE = 0.0005 # 0.05% comision taker futuros

def load_trades(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        jname = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
        d = json.loads(z.read(jname))
        trades = d['strategy']['WyckoffLab_SpringH72']['trades']
        df = pd.DataFrame(trades)
        df['open_date'] = pd.to_datetime(df['open_date'])
        df['close_date'] = pd.to_datetime(df['close_date'])
        return df

def wyckoff_events_with_lows(df):
    lows = df['low'].astype(float).values
    closes = df['close'].astype(float).values
    volume = df['volume'].astype(float).values
    avg_vol = talib.SMA(volume, timeperiod=VOLUME_PERIOD)
    with np.errstate(divide='ignore', invalid='ignore'):
        rel_vol = np.where(avg_vol > 0, volume / avg_vol, np.nan)
    support = df['low'].astype(float).rolling(LOOKBACK).min().shift(1).values
    n = len(df)
    spring = np.zeros(n, dtype=bool)
    breakout_low = np.full(n, np.nan)
    for i in range(n):
        level = support[i]
        if np.isnan(level) or not (lows[i] < level):
            continue
        for j in range(i + 1, min(i + 1 + CONFIRM_WINDOW, n)):
            if closes[j] > level:
                spring[j] = True
                breakout_low[j] = lows[i]
                break
    return spring, breakout_low

def build_trade_dataset():
    df_is = load_trades('audit_data/lab_trades/backtest-result-2026-09-29_15-29-59.zip')
    df_oos = load_trades('audit_data/lab_trades/backtest-result-2026-09-29_15-29-17.zip')
    df_is['dataset'] = 'IS'
    df_oos['dataset'] = 'OOS'
    all_trades = pd.concat([df_is, df_oos], ignore_index=True)

    # Cargar dfs 4h
    pair_dfs = {}
    for f in os.listdir(CACHE_DIR):
        if f.endswith('_4h.pkl') and not f.startswith('BTC_USDT_USDT'):
            parts = f.replace('_4h.pkl', '').split('_')
            full_pair = f"{parts[0]}/{parts[1]}:{parts[2]}"
            df_4h = pd.read_pickle(os.path.join(CACHE_DIR, f))
            spring, brk_low = wyckoff_events_with_lows(df_4h)
            df_4h['brk_low'] = brk_low
            df_4h['atr14'] = talib.ATR(
                df_4h['high'].astype(float).values,
                df_4h['low'].astype(float).values,
                df_4h['close'].astype(float).values,
                timeperiod=14
            )
            pair_dfs[full_pair] = df_4h

    # Enriquecer cada trade con velas subsecuentes (para 48h, 96h, etc.)
    enriched = []
    for idx, t in all_trades.iterrows():
        pair = t['pair']
        open_ts = t['open_timestamp']
        conf_ts = open_ts - 4 * 3600 * 1000
        df_p = pair_dfs[pair]
        
        conf_idx = df_p[df_p['timestamp'] == conf_ts].index
        if len(conf_idx) == 0:
            continue
        c_i = conf_idx[0]
        entry_i = c_i + 1 # vela de entrada (open_rate)
        
        # vela a 48h = entry_i + 12 velas (cada vela es 4h, 12 * 4 = 48h)
        # vela a 72h = entry_i + 18 velas (18 * 4 = 72h)
        # vela a 96h = entry_i + 24 velas (24 * 4 = 96h)
        
        atr14 = df_p.loc[c_i, 'atr14']
        brk_low = df_p.loc[c_i, 'brk_low']
        open_rate = t['open_rate']
        close_rate_72h = t['close_rate']
        min_rate_72h = t['min_rate']
        max_rate_72h = t['max_rate']
        
        # 48h data
        if entry_i + 12 < len(df_p):
            close_rate_48h = df_p.loc[entry_i + 12, 'open'] # sale al open de vela 12
            min_rate_48h = df_p.loc[entry_i : entry_i + 11, 'low'].min()
            max_rate_48h = df_p.loc[entry_i : entry_i + 11, 'high'].max()
        else:
            close_rate_48h = close_rate_72h
            min_rate_48h = min_rate_72h
            max_rate_48h = max_rate_72h

        # 96h data
        if entry_i + 24 < len(df_p):
            close_rate_96h = df_p.loc[entry_i + 24, 'open']
            min_rate_96h = df_p.loc[entry_i : entry_i + 23, 'low'].min()
            max_rate_96h = df_p.loc[entry_i : entry_i + 23, 'high'].max()
        else:
            close_rate_96h = close_rate_72h
            min_rate_96h = min_rate_72h
            max_rate_96h = max_rate_72h

        enriched.append({
            'dataset': t['dataset'],
            'pair': pair,
            'open_date': t['open_date'],
            'open_rate': open_rate,
            'close_rate_72h': close_rate_72h,
            'min_rate_72h': min_rate_72h,
            'max_rate_72h': max_rate_72h,
            'close_rate_48h': close_rate_48h,
            'min_rate_48h': min_rate_48h,
            'max_rate_48h': max_rate_48h,
            'close_rate_96h': close_rate_96h,
            'min_rate_96h': min_rate_96h,
            'max_rate_96h': max_rate_96h,
            'atr14': atr14,
            'brk_low': brk_low,
            'raw_profit_ratio_72h': t['profit_ratio'],
            'funding_fees': t.get('funding_fees', 0.0) / 100.0, # ratio sobre stake 100
        })

    return pd.DataFrame(enriched)

def calc_curve_metrics(returns_series):
    # returns_series es array de retornos fraccionales (ej: +0.015, -0.05)
    r = np.array(returns_series)
    n = len(r)
    if n == 0:
        return {}
    win_rate = (r > 0).mean() * 100.0
    mean_ret = r.mean() * 100.0
    total_ret = r.sum() * 100.0

    # Peor racha de perdidas consecutivas
    is_loss = (r <= 0).astype(int)
    max_streak = 0
    current_streak = 0
    for loss in is_loss:
        if loss == 1:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 0

    # Curva acumulada y Drawdown
    equity = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(equity)
    drawdowns = (equity - peak) / peak
    max_dd = abs(drawdowns.min()) * 100.0

    # Ratio Retorno / DD
    ret_dd_ratio = total_ret / max_dd if max_dd > 0 else np.nan

    return {
        'n': n,
        'win_rate': win_rate,
        'mean_ret': mean_ret,
        'total_ret': total_ret,
        'max_streak': max_streak,
        'max_dd': max_dd,
        'ret_dd_ratio': ret_dd_ratio
    }

def simulate_variants(df_all):
    variants = [
        ('1. Sin stop (72h)', lambda r: sim_trade(r, hold='72h', stop_type='none')),
        ('2. Stop -10% fijo (72h)', lambda r: sim_trade(r, hold='72h', stop_type='fixed', stop_pct=0.10)),
        ('3. Stop -7% fijo (72h)', lambda r: sim_trade(r, hold='72h', stop_type='fixed', stop_pct=0.07)),
        ('4. Stop -5% fijo (72h)', lambda r: sim_trade(r, hold='72h', stop_type='fixed', stop_pct=0.05)),
        ('5. Stop ATR 2.0x (72h)', lambda r: sim_trade(r, hold='72h', stop_type='atr', atr_mult=2.0)),
        ('6. Stop ATR 2.5x (72h)', lambda r: sim_trade(r, hold='72h', stop_type='atr', atr_mult=2.5)),
        ('7. Stop Estructural (72h)', lambda r: sim_trade(r, hold='72h', stop_type='structural')),
        ('8. Salida 48h (Stop -10%)', lambda r: sim_trade(r, hold='48h', stop_type='fixed', stop_pct=0.10)),
        ('9. Salida 96h (Stop -10%)', lambda r: sim_trade(r, hold='96h', stop_type='fixed', stop_pct=0.10)),
    ]

    print("\n=========================================================================================")
    print(" EVALUACION DE VARIANTES DE SALIDA (Gestion de Salida sobre entradas Wyckoff Spring)")
    print("=========================================================================================")
    print(f"{'Variante':<26} | {'IS Win%':<7} {'IS Ret%':<8} {'IS Racha':<8} {'IS DD%':<7} {'IS Ret/DD':<9} | {'OOS Win%':<8} {'OOS Ret%':<8} {'OOS Racha':<9} {'OOS DD%':<8} {'OOS Ret/DD':<9}")
    print("-" * 125)

    df_is = df_all[df_all['dataset'] == 'IS'].sort_values('open_date').reset_index(drop=True)
    df_oos = df_all[df_all['dataset'] == 'OOS'].sort_values('open_date').reset_index(drop=True)

    for name, sim_fn in variants:
        rets_is = [sim_fn(row) for _, row in df_is.iterrows()]
        rets_oos = [sim_fn(row) for _, row in df_oos.iterrows()]

        m_is = calc_curve_metrics(rets_is)
        m_oos = calc_curve_metrics(rets_oos)

        print(f"{name:<26} | {m_is['win_rate']:5.1f}%  {m_is['mean_ret']:+6.2f}%   {m_is['max_streak']:<8} {m_is['max_dd']:5.1f}%  {m_is['ret_dd_ratio']:8.2f} | "
              f"{m_oos['win_rate']:5.1f}%   {m_oos['mean_ret']:+6.2f}%    {m_oos['max_streak']:<9} {m_oos['max_dd']:5.1f}%   {m_oos['ret_dd_ratio']:8.2f}")

def sim_trade(row, hold='72h', stop_type='none', stop_pct=0.10, atr_mult=2.0):
    open_p = row['open_rate']
    if hold == '48h':
        close_p = row['close_rate_48h']
        min_p = row['min_rate_48h']
    elif hold == '96h':
        close_p = row['close_rate_96h']
        min_p = row['min_rate_96h']
    else: # 72h
        close_p = row['close_rate_72h']
        min_p = row['min_rate_72h']

    fees = 2 * FEE # taker open + taker close
    funding = row.get('funding_fees', 0.0)

    # Determinar stop_price
    if stop_type == 'none':
        stop_p = 0.0
    elif stop_type == 'fixed':
        stop_p = open_p * (1.0 - stop_pct)
    elif stop_type == 'atr':
        atr = row['atr14']
        if pd.isna(atr) or atr <= 0:
            stop_p = open_p * 0.90 # fallback
        else:
            stop_p = open_p - atr_mult * atr
    elif stop_type == 'structural':
        brk_low = row['brk_low']
        if pd.isna(brk_low) or brk_low <= 0 or brk_low >= open_p:
            stop_p = open_p * 0.90 # fallback si no hay minimo valido
        else:
            # Colocar 0.5% debajo del minimo de la ruptura
            stop_p = brk_low * 0.995
            # Cap de seguridad: maximo riesgo -15%
            stop_p = max(stop_p, open_p * 0.85)

    # Chequear si toco stop
    if stop_p > 0 and min_p <= stop_p:
        # Salida por stop
        raw_ret = (stop_p - open_p) / open_p
        net_ret = raw_ret - fees - funding
        return net_ret
    else:
        # Salida por tiempo
        raw_ret = (close_p - open_p) / open_p
        net_ret = raw_ret - fees - funding
        return net_ret

if __name__ == '__main__':
    df_all = build_trade_dataset()
    simulate_variants(df_all)
