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

        dataframe = pandas.DataFrame(historical_data)
        dataframe.transpose()

        dataframe.columns = ['timestamp', 'open',
                             'high', 'low', 'close', 'volume']
        dataframe['datetime'] = pandas.to_datetime(
            dataframe['timestamp'], unit='ms', utc=True
        )

        dataframe.set_index('datetime', inplace=True, drop=True)
        dataframe.drop('timestamp', axis=1, inplace=True)

        return dataframe
