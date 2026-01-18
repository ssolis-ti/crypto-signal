"""
Módulo de Plotters
Funciones puras para dibujar indicadores y gráficos específicos sobre ejes Matplotlib.
"""

import traceback
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from stockstats import StockDataFrame
from analyzers.indicators import ichimoku

# Importar utilidades
from rendering.utils import EMA, relative_strength

def candlestick_ohlc_draw(ax, quotes, cdl=None, width=0.2, colorup='k', colordown='r', alpha=1.0, ochl=False):
    """Primitiva de dibujo de velas con soporte para patrones coloreados."""
    if isinstance(cdl, pd.DataFrame):
        cdl_pattern = not pd.DataFrame(cdl).empty
    else:
        cdl_pattern = False

    OFFSET = width / 2.0
    colors = ['c', 'm', 'y', 'k', 'b']
    index = 0
    lines = []
    patches = []

    for q in quotes:
        if ochl:
            t, open_p, close_p, high_p, low_p = q[:5]
        else:
            t, open_p, high_p, low_p, close_p = q[:5]
        
        if close_p >= open_p:
            color = colorup
            if cdl_pattern:
                for column in cdl:
                    if cdl[column][index] != 0:
                        color = colors[cdl.columns.get_loc(column)]
                        break
            lower = open_p
            height = close_p - open_p
        else:
            color = colordown
            if cdl_pattern:
                for column in cdl:
                    if cdl[column][index] != 0:
                        color = colors[cdl.columns.get_loc(column)]
                        break
            lower = close_p
            height = open_p - close_p

        vline = Line2D(
            xdata=(t, t), ydata=(low_p, high_p),
            color=color, linewidth=0.5, antialiased=False,
        )

        rect = Rectangle(
            xy=(t - OFFSET, lower),
            width=width, height=height,
            facecolor=color, edgecolor=None, antialiased=False, alpha=1.0
        )

        lines.append(vline)
        patches.append(rect)
        ax.add_line(vline)
        ax.add_patch(rect)
        index += 1

    ax.autoscale_view()
    return lines, patches

def plot_candlestick(ax, df, candle_period, candle_pattern):
    textsize = 11

    ma7 = EMA(df, 7)
    ma25 = EMA(df, 25)
    ma99 = EMA(df, 99)

    if(df['close'].count() > 120):
        df = df.iloc[-120:]
        ma7 = ma7.iloc[-120:]
        ma25 = ma25.iloc[-120:]
        ma99 = ma99.iloc[-120:]
        candle_pattern = candle_pattern.iloc[-120:]

    _time = mdates.date2num(df.index.to_pydatetime())
    min_x = np.nanmin(_time)
    max_x = np.nanmax(_time)

    stick_width = ((max_x - min_x) / _time.size)

    ax.set_ymargin(0.2)
    ax.ticklabel_format(axis='y', style='plain')

    candlestick_ohlc_draw(
        ax, 
        zip(_time, df['open'], df['high'], df['low'], df['close']), 
        cdl=candle_pattern,
        width=stick_width, colorup='olivedrab', colordown='crimson'
    )

    ax.plot(df.index, ma7, color='darkorange', lw=0.8, label='EMA (7)')
    ax.plot(df.index, ma25, color='mediumslateblue', lw=0.8, label='EMA (25)')
    ax.plot(df.index, ma99, color='firebrick', lw=0.8, label='EMA (99)')

    ax.text(0.04, 0.94, 'EMA (7, close)', color='darkorange', transform=ax.transAxes, fontsize=textsize, va='top')
    ax.text(0.24, 0.94, 'EMA (25, close)', color='mediumslateblue', transform=ax.transAxes, fontsize=textsize, va='top')
    ax.text(0.46, 0.94, 'EMA (99, close)', color='firebrick', transform=ax.transAxes, fontsize=textsize, va='top')

def plot_rsi(ax, df):
    textsize = 11
    fillcolor = 'darkmagenta'
    rsi = relative_strength(df["close"])

    if(df['close'].count() > 120):
        df = df.iloc[-120:]
        rsi = rsi[-120:]

    ax.plot(df.index, rsi, color=fillcolor, linewidth=0.5)
    ax.axhline(70, color='darkmagenta', linestyle='dashed', alpha=0.6)
    ax.axhline(30, color='darkmagenta', linestyle='dashed', alpha=0.6)
    ax.fill_between(df.index, rsi, 70, where=(rsi >= 70), facecolor=fillcolor, edgecolor=fillcolor)
    ax.fill_between(df.index, rsi, 30, where=(rsi <= 30), facecolor=fillcolor, edgecolor=fillcolor)
    ax.set_ylim(0, 100)
    ax.set_yticks([30, 70])
    ax.text(0.024, 0.94, 'RSI (14)', va='top', transform=ax.transAxes, fontsize=textsize)

def plot_macd(ax, df, candle_period):
    textsize = 11
    df = StockDataFrame.retype(df)
    df['macd'] = df.get('macd')

    if(df['macd'].count() > 120):
        df = df.iloc[-120:]

    min_y = df.macd.min()
    max_y = df.macd.max()
    macd_h = df.macdh * 0.5

    if (macd_h.min() < min_y): min_y = macd_h.min()
    if (macd_h.max() > max_y): max_y = macd_h.max()

    min_y = min_y * 1.2
    max_y = max_y * 1.2

    _time = mdates.date2num(df.index.to_pydatetime())
    min_x = np.nanmin(_time)
    max_x = np.nanmax(_time)
    bar_width = ((max_x - min_x) / _time.size) * 0.8

    ax.bar(x=_time, bottom=[0 for _ in macd_h.index], height=macd_h, width=bar_width, color="red", alpha=0.4)
    ax.plot(_time, df.macd, color='blue', lw=0.6)
    ax.plot(_time, df.macds, color='red', lw=0.6)
    ax.set_ylim((min_y, max_y))

    ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=5, prune='upper'))
    ax.text(0.024, 0.94, 'MACD (12, 26, close, 9)', va='top', transform=ax.transAxes, fontsize=textsize)

def plot_ichimoku(ax, df, historical_data, candle_period, indicator_config):
    indicator_conf = {}
    if 'ichimoku' in indicator_config:
        for config in indicator_config['ichimoku']:
            if config['enabled'] and config['candle_period'] == candle_period:
                indicator_conf = config
                break

    tenkansen_period = indicator_conf.get('tenkansen_period', 20)
    kijunsen_period = indicator_conf.get('kijunsen_period', 60)
    senkou_span_b_period = indicator_conf.get('senkou_span_b_period', 120)

    textsize = 11
    ichimoku_data = ichimoku.Ichimoku().analyze(
        historical_data, tenkansen_period, kijunsen_period, senkou_span_b_period, chart=True
    )

    if(df['close'].count() > 120):
        df = df.iloc[-120:]
        ichimoku_data = ichimoku_data.iloc[-146:]

    _time = mdates.date2num(df.index.to_pydatetime())
    _time2 = mdates.date2num(ichimoku_data.index.to_pydatetime())

    if len(_time) == 0: return # Safety check

    min_x = np.nanmin(_time)
    max_x = np.nanmax(_time)
    stick_width = ((max_x - min_x) / _time.size)

    ax.set_ymargin(0.2)
    ax.ticklabel_format(axis='y', style='plain')

    candlestick_ohlc_draw(
        ax, 
        zip(_time, df['open'], df['high'], df['low'], df['close']),
        width=stick_width, colorup='olivedrab', colordown='crimson'
    )

    ax.plot(_time2, ichimoku_data.kijunsen, color='red', lw=0.6)
    ax.plot(_time2, ichimoku_data.tenkansen, color='blue', lw=0.6)
    ax.plot(_time2, ichimoku_data.leading_span_a, color='darkgreen', lw=0.6, linestyle='dashed')
    ax.plot(_time2, ichimoku_data.leading_span_b, color='darkred', lw=0.6, linestyle='dashed')
    ax.plot(_time2, ichimoku_data.chikou_span, color='purple', lw=0.6)

    ax.fill_between(_time2, ichimoku_data.leading_span_a, ichimoku_data.leading_span_b, 
                    where=ichimoku_data.leading_span_a > ichimoku_data.leading_span_b,
                    facecolor='#008000', interpolate=True, alpha=0.25)
    ax.fill_between(_time2, ichimoku_data.leading_span_a, ichimoku_data.leading_span_b, 
                    where=ichimoku_data.leading_span_b > ichimoku_data.leading_span_a,
                    facecolor='#ff0000', interpolate=True, alpha=0.25)

    ax.text(0.06, 0.94, 'kijunsen', color='red', transform=ax.transAxes, fontsize=textsize, va='top')
    ax.text(0.19, 0.94, 'tenkansen', color='blue', transform=ax.transAxes, fontsize=textsize, va='top')
