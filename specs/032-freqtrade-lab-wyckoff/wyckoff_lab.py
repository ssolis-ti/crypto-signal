# pragma pylint: disable=missing-docstring, invalid-name
"""
WYCKOFF_LAB: laboratorio del edge en produccion de crypto-signal (Desktop/deploy,
specs/017, 018, 023 y 032). Solo laboratorio, no se opera.

Replica exacta de WyckoffPrimitives.detect_springs / detect_upthrusts
(deploy/app/analyzers/indicators/wyckoff.py) + el filtro que se usa en vivo:
volumen de la vela de ruptura >= 2.5x su SMA(20). Lookback 20, ventana de confirmacion 3.

La senal cae en la vela de CONFIRMACION (ya cerrada); Freqtrade entra a la apertura de
la vela siguiente, que es cuando llega la alerta de Telegram. Spring -> long, Upthrust -> short.

La base mantiene la posicion `hold_hours` sin stop ni take-profit (mide el edge crudo, con
comisiones y funding reales). Las subclases cambian horizonte, stop y apalancamiento.
"""
from datetime import timedelta

import numpy as np
import talib
from pandas import DataFrame

from freqtrade.strategy import IStrategy

LOOKBACK = 20
CONFIRM_WINDOW = 3
VOLUME_PERIOD = 20
EXTREME_VOLUME = 2.5


def wyckoff_events(df: DataFrame):
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
                    break

    return spring, upthrust, spring_rv, upthrust_rv


class WyckoffLab(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = True
    startup_candle_count = 40
    process_only_new_candles = True
    use_exit_signal = True  # necesario para que Freqtrade llame custom_exit; no hay senales de salida

    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    trailing_stop = False

    hold_hours = 168
    lev = 1.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        spring, upthrust, spring_rv, upthrust_rv = wyckoff_events(dataframe)
        dataframe['wy_spring'] = spring & (np.nan_to_num(spring_rv) >= EXTREME_VOLUME)
        dataframe['wy_upthrust'] = upthrust & (np.nan_to_num(upthrust_rv) >= EXTREME_VOLUME)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Mismo orden de prioridad que WyckoffAlerter: spring primero.
        dataframe.loc[dataframe['wy_spring'], ['enter_long', 'enter_tag']] = (1, 'spring')
        dataframe.loc[dataframe['wy_upthrust'] & ~dataframe['wy_spring'],
                      ['enter_short', 'enter_tag']] = (1, 'upthrust')
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


# ── Horizonte crudo (1x, sin stop): la pregunta "rapida vs sostenida" ──
class WyckoffLab_H1(WyckoffLab):
    hold_hours = 1


class WyckoffLab_H2(WyckoffLab):
    hold_hours = 2


class WyckoffLab_H24(WyckoffLab):
    hold_hours = 24


class WyckoffLab_H72(WyckoffLab):
    hold_hours = 72


class WyckoffLab_H7D(WyckoffLab):
    hold_hours = 168


class WyckoffLab_H14D(WyckoffLab):
    hold_hours = 336


# ── Gestion de riesgo con apalancamiento (stoploss es sobre margen: -0.30 a 3x = -10 % en precio) ──
class WyckoffLab_H7D_SL10(WyckoffLab):
    hold_hours = 168
    stoploss = -0.10


class WyckoffLab_H7D_3X_SL10(WyckoffLab):
    hold_hours = 168
    lev = 3.0
    stoploss = -0.30


# ── Afinado tras la ronda 1: solo springs (long), 72h ──
class WyckoffLab_SpringH72(WyckoffLab):
    hold_hours = 72

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe['wy_spring'], ['enter_long', 'enter_tag']] = (1, 'spring')
        return dataframe


class WyckoffLab_SpringH72_SL10(WyckoffLab_SpringH72):
    stoploss = -0.10


class WyckoffLab_SpringH72_3X_SL10(WyckoffLab_SpringH72):
    lev = 3.0
    stoploss = -0.30
