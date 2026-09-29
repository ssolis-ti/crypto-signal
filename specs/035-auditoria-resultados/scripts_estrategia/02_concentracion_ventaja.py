"""
audit/02_concentracion_ventaja.py
Analisis cuantitativo de donde se concentra y donde se diluye la ventaja de Wyckoff Spring.
Une los trades de WyckoffLab_SpringH72 (IS y OOS, modo senal) con caracteristicas calculadas
con precios publicos de Binance Futures:
(a) Volumen relativo de la ruptura por tramos (2.5-3.5x, 3.5-5x, >5x)
(b) Volatilidad previa (ATR% 14 de velas 4h)
(c) Cambio del par en 24h y 7d previas (capitulacion)
(d) Regimen de BTC (por encima / por debajo de EMA200 diaria)
(e) Hora UTC y dia de la semana de la confirmacion
(f) Liquidez del par (volumen 24h en USDT)

Reporta n, acierto (win%) y ganancia media (%) en IS y OOS por separado.
Identifica que cumple el estandar del proyecto (mejora en AMBOS periodos con n >= 30).
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

def load_trades(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        jname = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
        d = json.loads(z.read(jname))
        trades = d['strategy']['WyckoffLab_SpringH72']['trades']
        df = pd.DataFrame(trades)
        df['open_date'] = pd.to_datetime(df['open_date'])
        df['close_date'] = pd.to_datetime(df['close_date'])
        return df

def wyckoff_events(df):
    volume = df['volume'].astype(float).values
    avg_vol = talib.SMA(volume, timeperiod=VOLUME_PERIOD)
    with np.errstate(divide='ignore', invalid='ignore'):
        rel_vol = np.where(avg_vol > 0, volume / avg_vol, np.nan)
    lows = df['low'].astype(float).values
    closes = df['close'].astype(float).values
    support = df['low'].astype(float).rolling(LOOKBACK).min().shift(1).values
    n = len(df)
    spring = np.zeros(n, dtype=bool)
    spring_rv = np.full(n, np.nan)
    breakout_idx = np.full(n, -1, dtype=int)
    for i in range(n):
        level = support[i]
        if np.isnan(level) or not (lows[i] < level):
            continue
        for j in range(i + 1, min(i + 1 + CONFIRM_WINDOW, n)):
            if closes[j] > level:
                spring[j] = True
                spring_rv[j] = rel_vol[i]
                breakout_idx[j] = i
                break
    return spring, spring_rv, breakout_idx

def enrich_trades():
    # Cargar BTC 1d y calcular EMA200
    df_btc_1d = pd.read_pickle(os.path.join(CACHE_DIR, 'BTC_1d.pkl'))
    df_btc_1d['ema200'] = talib.EMA(df_btc_1d['close'].astype(float).values, timeperiod=200)
    df_btc_1d['btc_bull'] = df_btc_1d['close'] > df_btc_1d['ema200']
    df_btc_1d['date'] = df_btc_1d['datetime'].dt.date

    # Mapeo date -> btc_bull
    btc_regime_map = dict(zip(df_btc_1d['date'], df_btc_1d['btc_bull']))

    # Cargar todos los dataframes 4h de pares
    pair_dfs = {}
    pair_features = {}
    for f in os.listdir(CACHE_DIR):
        if f.endswith('_4h.pkl') and not f.startswith('BTC_USDT_USDT'):
            p_name = f.replace('_4h.pkl', '').replace('_', '/', 1)
            # e.g. DOGE/USDT:USDT -> DOGE_USDT_USDT -> p_name = DOGE/USDT_USDT
            # Fix naming:
            parts = f.replace('_4h.pkl', '').split('_')
            # parts: ['DOGE', 'USDT', 'USDT'] -> 'DOGE/USDT:USDT'
            full_pair = f"{parts[0]}/{parts[1]}:{parts[2]}"
            df_4h = pd.read_pickle(os.path.join(CACHE_DIR, f))
            
            # Calcular indicadores
            spring, spring_rv, brk_idx = wyckoff_events(df_4h)
            df_4h['spring'] = spring
            df_4h['spring_rv'] = spring_rv
            df_4h['brk_idx'] = brk_idx
            
            # ATR 14
            df_4h['atr14'] = talib.ATR(
                df_4h['high'].astype(float).values,
                df_4h['low'].astype(float).values,
                df_4h['close'].astype(float).values,
                timeperiod=14
            )
            df_4h['atr_pct'] = (df_4h['atr14'] / df_4h['close'].astype(float)) * 100.0

            # Retornos previos
            df_4h['chg24h'] = (df_4h['close'] / df_4h['close'].shift(6) - 1.0) * 100.0
            df_4h['chg7d'] = (df_4h['close'] / df_4h['close'].shift(42) - 1.0) * 100.0

            # Volumen 24h en USDT
            df_4h['quote_vol_candle'] = df_4h['volume'].astype(float) * df_4h['close'].astype(float)
            df_4h['vol24h_usdt'] = df_4h['quote_vol_candle'].rolling(6).sum()

            pair_dfs[full_pair] = df_4h

    # Ahora procesar trades IS y OOS
    df_is = load_trades('audit_data/lab_trades/backtest-result-2026-09-29_15-29-59.zip')
    df_oos = load_trades('audit_data/lab_trades/backtest-result-2026-09-29_15-29-17.zip')
    df_is['dataset'] = 'IS'
    df_oos['dataset'] = 'OOS'

    all_trades = pd.concat([df_is, df_oos], ignore_index=True)

    enriched_rows = []
    matched_count = 0
    unmatched_count = 0

    for idx, trade in all_trades.iterrows():
        pair = trade['pair']
        open_ts = trade['open_timestamp']
        # La vela de confirmacion cerro en open_ts, es decir su timestamp fue open_ts - 4h
        conf_ts = open_ts - 4 * 3600 * 1000
        
        if pair not in pair_dfs:
            unmatched_count += 1
            continue
        
        df_p = pair_dfs[pair]
        conf_rows = df_p[df_p['timestamp'] == conf_ts]
        if len(conf_rows) == 0:
            unmatched_count += 1
            continue
        
        matched_count += 1
        conf_row = conf_rows.iloc[0]
        trade_date = pd.to_datetime(open_ts, unit='ms', utc=True).date()

        enriched_rows.append({
            'dataset': trade['dataset'],
            'pair': pair,
            'open_date': trade['open_date'],
            'profit_ratio': trade['profit_ratio'] * 100.0,
            'win': trade['profit_ratio'] > 0,
            'spring_rv': conf_row['spring_rv'],
            'atr_pct': conf_row['atr_pct'],
            'chg24h': conf_row['chg24h'],
            'chg7d': conf_row['chg7d'],
            'vol24h_usdt': conf_row['vol24h_usdt'],
            'btc_bull': btc_regime_map.get(trade_date, None),
            'conf_hour_utc': pd.to_datetime(conf_ts, unit='ms', utc=True).hour,
            'conf_weekday': pd.to_datetime(conf_ts, unit='ms', utc=True).weekday(), # 0=Mon, 6=Sun
            'open_hour_utc': pd.to_datetime(open_ts, unit='ms', utc=True).hour,
            'open_weekday': pd.to_datetime(open_ts, unit='ms', utc=True).weekday(),
        })

    print(f"Trades matched: {matched_count}, unmatched: {unmatched_count}")
    df_feat = pd.DataFrame(enriched_rows)
    return df_feat

def evaluate_subsets(df_feat):
    df_is = df_feat[df_feat['dataset'] == 'IS']
    df_oos = df_feat[df_feat['dataset'] == 'OOS']

    base_is_n = len(df_is)
    base_is_win = df_is['win'].mean() * 100
    base_is_mean = df_is['profit_ratio'].mean()

    base_oos_n = len(df_oos)
    base_oos_win = df_oos['win'].mean() * 100
    base_oos_mean = df_oos['profit_ratio'].mean()

    print("\n=======================================================")
    print(" BASELINE (WyckoffLab_SpringH72, todos los trades)")
    print("=======================================================")
    print(f"IS : N={base_is_n}, Win={base_is_win:.2f}%, Media={base_is_mean:+.2f}%")
    print(f"OOS: N={base_oos_n}, Win={base_oos_win:.2f}%, Media={base_oos_mean:+.2f}%")

    def report_cut(cut_name, col, bins_or_func):
        print(f"\n-------------------------------------------------------")
        print(f" CORTE: {cut_name}")
        print(f"-------------------------------------------------------")
        print(f"{'Categoria':<25} | {'IS n':<6} {'IS win%':<8} {'IS media%':<10} | {'OOS n':<6} {'OOS win%':<8} {'OOS media%':<10} | {'Candidato?':<12}")
        print("-" * 85)

        if isinstance(bins_or_func, dict):
            categories = bins_or_func.keys()
            for cat in categories:
                mask_fn = bins_or_func[cat]
                sub_is = df_is[mask_fn(df_is)]
                sub_oos = df_oos[mask_fn(df_oos)]
                
                n_is = len(sub_is)
                win_is = sub_is['win'].mean() * 100 if n_is > 0 else 0
                mean_is = sub_is['profit_ratio'].mean() if n_is > 0 else 0

                n_oos = len(sub_oos)
                win_oos = sub_oos['win'].mean() * 100 if n_oos > 0 else 0
                mean_oos = sub_oos['profit_ratio'].mean() if n_oos > 0 else 0

                # Criterio estricto del proyecto:
                # Mejora en AMBOS periodos vs baseline (media > base_media) Y n >= 30 en ambos
                is_candidate = (n_is >= 30 and n_oos >= 30 and mean_is > base_is_mean and mean_oos > base_oos_mean)
                cand_str = "SI (VALIDO)" if is_candidate else "NO"
                if not is_candidate and mean_oos > base_oos_mean and mean_is <= base_is_mean:
                    cand_str = "RUIDO (IS<=)"

                print(f"{cat:<25} | {n_is:<6} {win_is:6.1f}% {mean_is:+8.2f}% | {n_oos:<6} {win_oos:6.1f}% {mean_oos:+8.2f}% | {cand_str:<12}")

    # (a) Volumen relativo de la ruptura por tramos
    report_cut("Volumen Relativo Ruptura (spring_rv)", "spring_rv", {
        "2.5x <= RV < 3.5x": lambda d: (d['spring_rv'] >= 2.5) & (d['spring_rv'] < 3.5),
        "3.5x <= RV < 5.0x": lambda d: (d['spring_rv'] >= 3.5) & (d['spring_rv'] < 5.0),
        "RV >= 5.0x": lambda d: d['spring_rv'] >= 5.0,
    })

    # (b) Volatilidad previa (ATR% 14)
    # Calculemos terciles de ATR% en IS para cortes limpios
    atr_q1 = df_is['atr_pct'].quantile(0.33)
    atr_q2 = df_is['atr_pct'].quantile(0.66)
    report_cut("Volatilidad Previa (ATR% 14)", "atr_pct", {
        f"Baja ATR (<{atr_q1:.1f}%)": lambda d: d['atr_pct'] < atr_q1,
        f"Media ATR ({atr_q1:.1f}-{atr_q2:.1f}%)": lambda d: (d['atr_pct'] >= atr_q1) & (d['atr_pct'] < atr_q2),
        f"Alta ATR (>={atr_q2:.1f}%)": lambda d: d['atr_pct'] >= atr_q2,
        "ATR% < 3.5%": lambda d: d['atr_pct'] < 3.5,
        "ATR% 3.5% - 5.5%": lambda d: (d['atr_pct'] >= 3.5) & (d['atr_pct'] < 5.5),
        "ATR% >= 5.5%": lambda d: d['atr_pct'] >= 5.5,
    })

    # (c) Cambio del par en las 24h y 7d previas
    report_cut("Cambio Prev 24h (chg24h)", "chg24h", {
        "Caida fuerte (<= -10%)": lambda d: d['chg24h'] <= -10.0,
        "Caida moderada (-10% a -5%)": lambda d: (d['chg24h'] > -10.0) & (d['chg24h'] <= -5.0),
        "Caida leve (-5% a 0%)": lambda d: (d['chg24h'] > -5.0) & (d['chg24h'] <= 0.0),
        "Subida previa (> 0%)": lambda d: d['chg24h'] > 0.0,
    })

    report_cut("Cambio Prev 7d (chg7d)", "chg7d", {
        "Caida semanal fuerte (<= -15%)": lambda d: d['chg7d'] <= -15.0,
        "Caida semanal (-15% a 0%)": lambda d: (d['chg7d'] > -15.0) & (d['chg7d'] <= 0.0),
        "Subida semanal (> 0%)": lambda d: d['chg7d'] > 0.0,
    })

    # (d) Regimen de BTC (BTC close > EMA200 diaria)
    report_cut("Regimen de BTC (vs EMA200 diaria)", "btc_bull", {
        "BTC > EMA200 (Bull market)": lambda d: d['btc_bull'] == True,
        "BTC <= EMA200 (Bear market)": lambda d: d['btc_bull'] == False,
    })

    # (e) Hora UTC y Dia de semana de la confirmacion
    report_cut("Hora UTC de confirmacion (cierre)", "conf_hour_utc", {
        "00:00 UTC": lambda d: d['conf_hour_utc'] == 0,
        "04:00 UTC": lambda d: d['conf_hour_utc'] == 4,
        "08:00 UTC": lambda d: d['conf_hour_utc'] == 8,
        "12:00 UTC": lambda d: d['conf_hour_utc'] == 12,
        "16:00 UTC": lambda d: d['conf_hour_utc'] == 16,
        "20:00 UTC": lambda d: d['conf_hour_utc'] == 20,
    })

    report_cut("Dia de la semana (confirmacion)", "conf_weekday", {
        "Lunes (0)": lambda d: d['conf_weekday'] == 0,
        "Martes (1)": lambda d: d['conf_weekday'] == 1,
        "Miercoles (2)": lambda d: d['conf_weekday'] == 2,
        "Jueves (3)": lambda d: d['conf_weekday'] == 3,
        "Viernes (4)": lambda d: d['conf_weekday'] == 4,
        "Sabado (5)": lambda d: d['conf_weekday'] == 5,
        "Domingo (6)": lambda d: d['conf_weekday'] == 6,
        "Fin de semana (Sab-Dom)": lambda d: d['conf_weekday'].isin([5, 6]),
        "Dias habiles (Lun-Vie)": lambda d: d['conf_weekday'].isin([0, 1, 2, 3, 4]),
    })

    # (f) Liquidez del par (volumen 24h en USDT)
    v_q1 = df_is['vol24h_usdt'].quantile(0.33)
    v_q2 = df_is['vol24h_usdt'].quantile(0.66)
    report_cut("Liquidez del par (Volumen 24h USDT)", "vol24h_usdt", {
        f"Baja liquidez (< {v_q1/1e6:.1f}M)": lambda d: d['vol24h_usdt'] < v_q1,
        f"Media liquidez ({v_q1/1e6:.1f}M - {v_q2/1e6:.1f}M)": lambda d: (d['vol24h_usdt'] >= v_q1) & (d['vol24h_usdt'] < v_q2),
        f"Alta liquidez (>= {v_q2/1e6:.1f}M)": lambda d: d['vol24h_usdt'] >= v_q2,
    })

    # Guardar dataframe enriquecido para analisis posteriores
    df_feat.to_pickle('audit/enriched_trades.pkl')
    print("\nDataframe enriquecido guardado en audit/enriched_trades.pkl")

if __name__ == '__main__':
    df_feat = enrich_trades()
    evaluate_subsets(df_feat)
