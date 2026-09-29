"""
Experimentos pendientes (specs/038-experimentos-lab-pendientes). Solo laboratorio, no se opera.
Misma logica de eventos que wyckoff_lab.py (validada contra WyckoffPrimitives); agrega la
profundidad de la barrida y variantes de filtro/salida sobre WyckoffLab_SpringH72_SL10.
"""
import numpy as np
import talib
from pandas import DataFrame

from wyckoff_lab import (CONFIRM_WINDOW, EXTREME_VOLUME, LOOKBACK, VOLUME_PERIOD,
                         WyckoffLab_SpringH72_SL10)


def spring_events_with_depth(df: DataFrame):
    volume = df['volume'].astype(float).values
    avg_vol = talib.SMA(volume, timeperiod=VOLUME_PERIOD)
    with np.errstate(divide='ignore', invalid='ignore'):
        rel_vol = np.where(avg_vol > 0, volume / avg_vol, np.nan)
    lows = df['low'].astype(float).values
    closes = df['close'].astype(float).values
    support = df['low'].astype(float).rolling(LOOKBACK).min().shift(1).values
    n = len(df)
    spring = np.zeros(n, dtype=bool)
    brk_rv = np.full(n, np.nan)
    depth = np.full(n, np.nan)
    for i in range(n):
        level = support[i]
        if np.isnan(level) or not lows[i] < level:
            continue
        for j in range(i + 1, min(i + 1 + CONFIRM_WINDOW, n)):
            if closes[j] > level:
                spring[j] = True
                brk_rv[j] = rel_vol[i]
                depth[j] = (level - lows[i]) / level * 100
                break
    return spring, brk_rv, depth


class ExpBase(WyckoffLab_SpringH72_SL10):
    startup_candle_count = 40

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        spring, rv, depth = spring_events_with_depth(dataframe)
        dataframe['wy_spring'] = spring & (np.nan_to_num(rv) >= EXTREME_VOLUME)
        dataframe['depth'] = depth
        dataframe['chg24h'] = (dataframe['close'] / dataframe['close'].shift(6) - 1.0) * 100
        return dataframe

    extra_filter = None

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cond = dataframe['wy_spring']
        if self.extra_filter is not None:
            cond = cond & self.extra_filter(dataframe)
        dataframe.loc[cond, ['enter_long', 'enter_tag']] = (1, 'spring')
        return dataframe


class Exp_E0_Base(ExpBase):
    """Control: misma logica que la base; debe reproducir 861 / 525 trades."""


class Exp_E1_Sweep10(ExpBase):
    extra_filter = staticmethod(lambda d: d['depth'] >= 1.0)


class Exp_E2_Sweep15(ExpBase):
    extra_filter = staticmethod(lambda d: d['depth'] >= 1.5)


class Exp_E3_Drop24h(ExpBase):
    extra_filter = staticmethod(lambda d: d['chg24h'] <= -8.0)


class Exp_E4_Trailing(ExpBase):
    trailing_stop = True
    trailing_stop_positive = 0.020
    trailing_stop_positive_offset = 0.035
    trailing_only_offset_is_reached = True


class Exp_E5_TP48h(ExpBase):
    hold_hours = 48
    minimal_roi = {"0": 0.06, "1440": 0.04, "2880": 0.0}


class Exp_E6_H48(ExpBase):
    hold_hours = 48
