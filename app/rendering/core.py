"""
Módulo Core de Renderizado (ChartRenderer)
Orquesta la creación de la figura Matplotlib y delega en plotters específicos.
"""

import datetime
import structlog
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.dates import DateFormatter
from pytz import timezone

# Configuración Backend
matplotlib.use('Agg')

# Imports Modulares
from rendering.utils import convert_to_dataframe, candle_check
from rendering.plotters import plot_candlestick, plot_rsi, plot_macd, plot_ichimoku


class ChartRenderer:
    """
    Clase encargada de coordinar la creación de gráficos financieros complejos.
    """

    def __init__(self, indicator_config, timezone_str='UTC'):
        self.logger = structlog.get_logger()
        self.indicator_config = indicator_config
        self.timezone_str = timezone_str

    def create_chart(self, exchange, market_pair, candle_period, candles_data):
        """
        Genera y guarda un gráfico financiero completo.
        """
        now = datetime.datetime.now(timezone(self.timezone_str))
        creation_date = now.strftime("%Y-%m-%d %H:%M:%S")

        df = convert_to_dataframe(candles_data)

        # Configuración Visual
        plt.rc('axes', grid=True)
        plt.rc('grid', color='0.75', linestyle='-', linewidth=0.5)

        # Definición de Ejes
        left, width = 0.1, 0.8
        rect1 = [left, 0.69, width, 0.23] # Velas
        rect2 = [left, 0.51, width, 0.18] # RSI
        rect3 = [left, 0.35, width, 0.16] # MACD
        rect4 = [left, 0.08, width, 0.23] # Ichimoku

        fig = plt.figure(facecolor='white')
        fig.set_size_inches(8, 18, forward=True)
        axescolor = '#f6f6f6'

        ax1 = fig.add_axes(rect1, facecolor=axescolor)
        ax2 = fig.add_axes(rect2, facecolor=axescolor, sharex=ax1)
        ax3 = fig.add_axes(rect3, facecolor=axescolor, sharex=ax1)
        ax4 = fig.add_axes(rect4, facecolor=axescolor)

        # 1. Plot Candles
        candle_pattern = candle_check(df, candle_period, self.indicator_config)
        plot_candlestick(ax1, df, candle_period, candle_pattern)

        # 2. Plot RSI
        plot_rsi(ax2, df)

        # 3. Plot MACD
        plot_macd(ax3, df, candle_period)

        # 4. Plot Ichimoku
        plot_ichimoku(ax4, df, candles_data, candle_period, self.indicator_config)

        # Configuración de Ejes Común
        for ax in ax1, ax2, ax3, ax4:
            if ax != ax3 and ax != ax4:
                for label in ax.get_xticklabels():
                    label.set_visible(False)
            elif ax == ax3 or ax == ax4:
                for label in ax.get_xticklabels():
                    label.set_rotation(30)
                    label.set_horizontalalignment('right')

            ax.xaxis.set_major_locator(mticker.MaxNLocator(10))
            ax.xaxis.set_major_formatter(DateFormatter('%d/%b'))
            ax.xaxis.set_tick_params(which='major', pad=15)

        fig.autofmt_xdate()

        title = '{} {} {} - {}'.format(exchange, market_pair, candle_period, creation_date).upper()
        fig.suptitle(title, fontsize=14)

        market_pair_safe = market_pair.replace('/', '_').lower()
        chart_file = '{}/{}_{}_{}.png'.format('./charts', exchange, market_pair_safe, candle_period)

        plt.savefig(chart_file)
        plt.close(fig)

        return chart_file
