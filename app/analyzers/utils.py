""" Utilities for technical indicators
"""

import math

import pandas
import structlog


class IndicatorUtils():
    """ Utilities for technical indicators
    """

    def __init__(self):
        self.logger = structlog.get_logger()

    def convert_to_dataframe(self, historical_data):
        """Converts historical data matrix to a pandas dataframe.

        Args:
            historical_data (list): A matrix of historical OHCLV data.

        Returns:
            pandas.DataFrame: Contains the historical data in a pandas dataframe, indexed by a
                UTC-aware datetime built directly from each candle's epoch-millisecond timestamp
                (specs/002-utc-internal-time/) — independent of the host's system timezone/locale,
                unlike a datetime.fromtimestamp()/strftime() round trip.
        """

        cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not historical_data:
            empty_df = pandas.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            empty_df.index = pandas.DatetimeIndex([], tz='UTC', name='datetime')
            return empty_df

        dataframe = pandas.DataFrame(historical_data)

        # Si vienen mas columnas que las esperadas, truncar a las primeras 6
        if dataframe.shape[1] >= 6:
            dataframe = dataframe.iloc[:, :6]
        elif dataframe.shape[1] < 6:
            raise ValueError(f"Historical data must have at least 6 columns, got {dataframe.shape[1]}")

        dataframe.columns = cols

        # Asegurar coercion numerica de timestamp para evitar overflow con strings
        timestamps = pandas.to_numeric(dataframe['timestamp'], errors='coerce')
        dataframe['datetime'] = pandas.to_datetime(
            timestamps, unit='ms', utc=True
        )

        # Coercion numerica de columnas de precio y volumen
        for col in ['open', 'high', 'low', 'close', 'volume']:
            dataframe[col] = pandas.to_numeric(dataframe[col], errors='coerce')

        dataframe.set_index('datetime', inplace=True, drop=True)
        dataframe.drop('timestamp', axis=1, inplace=True)

        return dataframe
