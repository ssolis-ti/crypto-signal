"""
audit/experimentos_lab.py
Estrategias candidatas del laboratorio Freqtrade para auditar y validar mejoras al edge Wyckoff Spring.
Cada clase es una subclase lista para correr de WyckoffLab o MeanRevLab (audit_data/strategies/).
Modifica solo parametros o logica minima, manteniendo trazabilidad completa.

Verificacion sintactica:
python -c "import ast; ast.parse(open('audit/experimentos_lab.py').read())"
"""

import sys
from datetime import timedelta
import numpy as np
import pandas as pd
from pandas import DataFrame
import talib

try:
    from freqtrade.strategy import IStrategy, informative
except ImportError:
    # Fallback para ejecucion fuera del entorno de Freqtrade
    class IStrategy:
        INTERFACE_VERSION = 3
    def informative(timeframe, asset='', fmt=None, currency=''):
        def decorator(f):
            return f
        return decorator

# Importar constantes y funciones base de wyckoff_lab si esta en el path
LOOKBACK = 20
CONFIRM_WINDOW = 3
VOLUME_PERIOD = 20
EXTREME_VOLUME = 2.5


def wyckoff_events_extended(df: DataFrame):
    volume = df['volume'].astype(float).values
    avg_vol = talib.SMA(volume, timeperiod=VOLUME_PERIOD)
    with np.errstate(divide='ignore', invalid='ignore'):
        rel_vol = np.where(avg_vol > 0, volume / avg_vol, np.nan)

    lows = df['low'].astype(float).values
    highs = df['high'].astype(float).values
    closes = df['close'].astype(float).values
    support = df['low'].astype(float).rolling(LOOKBACK).min().shift(1).values
    resistance = df['high'].astype(float).rolling(LOOKBACK).max().shift(1).values

    n = len(df)
    spring = np.zeros(n, dtype=bool)
    upthrust = np.zeros(n, dtype=bool)
    spring_rv = np.full(n, np.nan)
    upthrust_rv = np.full(n, np.nan)
    spring_penetration = np.full(n, np.nan)

    for flag, brk_rv, levels, is_spring in (
        (spring, spring_rv, support, True),
        (upthrust, upthrust_rv, resistance, False),
    ):
        for i in range(n):
            level = levels[i]
            if np.isnan(level):
                continue
            broke = lows[i] < level if is_spring else highs[i] > level
            if not broke:
                continue
            for j in range(i + 1, min(i + 1 + CONFIRM_WINDOW, n)):
                returned = closes[j] > level if is_spring else closes[j] < level
                if returned:
                    flag[j] = True
                    brk_rv[j] = rel_vol[i]
                    if is_spring:
                        # Profundidad de penetracion: % que cayo bajo soporte
                        spring_penetration[j] = (level - lows[i]) / level
                    break

    return spring, upthrust, spring_rv, upthrust_rv, spring_penetration


class WyckoffLabBase(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = True
    startup_candle_count = 200
    process_only_new_candles = True
    use_exit_signal = True

    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    trailing_stop = False

    hold_hours = 72
    lev = 1.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        spring, upthrust, spring_rv, upthrust_rv, spring_pen = wyckoff_events_extended(dataframe)
        dataframe['wy_spring'] = spring & (np.nan_to_num(spring_rv) >= EXTREME_VOLUME)
        dataframe['wy_upthrust'] = upthrust & (np.nan_to_num(upthrust_rv) >= EXTREME_VOLUME)
        dataframe['spring_rv'] = spring_rv
        dataframe['spring_pen'] = spring_pen

        # ATR 14
        dataframe['atr14'] = talib.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr14'] / dataframe['close']

        # Cambio 24h
        dataframe['chg24h'] = dataframe['close'] / dataframe['close'].shift(6) - 1.0
        # Cambio 7d
        dataframe['chg7d'] = dataframe['close'] / dataframe['close'].shift(42) - 1.0

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe['wy_spring'], ['enter_long', 'enter_tag']] = (1, 'spring')
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if current_time - trade.open_date_utc >= timedelta(hours=self.hold_hours):
            return f'time_{self.hold_hours}h'
        return None

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage,
                 entry_tag, side, **kwargs):
        return min(self.lev, max_leverage)


# ======================================================================================
# EXPERIMENTO 1: WyckoffLab_Spring_Capitulation24h
# Tesis: Confluencia entre Wyckoff Spring (absorcion) y Mean Reversion (caida previa fuerte 24h <= -8%)
# ======================================================================================
class WyckoffLab_Spring_Capitulation24h(WyckoffLabBase):
    """
    Pregunta: ¿Filtrar springs exigiendo una caida previa en 24h <= -8% elimina entradas
    de baja conviccion y duplica el retorno medio por trade manteniendo win-rate > 60%?
    """
    hold_hours = 72
    stoploss = -0.10
    drop_threshold = -0.08

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        entry_cond = dataframe['wy_spring'] & (dataframe['chg24h'] <= self.drop_threshold)
        dataframe.loc[entry_cond, ['enter_long', 'enter_tag']] = (1, 'spring_cap24h')
        return dataframe


# ======================================================================================
# EXPERIMENTO 2: WyckoffLab_Spring_DeepSweep
# Tesis: Barrida de liquidez real (penetracion >= 1.5% bajo soporte).
# Descarta rebotes superficiales (< 1%) que estadisticamente pierden dinero.
# ======================================================================================
class WyckoffLab_Spring_DeepSweep(WyckoffLabBase):
    """
    Pregunta: ¿Exigir una penetracion estructural de al menos 1.5% bajo el soporte previo
    elimina los falsos springs de microestructura y aumenta la robustez del rebote?
    """
    hold_hours = 72
    stoploss = -0.10
    min_penetration = 0.015

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        entry_cond = dataframe['wy_spring'] & (dataframe['spring_pen'] >= self.min_penetration)
        dataframe.loc[entry_cond, ['enter_long', 'enter_tag']] = (1, 'spring_deepsweep')
        return dataframe


# ======================================================================================
# EXPERIMENTO 3: WyckoffLab_Spring_HighATR
# Tesis: El edge se concentra en alta volatilidad (ATR% 14 >= 3.5%).
# Evita activos en baja volatilidad que no generan expansion suficiente.
# ======================================================================================
class WyckoffLab_Spring_HighATR(WyckoffLabBase):
    """
    Pregunta: ¿Restringir los trades a entornos de volatilidad media-alta (ATR% >= 3.5%)
    aumenta el retorno medio a > 3.0% sin reducir drásticamente el tamaño muestral?
    """
    hold_hours = 72
    stoploss = -0.10
    min_atr_pct = 0.035

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        entry_cond = dataframe['wy_spring'] & (dataframe['atr_pct'] >= self.min_atr_pct)
        dataframe.loc[entry_cond, ['enter_long', 'enter_tag']] = (1, 'spring_high_atr')
        return dataframe


# ======================================================================================
# EXPERIMENTO 4: WyckoffLab_Spring_BTCRegime
# Tesis: Filtrar springs al nivel macro de Bitcoin (BTC > EMA200 diaria).
# Evita comprar fondos falsos durante mercados bajistas implacables.
# ======================================================================================
class WyckoffLab_Spring_BTCRegime(WyckoffLabBase):
    """
    Pregunta: ¿Tomar springs únicamente cuando BTC esta por encima de su EMA200 diaria
    reduce el drawdown de la cartera de 100 USDT de 19-27% a < 12%?
    """
    hold_hours = 72
    stoploss = -0.10

    @informative('1d', 'BTC/USDT:USDT')
    def populate_indicators_btc(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema200'] = talib.EMA(dataframe['close'], timeperiod=200)
        dataframe['btc_bull'] = dataframe['close'] > dataframe['ema200']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        btc_bull = dataframe.get('btc_bull_1d', pd.Series(True, index=dataframe.index))
        entry_cond = dataframe['wy_spring'] & btc_bull
        dataframe.loc[entry_cond, ['enter_long', 'enter_tag']] = (1, 'spring_btc_regime')
        return dataframe


# ======================================================================================
# EXPERIMENTO 5: WyckoffLab_Spring_StopATR
# Tesis: Stop adaptativo segun la volatilidad del activo (entry - 2.2 * ATR14).
# Reemplaza el -10% arbitrario para no estrangular monedas volatiles ni regalar margen en calmas.
# ======================================================================================
class WyckoffLab_Spring_StopATR(WyckoffLabBase):
    """
    Pregunta: ¿Un stop adaptativo a 2.2x ATR14 mejora el ratio Retorno/Drawdown
    frente a un stop estático de -10%?
    """
    hold_hours = 72
    stoploss = -0.15 # Stoploss duro de emergencia
    use_custom_stoploss = True
    atr_multiplier = 2.2

    def custom_stoploss(self, pair: str, trade, current_time, current_rate,
                        current_profit: float, **kwargs) -> float:
        # Calcular distancia en porcentaje de 2.2 * ATR14 en la entrada
        # Freqtrade pasa custom_stoploss relativo al current_rate
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        trade_date = trade.open_date_utc
        row = dataframe.loc[dataframe['date'] <= trade_date].iloc[-1]
        atr = row['atr14']
        open_rate = trade.open_rate
        if open_rate > 0 and atr > 0:
            stop_dist = (self.atr_multiplier * atr) / open_rate
            # Limitar entre -5% y -12%
            clamped_dist = min(max(stop_dist, 0.05), 0.12)
            return -clamped_dist
        return -0.10


# ======================================================================================
# EXPERIMENTO 6: WyckoffLab_Spring_TrailingStop
# Tesis: Asegurar ganancias en movimientos explosivos rapidos que se desinflan antes de 72h.
# ======================================================================================
class WyckoffLab_Spring_TrailingStop(WyckoffLabBase):
    """
    Pregunta: ¿Activar un trailing stop (activacion +3.5%, trailing 2.0%) reduce el drawdown
    y mejora el retorno neto al capturar clímax antes de que reviertan a 72h?
    """
    hold_hours = 72
    stoploss = -0.10
    trailing_stop = True
    trailing_stop_positive = 0.020 # Trailing a 2.0%
    trailing_stop_positive_offset = 0.035 # Se activa tras ganar +3.5%
    trailing_only_offset_is_reached = True


# ======================================================================================
# EXPERIMENTO 7: WyckoffLab_Spring_TakeProfit48h
# Tesis: Horizonte optimizado a 48h con salida por ROI acelerada.
# Disminuye el tiempo en riesgo para cuentas chicas y libera slots de capital mas rapido.
# ======================================================================================
class WyckoffLab_Spring_TakeProfit48h(WyckoffLabBase):
    """
    Pregunta: ¿Reducir el horizonte a 48h y agregar un Take-Profit moderado (+5% tras 24h)
    aumenta la rotacion del capital de 100 USDT reduciendo los periodos de estancamiento?
    """
    hold_hours = 48
    stoploss = -0.10
    # ROI: 6% inmediato, 4% a las 24h (1440 min), 0% a las 48h (2880 min)
    minimal_roi = {
        "0": 0.06,
        "1440": 0.04,
        "2880": 0.00
    }


# ======================================================================================
# EXPERIMENTO 8: WyckoffLab_Spring_WeekdayOnly
# Tesis: Eliminar entradas en fines de semana (sabados y domingos UTC).
# La falta de volumen institucional en fin de semana genera trampas y retornos mediocres (+0.20%).
# ======================================================================================
class WyckoffLab_Spring_WeekdayOnly(WyckoffLabBase):
    """
    Pregunta: ¿Excluir senales de fin de semana (sabado/domingo UTC) elimina falsos positivos
    y eleva la calidad media de ejecucion del operador?
    """
    hold_hours = 72
    stoploss = -0.10

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        is_weekday = dataframe['date'].dt.weekday < 5 # Lunes a Viernes
        entry_cond = dataframe['wy_spring'] & is_weekday
        dataframe.loc[entry_cond, ['enter_long', 'enter_tag']] = (1, 'spring_weekday')
        return dataframe
