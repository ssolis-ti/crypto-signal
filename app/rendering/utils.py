"""
Módulo de Utilidades de Renderizado
Contiene funciones matemáticas, conversión de datos y lógica de verificación de patrones.
"""

import datetime
import sys
import pandas as pd
import numpy as np
import talib
import structlog
from analyzers.indicators import candle_recognition, ichimoku

logger = structlog.get_logger()

def convert_to_dataframe(historical_data):
    """Convierte datos OHLCV crudos a un DataFrame de Pandas."""
    dataframe = pd.DataFrame(historical_data)
    dataframe.transpose()
    dataframe.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    dataframe['timestamp'] = dataframe['timestamp'].apply(
        lambda x: datetime.datetime.fromtimestamp(x / 1000.0)
    )
    dataframe.set_index('timestamp', inplace=True, drop=False)
    return dataframe

def relative_strength(prices, n=14):
    """Calcula el Relative Strength (parte del RSI)."""
    deltas = np.diff(prices)
    seed = deltas[:n + 1]
    up = seed[seed >= 0].sum() / n
    down = -seed[seed < 0].sum() / n
    rs = up / down
    rsi = np.zeros_like(prices)
    rsi[:n] = 100. - 100. / (1. + rs)

    for i in range(n, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up * (n - 1) + upval) / n
        down = (down * (n - 1) + downval) / n
        rs = up / down
        rsi[i] = 100. - 100. / (1. + rs)

    return rsi

def EMA(df, n, field='close'):
    """Calcula la Media Móvil Exponencial usando TA-Lib."""
    return pd.Series(
        talib.EMA(df[field].astype('f8').values, n), 
        name='EMA_' + field.upper() + '_' + str(n), 
        index=df.index
    )

def candle_check(df, candle_period, indicator_config):
    """Verifica patrones de velas configurados."""
    try:
        indicator_conf = {}

        if 'candle_recognition' in indicator_config:
            for config in indicator_config['candle_recognition']:
                if config['enabled'] and config['candle_period'] == candle_period and config['chart']:
                    indicator_conf = config
                    break

        if bool(indicator_conf):
            signal = indicator_conf['signal']
            notification = indicator_conf.get('notification', 'hot')
            candle_check_val = indicator_conf.get('candle_check', 1)
            hot_thresh = indicator_conf.get('hot', 0)
            cold_thresh = indicator_conf.get('cold', 0)

            historical_data = df
            cdl = candle_recognition.Candle_recognition()
            candle_pattern = cdl.analyze(
                historical_data, signal, notification, candle_check_val, hot_thresh, cold_thresh)
            candle_pattern = candle_pattern.drop(['is_hot', 'is_cold'], axis=1)
        else:
            candle_pattern = pd.DataFrame()

    except Exception:
        logger.info(
            'error in indicator config for candle pattern: {}'.format(sys.exc_info()[0]))
        candle_pattern = pd.DataFrame()

    return candle_pattern
