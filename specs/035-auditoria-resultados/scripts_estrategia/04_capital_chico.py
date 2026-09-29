"""
audit/04_capital_chico.py
Simulador de cartera para el operador con 100 USDT, max 3 posiciones de 30 USDT (futuros Binance).
Resuelve el problema de los racimos (clusters) de senales correlacionadas.

Reglas de SELECCION testeadas cuando hay mas senales que slots disponibles:
1. Whitelist baseline (orden estatico de config, replica Freqtrade default)
2. Mayor volumen relativo de ruptura (spring_rv desc)
3. Mayor caida previa 24h (chg24h asc - capitulacion)
4. Mayor caida previa 7d (chg7d asc - capitulacion semanal)
5. Mayor volatilidad previa (atr_pct desc)
6. Menor volatilidad previa (atr_pct asc)
7. Filtro de Regimen BTC: solo tomar senales si BTC > EMA200 diaria (o priorizarlas)

Reglas de TAMANO / GESTION DE CAPITAL:
A. Fijo 30 USDT (1x, sin interes compuesto)
B. Proporcional 30% del equity actual (interes compuesto)
C. Apalancamiento segun volatilidad (1.5x si ATR < 4%, 1x si ATR >= 4%)

Reporta en IS y OOS:
- Saldo final (inicia con 100 USDT)
- Retorno total (%)
- Tasa de acierto (win%)
- Total trades ejecutados
- Max Drawdown (%)
- Ratio Retorno / Drawdown
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
FEE = 0.0005 # 0.05% taker

WHITELIST = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT", "ADA/USDT:USDT",
    "DOGE/USDT:USDT", "AVAX/USDT:USDT", "DOT/USDT:USDT", "LINK/USDT:USDT", "LTC/USDT:USDT",
    "ATOM/USDT:USDT", "NEAR/USDT:USDT", "UNI/USDT:USDT", "AAVE/USDT:USDT", "FIL/USDT:USDT",
    "ETC/USDT:USDT", "TRX/USDT:USDT", "XLM/USDT:USDT", "ALGO/USDT:USDT", "SAND/USDT:USDT",
    "MANA/USDT:USDT", "AXS/USDT:USDT", "GALA/USDT:USDT", "EOS/USDT:USDT", "BCH/USDT:USDT",
    "ICP/USDT:USDT", "CRV/USDT:USDT", "CHZ/USDT:USDT", "DYDX/USDT:USDT", "APE/USDT:USDT"
]
WHITELIST_RANK = {p: i for i, p in enumerate(WHITELIST)}

def get_enriched_signals():
    # Cargar dataframe enriquecido generado en script 02
    df = pd.read_pickle('audit/enriched_trades.pkl')
    # Agregar whitelist rank
    df['wl_rank'] = df['pair'].map(lambda p: WHITELIST_RANK.get(p, 999))
    return df

def simulate_portfolio(df_signals, selection_key, ascending=True, btc_filter=False,
                       sizing='fixed_30', lev_mode='1x', stop_pct=0.10):
    # df_signals contiene todas las senales detectadas
    # Ordenamos cronologicamente por open_date
    signals = df_signals.copy()
    
    if btc_filter:
        signals = signals[signals['btc_bull'] == True].copy()

    # Agrupar senales por vela de apertura
    grouped = signals.groupby('open_date')

    # Estado de la cartera
    equity = 100.0
    cash = 100.0
    open_positions = [] # lista de dicts: pair, entry_date, exit_date, stake, ret, pnl
    trade_history = []
    equity_curve = [(signals['open_date'].min(), equity)]

    # Obtener todas las marcas de tiempo unicas ordenadas
    all_dates = sorted(signals['open_date'].unique())

    # Para simular paso a paso en el tiempo:
    # Usaremos una cola de eventos en el tiempo
    for current_date in all_dates:
        # 1. Cerrar posiciones que hayan vencido en o antes de current_date
        still_open = []
        for pos in open_positions:
            if pos['exit_date'] <= current_date:
                # La posicion cerro
                cash += pos['stake'] + pos['pnl']
                equity += pos['pnl']
                trade_history.append(pos)
                equity_curve.append((pos['exit_date'], equity))
            else:
                still_open.append(pos)
        open_positions = still_open

        # 2. Revisar senales disponibles en current_date
        current_signals = grouped.get_group(current_date)
        # Excluir pares que ya estan en posicion abierta
        open_pairs = set(p['pair'] for p in open_positions)
        available_signals = current_signals[~current_signals['pair'].isin(open_pairs)].copy()

        slots_available = 3 - len(open_positions)
        if slots_available > 0 and len(available_signals) > 0:
            # Ordenar candidatos segun selection_key
            if selection_key == 'whitelist':
                available_signals = available_signals.sort_values('wl_rank', ascending=True)
            else:
                available_signals = available_signals.sort_values(selection_key, ascending=ascending)

            selected = available_signals.head(slots_available)

            for _, sig in selected.iterrows():
                # Calcular tamano de posicion y apalancamiento
                if sizing == 'fixed_30':
                    stake = 30.0
                elif sizing == 'compound_30pct':
                    stake = (equity / 3.0) # 33% del equity
                else:
                    stake = 30.0

                if cash < stake:
                    # No hay cash suficiente
                    stake = max(cash, 0.0)
                if stake <= 1.0:
                    continue

                if lev_mode == '1x':
                    lev = 1.0
                elif lev_mode == 'vol_dynamic':
                    # Si volatilidad < 3.5%, usar 1.5x; si < 2.5%, usar 2x; si alta, 1x
                    atr = sig['atr_pct']
                    if atr < 2.5:
                        lev = 2.0
                    elif atr < 3.8:
                        lev = 1.5
                    else:
                        lev = 1.0
                else:
                    lev = 1.0

                # Calcular retorno del trade con stop -10%
                # Usamos profit_ratio enriquecido o verificamos si min_rate toco stop
                raw_ret = sig['profit_ratio'] / 100.0
                # Si min_rate toco stoploss -10%:
                # Nota: WyckoffLab_SpringH72 en enriquecido tiene profit_ratio sin stop
                # Vamos a aplicar la logica de stop -10%:
                # Si el trade original cayo <= -10%, stop loss lo corto en -10% (-0.10 - fees)
                # En df enriquecido, veamos si tenemos profit_ratio
                net_ret = max(raw_ret, -stop_pct) - (2 * FEE) # fees taker

                pnl = stake * net_ret * lev
                cash -= stake

                exit_date = current_date + pd.Timedelta(hours=72)
                open_positions.append({
                    'pair': sig['pair'],
                    'entry_date': current_date,
                    'exit_date': exit_date,
                    'stake': stake,
                    'ret': net_ret * lev,
                    'pnl': pnl,
                    'win': pnl > 0
                })

    # Cerrar posiciones remanentes
    for pos in open_positions:
        cash += pos['stake'] + pos['pnl']
        equity += pos['pnl']
        trade_history.append(pos)
        equity_curve.append((pos['exit_date'], equity))

    # Calcular metricas
    if not trade_history:
        return {'n': 0, 'equity': 100.0, 'ret_pct': 0.0, 'win_pct': 0.0, 'max_dd': 0.0, 'ret_dd': 0.0}

    eq_df = pd.DataFrame(equity_curve, columns=['date', 'equity']).sort_values('date')
    peak = eq_df['equity'].cummax()
    dd = (eq_df['equity'] - peak) / peak
    max_dd = abs(dd.min()) * 100.0

    n_trades = len(trade_history)
    wins = sum(1 for t in trade_history if t['win'])
    win_pct = (wins / n_trades) * 100.0
    final_equity = equity
    total_ret_pct = ((final_equity - 100.0) / 100.0) * 100.0
    ret_dd = total_ret_pct / max_dd if max_dd > 0 else np.nan

    return {
        'n': n_trades,
        'equity': final_equity,
        'ret_pct': total_ret_pct,
        'win_pct': win_pct,
        'max_dd': max_dd,
        'ret_dd': ret_dd
    }

def run_all_simulations():
    df_signals = get_enriched_signals()
    df_is = df_signals[df_signals['dataset'] == 'IS'].copy()
    df_oos = df_signals[df_signals['dataset'] == 'OOS'].copy()

    experiments = [
        ("1. Whitelist (Freqtrade Baseline 1x)", 'whitelist', True, False, 'fixed_30', '1x'),
        ("2. Mayor Volumen Ruptura (RV desc)", 'spring_rv', False, False, 'fixed_30', '1x'),
        ("3. Mayor Caida 24h (chg24h asc)", 'chg24h', True, False, 'fixed_30', '1x'),
        ("4. Mayor Caida 7d (chg7d asc)", 'chg7d', True, False, 'fixed_30', '1x'),
        ("5. Mayor Volatilidad (ATR% desc)", 'atr_pct', False, False, 'fixed_30', '1x'),
        ("6. Menor Volatilidad (ATR% asc)", 'atr_pct', True, False, 'fixed_30', '1x'),
        ("7. Filtro BTC Bull (>EMA200) + Whitelist", 'whitelist', True, True, 'fixed_30', '1x'),
        ("8. Filtro BTC Bull + Mayor Caida 24h", 'chg24h', True, True, 'fixed_30', '1x'),
        ("9. Caida 24h + Apalancamiento Vol (1-2x)", 'chg24h', True, False, 'fixed_30', 'vol_dynamic'),
        ("10. Caida 24h + Interes Compuesto (33%)", 'chg24h', True, False, 'compound_30pct', '1x'),
    ]

    print("\n=======================================================================================================")
    print(" SIMULACION DE CARTERA: OPERADOR CON 100 USDT (3 slots de 30 USDT, Futuros)")
    print("=======================================================================================================")
    print(f"{'Estrategia de Seleccion y Gestion':<40} | {'IS Final':<8} {'IS Ret%':<8} {'IS Win%':<8} {'IS DD%':<8} {'IS Ret/DD':<9} | {'OOS Final':<9} {'OOS Ret%':<9} {'OOS Win%':<9} {'OOS DD%':<8} {'OOS Ret/DD':<9}")
    print("-" * 135)

    for name, key, asc, btc_f, sz, lev in experiments:
        res_is = simulate_portfolio(df_is, key, ascending=asc, btc_filter=btc_f, sizing=sz, lev_mode=lev)
        res_oos = simulate_portfolio(df_oos, key, ascending=asc, btc_filter=btc_f, sizing=sz, lev_mode=lev)

        print(f"{name:<40} | ${res_is['equity']:<7.1f} {res_is['ret_pct']:+6.1f}%  {res_is['win_pct']:5.1f}%   {res_is['max_dd']:5.1f}%  {res_is['ret_dd']:8.2f} | "
              f"${res_oos['equity']:<8.1f} {res_oos['ret_pct']:+7.1f}%  {res_oos['win_pct']:5.1f}%   {res_oos['max_dd']:5.1f}%  {res_oos['ret_dd']:8.2f}")

if __name__ == '__main__':
    run_all_simulations()
