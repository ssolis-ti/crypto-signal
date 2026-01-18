""" Bollinger Bands Indicator
Migrado a TA-Lib para compatibilidad con Python 3.12+
"""

import numpy
import pandas
import talib

from analyzers.utils import IndicatorUtils


class Bollinger(IndicatorUtils):
    def analyze(self, historical_data, period_count=21):
        """Performs a bollinger band analysis on the historical data

        Args:
            historical_data (list): A matrix of historical OHCLV data.
            period_count (int, optional): Defaults to 21. The number of data points to consider for
                our bollinger bands.

        Returns:
            pandas.DataFrame: A dataframe containing the indicators and hot/cold values.
        """

        dataframe = self.convert_to_dataframe(historical_data)

        bb_columns = {
            'upperband': [numpy.nan] * dataframe.index.shape[0],
            'middleband': [numpy.nan] * dataframe.index.shape[0],
            'lowerband': [numpy.nan] * dataframe.index.shape[0]
        }

        bb_values = pandas.DataFrame(
            bb_columns,
            index=dataframe.index
        )

        close_data = numpy.array(dataframe['close'], dtype=numpy.float64)

        if close_data.size > period_count:
            # TA-Lib devuelve (upperband, middleband, lowerband)
            upper, middle, lower = talib.BBANDS(
                close_data, 
                timeperiod=period_count, 
                nbdevup=2, 
                nbdevdn=2, 
                matype=0  # SMA
            )
            
            bb_values['upperband'] = upper
            bb_values['middleband'] = middle
            bb_values['lowerband'] = lower

        bb_values.dropna(how='all', inplace=True)

        return bb_values
