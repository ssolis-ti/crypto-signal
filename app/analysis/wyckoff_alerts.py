"""
Alertas Wyckoff en vivo (specs/023-wyckoff-live-alerts/).

Envia una alerta de Telegram cuando la ultima vela de 4h cerrada confirma un
Spring/Upthrust con volumen extremo en la ruptura (>=2.5x el promedio) -- el UNICO
filtro que sobrevivio validacion in-sample/out-of-sample en este proyecto
(specs/017-wyckoff-edge-refinement/). El plan del mensaje sale del backtest en Freqtrade
(specs/032-freqtrade-lab-wyckoff/), que refuto el encuadre "rapido" de 1-2h y el de 14d:

  - Spring: long, mantener ~72h, stop -10% (consistente en 2022-2024 y 2025-2026).
  - Upthrust: solo informativo, perdio en promedio en 2022-2024.

Deliberadamente independiente de SignalEnhancer/SmartNotificationManager (ese
scoring ya se probo, dos veces, que no predice nada -- specs/007, specs/011): esta
alerta se envia directo via Notifier.send_direct_text, nunca sujeta al filtro
detail_min_quality ni al score 0-100.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd
import structlog

from analyzers.utils import IndicatorUtils
from analyzers.indicators.wyckoff import WyckoffPrimitives
from analysis.twitter_sentiment import TwitterSentimentAnalyzer

DEFAULT_RECORD_PATH = 'agent_state/rumor_radar.jsonl'
DEFAULT_RADAR_MIN_RATIO = 2.0
RADAR_MAX_FAILURES = 3
SHALLOW_SWEEP_PCT = 1.0
CLUSTER_STRONG = 5
STALE_ALERT_SECONDS = 2 * 3600
CANDLE_SECONDS = 4 * 3600

VALIDATED_CANDLE_PERIOD = '4h'
LOOKBACK = 20
CONFIRM_WINDOW = 3
EXTREME_VOLUME_THRESHOLD = 2.5
MAX_DEDUP_SIGNATURES = 500

# Numeros del backtest en Freqtrade (specs/032-freqtrade-lab-wyckoff/), auditados contra los
# trades crudos (QA de resultados, 2026-09-29): Binance futuros, 29 pares, comisiones y funding
# reales, IS 2022-2024 / OOS 2025-2026, sin sesgo de lookahead. Cada cifra dice de QUE formato
# sale: "todas las senales" (sin tope de posiciones) NO es lo mismo que "3 posiciones de 30 USDT".
SPRING_PLAN = (
    "📈 <b>Plan: long, mantener ~3 dias (72h), stop -10% en precio (mark)</b>\n"
    "Tomando TODAS las señales a 1x (con comisiones y funding): acierto 56-58%, "
    "ganancia media +1.5% a +1.8% por trade.\n"
    "⚠️ Con 100 USDT y solo 3 posiciones de 30 rinde menos: ~+1% medio y 50-56% de acierto, "
    "porque cuando saltan varias señales juntas quedan afuera las mejores. "
    "Caida maxima vista 19-27% (en una mala racha puede ser mayor); "
    "44-50% de los trades pierde y hubo rachas de 6 a 10 perdidas seguidas.\n"
    "⚠️ Con 3x no es prudente para 100 USDT (caida maxima hasta 46%).\n"
    "⚠️ Operar de 1-2h NO funciona: 44-49% de acierto y pierde con comisiones"
)
UPTHRUST_PLAN = (
    "⚠️ <b>Short con edge debil</b>\n"
    "Acierta la caida 57-61% de las veces, pero en 2022-24 los rebotes (squeezes) se comieron "
    "la ganancia; en 2025-26 fue positivo (+0.6% por trade a 72h).\n"
    "Si lo operas: tamaño chico y stop ajustado."
)


class WyckoffAlerter:
    """
    Detecta eventos Spring/Upthrust validados sobre el OHLCV de 4h que Behaviour ya
    obtiene cada ciclo, y envia una alerta directa por Telegram -- sin recalcular ni
    pedir datos nuevos al exchange (Principio I: solo lectura).
    """

    def __init__(self, notifier, enabled: bool = False, twitter_sentiment_enabled: bool = False,
                 rumor_radar_enabled: bool = False,
                 radar_min_ratio: float = DEFAULT_RADAR_MIN_RATIO,
                 record_path: Optional[str] = None):
        self.logger = structlog.get_logger()
        self.notifier = notifier
        self.enabled = enabled
        # dict (no set): conserva el orden de insercion, asi el prune descarta lo mas viejo.
        self._alerted_signatures: Dict[str, None] = {}
        self._radar_failures: Dict[str, int] = {}
        self._concurrent: Dict[tuple, int] = {}
        self.twitter_sentiment = TwitterSentimentAnalyzer(enabled=twitter_sentiment_enabled)
        # El radar necesita Twitter: sin el no hay nada que cruzar con el volumen.
        self.rumor_radar_enabled = rumor_radar_enabled and twitter_sentiment_enabled
        self.radar_min_ratio = radar_min_ratio
        self.record_path = record_path
        self._load_signatures_from_record()

    def _load_signatures_from_record(self) -> None:
        """
        La deduplicacion vive en memoria y se perdia en cada reinicio (redeploy, PC apagada de
        noche): la misma vela volvia a alertar. Se reconstruye desde el registro persistente.
        """
        if not self.record_path or not os.path.exists(self.record_path):
            return
        try:
            with open(self.record_path, encoding='utf-8') as f:
                lines = f.readlines()[-MAX_DEDUP_SIGNATURES:]
            for line in lines:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                kind = 'radar' if event.get('type') == 'radar' else event.get('direction')
                if kind and event.get('candle') and event.get('pair'):
                    self._remember(f"{event.get('exchange')}:{event['pair']}:{kind}:{event['candle']}")
        except Exception as e:
            self.logger.error(f"[WYCKOFF] No se pudo cargar el registro de alertas: {e}")

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

    def check_cycle(self, exchange: str, pairs_data: Dict[str, list]) -> None:
        """
        Revisa todos los pares de un exchange en un ciclo. Primero cuenta cuantos pares tienen
        evento en la MISMA vela: el edge viene de capitulaciones de todo el mercado (backtest:
        springs aislados sin ventaja clara; 5+ pares a la vez, +2.5% medio), y ese dato solo se
        conoce mirando todos los pares antes de avisar.
        """
        if not self.enabled:
            return
        self._concurrent = self._count_concurrent(exchange, pairs_data)
        for market_pair, historical_data in pairs_data.items():
            try:
                self.check_and_alert(exchange, market_pair, VALIDATED_CANDLE_PERIOD, historical_data)
            except Exception as e:  # un par que falla nunca debe impedir revisar los demas
                self.logger.error(f"[WYCKOFF] Exception checking pair {market_pair} on {exchange}: {e}")

    def _count_concurrent(self, exchange: str, pairs_data: Dict[str, list]) -> Dict[tuple, int]:
        counts: Dict[tuple, int] = {}
        min_history = LOOKBACK + CONFIRM_WINDOW + 5
        for market_pair, historical_data in pairs_data.items():
            if not historical_data or len(historical_data) < min_history:
                continue
            try:
                df = IndicatorUtils().convert_to_dataframe(historical_data)
                event = self._detect_event(df)
            except Exception as e:
                self.logger.error(f"[WYCKOFF] No se pudo contar eventos de {market_pair}: {e}")
                continue
            if event is not None:
                key = (exchange, event[0], event[2].isoformat())
                counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def _detect_event(df):
        """(direccion, volumen_ruptura, timestamp) de la ultima vela cerrada, o None si no hay evento."""
        springs = WyckoffPrimitives.detect_springs(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)
        upthrusts = WyckoffPrimitives.detect_upthrusts(df, lookback=LOOKBACK, confirm_window=CONFIRM_WINDOW)

        i = len(df) - 1  # ultima vela -- ya cerrada, DataManager.get_ohlcv garantiza no-repaint
        timestamp = df.index[i]

        spring_rv = springs['break_relative_volume'].iloc[i]
        upthrust_rv = upthrusts['break_relative_volume'].iloc[i]

        if bool(springs['is_spring'].iloc[i]) and not pd.isna(spring_rv) and spring_rv >= EXTREME_VOLUME_THRESHOLD:
            return 'hot', spring_rv, timestamp
        if bool(upthrusts['is_upthrust'].iloc[i]) and not pd.isna(upthrust_rv) and upthrust_rv >= EXTREME_VOLUME_THRESHOLD:
            return 'cold', upthrust_rv, timestamp
        return None

    @staticmethod
    def _sweep_depth(df, direction: str) -> Optional[float]:
        """
        % que la vela de ruptura penetro el soporte (spring) o la resistencia (upthrust). Misma
        semantica que la deteccion: la ultima vela de ruptura cuyo primer regreso al rango es la
        vela de confirmacion.
        """
        n = len(df)
        i = n - 1
        ranges = WyckoffPrimitives.detect_trading_range(df, lookback=LOOKBACK)
        level_col = 'support' if direction == 'hot' else 'resistance'
        levels = ranges[level_col].values
        lows = df['low'].astype(float).values
        highs = df['high'].astype(float).values
        closes = df['close'].astype(float).values
        depth = None
        for i0 in range(max(0, i - CONFIRM_WINDOW), i):
            level = levels[i0]
            if pd.isna(level) or level == 0:
                continue
            broke = lows[i0] < level if direction == 'hot' else highs[i0] > level
            if not broke:
                continue
            first_return = None
            for j in range(i0 + 1, min(i0 + 1 + CONFIRM_WINDOW, n)):
                if (closes[j] > level) if direction == 'hot' else (closes[j] < level):
                    first_return = j
                    break
            if first_return == i:
                depth = abs(level - (lows[i0] if direction == 'hot' else highs[i0])) / level * 100
        return depth

    def _check_and_alert_unsafe(self, exchange: str, market_pair: str, historical_data) -> None:
        df = IndicatorUtils().convert_to_dataframe(historical_data)
        event = self._detect_event(df)
        timestamp = df.index[len(df) - 1]

        if event is None:
            if self.rumor_radar_enabled:
                self._check_rumor_radar(exchange, market_pair, df, timestamp)
            return

        direction, break_relative_volume, timestamp = event
        signature = f"{exchange}:{market_pair}:{direction}:{timestamp.isoformat()}"
        if signature in self._alerted_signatures:
            return

        try:
            sweep_depth = self._sweep_depth(df, direction)
        except Exception as e:
            self.logger.error(f"[WYCKOFF] No se pudo medir la barrida de {market_pair}: {e}")
            sweep_depth = None
        concurrent = self._concurrent.get((exchange, direction, timestamp.isoformat()))

        self._send_alert(exchange, market_pair, direction, break_relative_volume, timestamp,
                         change_24h=self._change_24h(df), sweep_depth=sweep_depth,
                         concurrent=concurrent)
        self._remember(signature)

    def _check_rumor_radar(self, exchange: str, market_pair: str, df, timestamp) -> None:
        """
        Radar volumen + rumor (specs/033-rumor-radar/): vela de 4h cerrada con volumen
        extremo SIN evento Wyckoff -> se mira si las menciones en Twitter se aceleran.
        No validado: aviso para mirar el grafico, no una entrada.
        """
        rel_vol = WyckoffPrimitives.relative_volume(df).iloc[-1]
        if pd.isna(rel_vol) or rel_vol < EXTREME_VOLUME_THRESHOLD:
            return

        # El ciclo corre cada 5 min y ve la misma vela ~48 veces: se marca al obtener respuesta.
        # Si Twitter falla se reintenta el ciclo siguiente, hasta RADAR_MAX_FAILURES veces.
        signature = f"{exchange}:{market_pair}:radar:{timestamp.isoformat()}"
        if signature in self._alerted_signatures:
            return

        ticker = market_pair.split('/')[0]
        velocity = self.twitter_sentiment.mention_velocity(ticker)
        if velocity is None:
            failures = self._radar_failures.get(signature, 0) + 1
            self._radar_failures[signature] = failures
            if failures >= RADAR_MAX_FAILURES:
                self._remember(signature)
                self._radar_failures.pop(signature, None)
            return
        self._radar_failures.pop(signature, None)
        self._remember(signature)

        last = df.iloc[-1]
        candle_change = (last['close'] - last['open']) / last['open'] * 100 if last['open'] else 0.0
        ratio = velocity.get('ratio')
        triggered = ratio is not None and ratio >= self.radar_min_ratio

        twitter_result = None
        if triggered:
            twitter_result = self.twitter_sentiment.analyze(ticker, 'radar', velocity=velocity)
            self._send_radar_alert(exchange, market_pair, rel_vol, candle_change, twitter_result,
                                   change_24h=self._change_24h(df), timestamp=timestamp)

        self._record({
            'type': 'radar', 'exchange': exchange, 'pair': market_pair,
            'candle': timestamp.isoformat(), 'relative_volume': round(float(rel_vol), 2),
            'candle_change_pct': round(float(candle_change), 2),
            'mentions_now': velocity.get('current'), 'mentions_7d_ago': velocity.get('baseline'),
            'ratio': ratio, 'max_views': velocity.get('max_views'), 'alert_sent': triggered,
            'sentiment': (twitter_result or {}).get('sentiment_extreme'),
        })

    def _send_radar_alert(self, exchange: str, market_pair: str, rel_vol: float,
                          candle_change: float, twitter_result,
                          change_24h: Optional[float] = None, timestamp=None) -> None:
        color = "verde" if candle_change >= 0 else "roja"
        change_line = f" | 24h: {change_24h:+.1f}%" if change_24h is not None else ""
        message = (
            f"🛰️ <b>RADAR VOLUMEN + RUMOR</b> (sin dirección)\n"
            f"{self._stale_notice(timestamp)}"
            f"<b>{market_pair}</b> | {exchange} | 4h{change_line}\n"
            f"Volumen: {rel_vol:.1f}x el promedio | vela {color} {candle_change:+.1f}%\n\n"
            f"{TwitterSentimentAnalyzer.format_section(twitter_result)}\n\n"
            f"⚠️ <i>Señal NO validada (specs/033): no es el edge Wyckoff. "
            f"Aviso para mirar el gráfico, no una entrada automática.</i>"
        )
        self.notifier.send_direct_text(message)
        self.logger.info(f"[RADAR] Alert sent: {market_pair} (rel_vol={rel_vol:.2f}x)")

    def _record(self, event: dict) -> None:
        """Registro para validar despues con datos reales hacia adelante. Nunca rompe el ciclo."""
        if not self.record_path:
            return
        try:
            event = {'recorded_at': datetime.now(timezone.utc).isoformat(), **event}
            directory = os.path.dirname(self.record_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.record_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, default=str) + '\n')
        except Exception as e:
            self.logger.error(f"[RADAR] No se pudo registrar el evento: {e}")

    @staticmethod
    def _change_24h(df) -> Optional[float]:
        """Cambio % de las ultimas 6 velas de 4h cerradas (24h)."""
        if len(df) < 7:
            return None
        before = df['close'].iloc[-7]
        return (df['close'].iloc[-1] - before) / before * 100 if before else None

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    def _stale_notice(self, timestamp) -> str:
        """Aviso si la vela cerro hace mas de 2h (p. ej. la PC estuvo apagada): el precio ya pudo correr."""
        if timestamp is None:
            return ""
        elapsed = (self._now_utc() - (timestamp + pd.Timedelta(seconds=CANDLE_SECONDS))).total_seconds()
        if elapsed <= STALE_ALERT_SECONDS:
            return ""
        return f"⏱️ <b>ALERTA RETARDADA</b>: la vela cerró hace {elapsed / 3600:.1f} h; revisá si el precio ya se movió\n"

    @staticmethod
    def _quality_lines(direction: str, sweep_depth: Optional[float], concurrent: Optional[int]) -> str:
        """
        Contexto de la senal. Son HIPOTESIS del backtest (auditoria de resultados, 2026-09-29),
        aun sin confirmar en vivo: se muestran, no filtran ninguna alerta (Principio III). Las
        cifras historicas solo existen para el spring; el upthrust muestra el dato sin cifras.
        """
        lines = []
        if sweep_depth is not None:
            line = f"Barrida bajo el nivel: {sweep_depth:.1f}%"
            if direction == 'hot' and sweep_depth < SHALLOW_SWEEP_PCT:
                line += " ⚠️ superficial: en el backtest las de menos de 1% no rindieron (media -0.1%)"
            lines.append(line)
        if concurrent is not None:
            line = f"Pares con evento en esta misma vela: {concurrent}"
            if direction == 'hot':
                if concurrent <= 1:
                    line += " ⚠️ aislado: en el backtest sin ventaja clara (media ~+0.3%)"
                elif concurrent >= CLUSTER_STRONG:
                    line += " (backtest con 5+ pares: media ~+2.5%)"
            lines.append(line)
        if not lines:
            return ""
        return "\n".join(lines) + "\n<i>Hipotesis del backtest, aun sin confirmar en vivo.</i>\n"

    def _send_alert(self, exchange: str, market_pair: str, direction: str,
                     break_relative_volume: float, timestamp=None,
                     change_24h: Optional[float] = None, sweep_depth: Optional[float] = None,
                     concurrent: Optional[int] = None) -> None:
        if direction == 'hot':
            headline = "🟢 <b>ALCISTA — posible subida</b>"
            label = "Wyckoff Spring: rompio el soporte y volvio a entrar (trampa bajista)"
        else:
            headline = "🔴 <b>BAJISTA — posible caida</b>"
            label = "Wyckoff Upthrust: rompio la resistencia y volvio a caer (trampa alcista)"

        plan = SPRING_PLAN if direction == 'hot' else UPTHRUST_PLAN
        change_line = f" | 24h: {change_24h:+.1f}%" if change_24h is not None else ""
        message = (
            f"{headline}\n"
            f"{self._stale_notice(timestamp)}"
            f"<b>{market_pair}</b> | {exchange} | 4h{change_line}\n"
            f"{label}\n"
            f"Volumen en la ruptura: {break_relative_volume:.1f}x el promedio\n"
            f"{self._quality_lines(direction, sweep_depth, concurrent)}\n"
            f"{plan}\n\n"
            f"<i>Backtest Freqtrade 2022-2026 (specs/032-freqtrade-lab-wyckoff/). "
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
        self._record({
            'type': 'wyckoff', 'direction': direction, 'exchange': exchange, 'pair': market_pair,
            'candle': timestamp.isoformat() if timestamp is not None else None,
            'relative_volume': round(float(break_relative_volume), 2),
            'sweep_depth_pct': None if sweep_depth is None else round(float(sweep_depth), 3),
            'concurrent_pairs': concurrent,
            'change_24h_pct': None if change_24h is None else round(float(change_24h), 2),
            'mentions_now': (twitter_result or {}).get('current'),
            'mentions_7d_ago': (twitter_result or {}).get('baseline'),
            'ratio': (twitter_result or {}).get('ratio'),
            'sentiment': (twitter_result or {}).get('sentiment_extreme'),
        })

    def _remember(self, signature: str) -> None:
        self._alerted_signatures[signature] = None
        self._prune_signatures()

    def _prune_signatures(self, max_size: int = MAX_DEDUP_SIGNATURES) -> None:
        # Descarta las mas antiguas (orden de insercion), nunca las recientes.
        while len(self._alerted_signatures) > max_size:
            del self._alerted_signatures[next(iter(self._alerted_signatures))]
