"""
Primitivas del metodo Wyckoff (specs/013-wyckoff-effort-result/).

Ley de Esfuerzo vs. Resultado: el volumen (esfuerzo) y el movimiento de precio
(resultado) deberian ser proporcionales; cuando divergen, es la senal mas objetiva
y directamente calculable del metodo (ver specs/012-wyckoff-fractal-research/research.md).

Mismo patron que DerivedIndicators (app/analyzers/indicators/derived.py): metodos
estaticos, puros, sin estado. IMPORTANTE: estas funciones NO generan alertas ni se
conectan a config.yml -- son primitivas informativas hasta que
specs/015-wyckoff-historical-validation/ demuestre que predicen algo real
(Principio III de la constitucion).
"""
import numpy as np
import pandas as pd
import talib


class WyckoffPrimitives:
    """
    Primitivas del metodo Wyckoff calculables directamente desde OHLCV.

    Todos los metodos son estaticos para uso sin instanciar, igual que DerivedIndicators.
    """

    @staticmethod
    def relative_volume(dataframe: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Volumen actual respecto a su promedio movil (esfuerzo).

        Args:
            dataframe: DataFrame OHLCV con columna 'volume'.
            period: Ventana del promedio movil (default 20).

        Returns:
            pandas.Series: 1.0 = volumen normal, 2.0 = doble del promedio. NaN durante
            el periodo de calentamiento (no hay suficiente historia para el promedio).
        """
        avg_volume = talib.SMA(dataframe['volume'].astype(float).values, timeperiod=period)
        avg_volume = pd.Series(avg_volume, index=dataframe.index)
        volume = dataframe['volume'].astype(float)
        return volume / avg_volume.replace(0, np.nan)

    @staticmethod
    def relative_range(dataframe: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Rango de la vela (true range) respecto a su ATR (resultado).

        Args:
            dataframe: DataFrame OHLCV con columnas 'high', 'low', 'close'.
            period: Periodo del ATR (default 14, el mismo que ya usa el proyecto en
                otros indicadores via talib).

        Returns:
            pandas.Series: 1.0 = rango normal, 2.0 = doble del ATR promedio. NaN
            durante el calentamiento o si el ATR es 0 (dato degenerado/plano).
        """
        high = dataframe['high'].astype(float).values
        low = dataframe['low'].astype(float).values
        close = dataframe['close'].astype(float).values

        atr = talib.ATR(high, low, close, timeperiod=period)
        true_range = talib.TRANGE(high, low, close)

        atr = pd.Series(atr, index=dataframe.index).replace(0, np.nan)
        true_range = pd.Series(true_range, index=dataframe.index)
        return true_range / atr

    @staticmethod
    def effort_result_ratio(dataframe: pd.DataFrame, volume_period: int = 20,
                             range_period: int = 14) -> pd.Series:
        """
        Ratio esfuerzo/resultado: relative_volume / relative_range.

        Alto (>1): mucho volumen para poco movimiento de precio -- posible clímax o
        absorcion. Bajo (<1): poco volumen para mucho movimiento -- posible movimiento
        "delgado"/de baja conviccion.

        Returns:
            pandas.Series: NaN durante el calentamiento de cualquiera de los dos
            componentes, o si relative_range es NaN (ATR=0) -- nunca inf ni excepcion.
        """
        rel_vol = WyckoffPrimitives.relative_volume(dataframe, period=volume_period)
        rel_range = WyckoffPrimitives.relative_range(dataframe, period=range_period)
        return rel_vol / rel_range.replace(0, np.nan)

    @staticmethod
    def is_climax(dataframe: pd.DataFrame, volume_period: int = 20, range_period: int = 14,
                  climax_volume_threshold: float = 2.0,
                  climax_range_threshold: float = 1.0) -> pd.Series:
        """
        Flag de vela "clímax": mucho esfuerzo (volumen), poco resultado (rango) --
        posible absorcion/agotamiento (Selling Climax / Buying Climax en el esquema
        Wyckoff, ver specs/012-.../research.md).

        Args:
            climax_volume_threshold: relative_volume minimo para considerar "mucho esfuerzo".
            climax_range_threshold: relative_range maximo para considerar "poco resultado".

        Returns:
            pandas.Series[bool]: False (no NaN) cuando falta historia -- "aun no sabemos"
            se responde como "no es clímax", nunca como valor faltante.
        """
        rel_vol = WyckoffPrimitives.relative_volume(dataframe, period=volume_period)
        rel_range = WyckoffPrimitives.relative_range(dataframe, period=range_period)
        flag = (rel_vol >= climax_volume_threshold) & (rel_range <= climax_range_threshold)
        return flag.fillna(False)

    @staticmethod
    def is_thin_move(dataframe: pd.DataFrame, volume_period: int = 20, range_period: int = 14,
                      thin_range_threshold: float = 2.0,
                      thin_volume_threshold: float = 1.0) -> pd.Series:
        """
        Flag de vela "delgada": mucho resultado (rango), poco esfuerzo (volumen) --
        movimiento potencialmente insostenible / baja conviccion.

        Returns:
            pandas.Series[bool]: False (no NaN) cuando falta historia, mismo criterio
            que is_climax.
        """
        rel_vol = WyckoffPrimitives.relative_volume(dataframe, period=volume_period)
        rel_range = WyckoffPrimitives.relative_range(dataframe, period=range_period)
        flag = (rel_range >= thin_range_threshold) & (rel_vol <= thin_volume_threshold)
        return flag.fillna(False)
