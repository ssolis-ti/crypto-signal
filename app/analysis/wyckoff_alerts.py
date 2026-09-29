"""
Alertas Wyckoff en vivo (specs/023-wyckoff-live-alerts/).

Envia una alerta de Telegram cuando la ultima vela de 4h cerrada confirma un
Spring/Upthrust con volumen extremo en la ruptura (>=2.5x el promedio) -- el UNICO
filtro que sobrevivio validacion in-sample/out-of-sample en este proyecto
(specs/017-wyckoff-edge-refinement/). El mensaje incluye ambos encuadres, con los
numeros reales de la validacion (specs/017/018), tal como decidio el operador:

  - "Rapida" (1-2h): mayor probabilidad, movimiento chico.
  - "Sostenida" (hasta 14d): mas magnitud, con aviso explicito de riesgo de drawdown.

Deliberadamente independiente de SignalEnhancer/SmartNotificationManager (ese
scoring ya se probo, dos veces, que no predice nada -- specs/007, specs/011): esta
alerta se envia directo via Notifier.send_direct_text, nunca sujeta al filtro
detail_min_quality ni al score 0-100.
"""
from typing import Set

import pandas as pd
import structlog

from analyzers.utils import IndicatorUtils
from analyzers.indicators.wyckoff import WyckoffPrimitives
from analysis.twitter_sentiment import TwitterSentimentAnalyzer

VALIDATED_CANDLE_PERIOD = '4h'
LOOKBACK = 20
CONFIRM_WINDOW = 3
EXTREME_VOLUME_THRESHOLD = 2.5
MAX_DEDUP_SIGNATURES = 500

FAST_STATS = "72-78% de acierto historico | movimiento tipico &lt;1% (pensado para apalancamiento)"
SUSTAINED_STATS = (
    "64% de acierto historico a 14 dias | movimiento tipico +2.84%\n"
    "⚠️ ~26% de los casos historicos tuvieron un retroceso adverso ≥10% antes de resolver a favor"
)


class WyckoffAlerter:
    """
    Detecta eventos Spring/Upthrust validados sobre el OHLCV de 4h que Behaviour ya
    obtiene cada ciclo, y envia una alerta directa por Telegram -- sin recalcular ni
    pedir datos nuevos al exchange (Principio I: solo lectura).
    """

    def __init__(self, notifier, enabled: bool = False, twitter_sentiment_enabled: bool = False):
        self.logger = structlog.get_logger()
        self.notifier = notifier
        self.enabled = enabled
        self._alerted_signatures: Set[str] = set()
        self.twitter_sentiment = TwitterSentimentAnalyzer(enabled=twitter_sentiment_enabled)

    def check_and_alert(self, exchange: str, market_pair: str, candle_period: str,
                         historical_data) -> None:
        """
        Revisa un par/periodo especifico. No hace nada si el feature esta deshabilitado,
        el periodo no es el validado (4h), o no hay suficiente historia. Cualquier error
        de deteccion se loguea y se ignora -- nunca debe interrumpir el ciclo de analisis
        (Principio: degradar seguro, nunca romper el pipeline).
        """
        if not self.enabled or candle_period != VALIDATED_CANDLE_PERIOD:
            return

        min_history = LOOKBACK + CONFIRM_WINDOW + 5
        if not historical_data or len(historical_data) < min_history:
            return

        try:
            self._check_and_alert_unsafe(exchange, market_pair, historical_data)
        except Exception as e:
            self.logger.error(f"[WYCKOFF] Error checking {market_pair} on {exchange}: {e}")

    def _check_and_alert_unsafe(self, exchange: str, market_pair: str, historical_data) -> None:
        df = IndicatorUtils().convert_to_dataframe(historical_data)

        springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)

        i = len(df) - 1  # ultima vela -- ya cerrada, DataManager.get_ohlcv garantiza no-repaint
        timestamp = df.index[i]

        direction = None
        break_relative_volume = None

        spring_rv = springs['break_relative_volume'].iloc[i]
        upthrust_rv = upthrusts['break_relative_volume'].iloc[i]

        if bool(springs['is_spring'].iloc[i]) and not pd.isna(spring_rv) and spring_rv >= EXTREME_VOLUME_THRESHOLD:
            direction = 'hot'
            break_relative_volume = spring_rv
        elif bool(upthrusts['is_upthrust'].iloc[i]) and not pd.isna(upthrust_rv) and upthrust_rv >= EXTREME_VOLUME_THRESHOLD:
            direction = 'cold'
            break_relative_volume = upthrust_rv

        if direction is None:
            return

        signature = f"{exchange}:{market_pair}:{direction}:{timestamp.isoformat()}"
        if signature in self._alerted_signatures:
            return

        self._send_alert(exchange, market_pair, direction, break_relative_volume)
        self._alerted_signatures.add(signature)
        self._prune_signatures()

    def _send_alert(self, exchange: str, market_pair: str, direction: str,
                     break_relative_volume: float) -> None:
        if direction == 'hot':
            label, emoji = "SPRING (posible acumulacion)", "🟢"
        else:
            label, emoji = "UPTHRUST (posible distribucion)", "🔴"

        message = (
            f"{emoji} <b>WYCKOFF {label}</b>\n"
            f"{market_pair} | {exchange} | 4h\n"
            f"Volumen en la ruptura: {break_relative_volume:.1f}x el promedio\n\n"
            f"⚡ <b>Rapida (1-2h)</b>\n{FAST_STATS}\n\n"
            f"📈 <b>Sostenida (hasta 14d)</b>\n{SUSTAINED_STATS}\n\n"
            f"<i>Edge validado con holdout in-sample/out-of-sample "
            f"(specs/017-wyckoff-edge-refinement/, specs/018-wyckoff-timing-and-drawdown/). "
            f"No es asesoria financiera.</i>"
        )

        ticker = market_pair.split('/')[0]
        twitter_result = self.twitter_sentiment.analyze(ticker, direction)
        twitter_section = TwitterSentimentAnalyzer.format_section(twitter_result)
        if twitter_section:
            message = f"{message}\n\n{twitter_section}"

        self.notifier.send_direct_text(message)
        self.logger.info(
            f"[WYCKOFF] Alert sent: {market_pair} {direction} "
            f"(break_relative_volume={break_relative_volume:.2f}x)"
        )

    def _prune_signatures(self, max_size: int = MAX_DEDUP_SIGNATURES) -> None:
        if len(self._alerted_signatures) > max_size:
            self._alerted_signatures = set(list(self._alerted_signatures)[-max_size:])
