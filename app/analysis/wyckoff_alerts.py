"""
Alertas Wyckoff en vivo (specs/023-wyckoff-live-alerts/).

La unica alerta de Telegram es el Spring de la ultima vela de 4h cerrada, con
volumen extremo en la ruptura (>=2.5x el promedio) -- el UNICO filtro que sobrevivio
validacion in-sample/out-of-sample en este proyecto (specs/017-wyckoff-edge-refinement/).
El plan del mensaje sale del backtest en Freqtrade (specs/032-freqtrade-lab-wyckoff/),
que refuto el encuadre "rapido" de 1-2h y el de 14d:

  - Spring: long, mantener ~72h, stop -10% (consistente en 2022-2024 y 2025-2026).
    Es la alerta principal: entra al chat y el HTML queda en telegram_sent.jsonl.
  - Upthrust y radar de rumores: se detectan y se registran, no se envian.

Deliberadamente independiente de SignalEnhancer/SmartNotificationManager (ese
scoring ya se probo, dos veces, que no predice nada -- specs/007, specs/011): esta
alerta se envia directo via Notifier.send_direct_text, nunca sujeta al filtro
detail_min_quality ni al score 0-100.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pandas as pd
import structlog

from analyzers.utils import IndicatorUtils
from analyzers.indicators.wyckoff import WyckoffPrimitives
from analysis.alert_text import LOW_LIQUIDITY_USD, WIDE_FRACTION, AlertItem, build_group_buy, build_single_buy
from analysis.market_microstructure import MarketMicrostructure
from analysis.twitter_sentiment import TwitterSentimentAnalyzer

DEFAULT_RECORD_PATH = 'agent_state/rumor_radar.jsonl'
SENT_ARCHIVE_NAME = 'telegram_sent.jsonl'
DEFAULT_RADAR_MIN_RATIO = 2.0
RADAR_MAX_FAILURES = 3
SEND_MAX_FAILURES = 12  # ciclos de 5 min: ~1h reintentando si Telegram no responde
# DEFAULT_WATCHED: universo supuesto si no se conoce (la fraccion de pares con spring se mide contra el universo vigilado;
# el umbral de "capitulacion amplia" (20%) vive en analysis/alert_text.py).
DEFAULT_WATCHED = 30
CANDLE_SECONDS = 4 * 3600
# Springs confirmados mientras el bot estuvo apagado: se avisan hasta 3 velas (12h) despues. Medido en el
# laboratorio (specs/039): cada 4h de demora cuesta ~0.5 pp; a 12h el promedio sigue positivo pero el acierto
# baja a ~47-52%. Mas viejo que eso ya no se avisa.
MAX_LATE_CANDLES = 3

VALIDATED_CANDLE_PERIOD = '4h'
LOOKBACK = 20
CONFIRM_WINDOW = 3
EXTREME_VOLUME_THRESHOLD = 2.5
MAX_DEDUP_SIGNATURES = 500


class WyckoffAlerter:
    """
    Detecta eventos Spring/Upthrust validados sobre el OHLCV de 4h que Behaviour ya
    obtiene cada ciclo, y envia una alerta directa por Telegram -- sin recalcular ni
    pedir datos nuevos al exchange (Principio I: solo lectura).
    """

    def __init__(self, notifier, enabled: bool = False, twitter_sentiment_enabled: bool = False,
                 rumor_radar_enabled: bool = False,
                 radar_min_ratio: float = DEFAULT_RADAR_MIN_RATIO,
                 record_path: Optional[str] = None,
                 microstructure_enabled: bool = False,
                 timezone_str: str = 'UTC', clock_offset_fn=None):
        self.logger = structlog.get_logger()
        self.notifier = notifier
        self.enabled = enabled
        # dict (no set): conserva el orden de insercion, asi el prune descarta lo mas viejo.
        self._alerted_signatures: Dict[str, None] = {}
        self._radar_failures: Dict[str, int] = {}
        self._send_failures: Dict[str, int] = {}
        self._concurrent: Dict[tuple, int] = {}
        self._watched: Optional[int] = None  # pares liquidos del ciclo: denominador del 20%
        self._liquid_watched: Optional[int] = None
        self._apply_breadth_gate = False  # check_cycle lo enciende; check_and_alert no tiene universo
        self.twitter_sentiment = TwitterSentimentAnalyzer(enabled=twitter_sentiment_enabled)
        # El radar necesita Twitter: sin el no hay nada que cruzar con el volumen.
        self.rumor_radar_enabled = rumor_radar_enabled and twitter_sentiment_enabled
        self.radar_min_ratio = radar_min_ratio
        self.record_path = record_path
        self.microstructure = MarketMicrostructure(enabled=microstructure_enabled)
        self.timezone_str = timezone_str or 'UTC'
        # Segundos a sumar al reloj local para obtener la hora del exchange (ver DataCollector._clock_offset).
        self._clock_offset_fn = clock_offset_fn
        self._current_exchange: Optional[str] = None
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
        Revisa un par/periodo especifico y avisa. No hace nada si el feature esta deshabilitado,
        el periodo no es el validado (4h), o no hay suficiente historia. Cualquier error
        de deteccion se loguea y se ignora -- nunca debe interrumpir el ciclo de analisis
        (Principio: degradar seguro, nunca romper el pipeline).
        """
        self._apply_breadth_gate = False
        self._deliver(self._collect_pair(exchange, market_pair, candle_period, historical_data))

    def _collect_pair(self, exchange: str, market_pair: str, candle_period: str, historical_data) -> list:
        """Detecta los avisos pendientes de un par (sin enviarlos todavia)."""
        if not self.enabled or candle_period != VALIDATED_CANDLE_PERIOD:
            return []
        self._current_exchange = exchange
        if not historical_data or len(historical_data) < self._min_history():
            return []
        try:
            return self._collect(exchange, market_pair, historical_data)
        except Exception as e:
            self.logger.error(f"[WYCKOFF] Error checking {market_pair} on {exchange}: {e}")
            return []

    def check_cycle(self, exchange: str, pairs_data: Dict[str, list]) -> None:
        """
        Revisa todos los pares de un exchange en un ciclo. Primero cuenta cuantos pares LIQUIDOS
        (>= 20 millones USD en 24 h) tienen evento en la MISMA vela. Telegram recibe la compra
        solo si esos springs son >= 20% de los pares liquidos. El resto se registra y no se envia.
        """
        if not self.enabled:
            return
        self._apply_breadth_gate = True
        self._concurrent, self._liquid_watched = self._count_concurrent(exchange, pairs_data)
        self._watched = self._liquid_watched
        pending = []
        for market_pair, historical_data in pairs_data.items():
            try:
                pending += self._collect_pair(exchange, market_pair, VALIDATED_CANDLE_PERIOD, historical_data)
            except Exception as e:  # un par que falla nunca debe impedir revisar los demas
                self.logger.error(f"[WYCKOFF] Exception checking pair {market_pair} on {exchange}: {e}")
        self._deliver(pending)

    def _count_concurrent(self, exchange: str, pairs_data: Dict[str, list]):
        """Cuenta solo pares con volumen 24h >= 20 millones USD. Devuelve (conteos, universo liquido)."""
        counts: Dict[tuple, int] = {}
        liquid = 0
        for market_pair, historical_data in pairs_data.items():
            if not historical_data or len(historical_data) < self._min_history():
                continue
            try:
                df = IndicatorUtils().convert_to_dataframe(historical_data)
                if not self._is_liquid_df(df):
                    continue
                liquid += 1
                events = [event for event, _ in self._recent_events(df)]
            except Exception as e:
                self.logger.error(f"[WYCKOFF] No se pudo contar eventos de {market_pair}: {e}")
                continue
            for event in events:
                key = (exchange, event[0], event[2].isoformat())
                counts[key] = counts.get(key, 0) + 1
        return counts, liquid

    @staticmethod
    def _is_liquid_df(df) -> bool:
        dvol = WyckoffAlerter._dollar_volume_24h(df)
        return dvol is not None and dvol >= LOW_LIQUIDITY_USD

    @staticmethod
    def _is_liquid_event(event: dict) -> bool:
        dvol = event.get('dvol24h')
        return dvol is not None and dvol >= LOW_LIQUIDITY_USD

    @staticmethod
    def _min_history() -> int:
        return LOOKBACK + CONFIRM_WINDOW + 5

    def _recent_events(self, df):
        """
        Eventos de la ultima vela cerrada y de las MAX_LATE_CANDLES anteriores, del mas viejo al mas nuevo:
        [(evento, df_hasta_esa_vela)]. Cada evento se detecta con el df truncado en su vela, asi que es
        exactamente lo que el bot habria visto entonces (sin mirar el futuro). Sirve para no perder un
        spring confirmado mientras el bot estaba apagado.
        """
        found = []
        for offset in range(MAX_LATE_CANDLES, -1, -1):
            sub = df.iloc[:len(df) - offset]
            if len(sub) < self._min_history():
                continue
            event = self._detect_event(sub)
            if event is not None:
                found.append((event, sub))
        return found

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

    def _collect(self, exchange: str, market_pair: str, historical_data) -> list:
        df = IndicatorUtils().convert_to_dataframe(historical_data)
        events = self._recent_events(df)

        last_timestamp = df.index[len(df) - 1]
        if self.rumor_radar_enabled and not any(event[2] == last_timestamp for event, _ in events):
            try:
                self._check_rumor_radar(exchange, market_pair, df, last_timestamp)
            except Exception as e:
                # el radar no validado nunca debe costar un spring (unico edge comprobado) del mismo par
                self.logger.error(f"[RADAR] Error en {market_pair}: {e}")

        pending = []
        for (direction, break_relative_volume, timestamp), sub in events:
            signature = f"{exchange}:{market_pair}:{direction}:{timestamp.isoformat()}"
            if signature in self._alerted_signatures:
                continue
            try:
                sweep_depth = self._sweep_depth(sub, direction)
            except Exception as e:
                self.logger.error(f"[WYCKOFF] No se pudo medir la barrida de {market_pair}: {e}")
                sweep_depth = None
            pending.append({
                'signature': signature, 'exchange': exchange, 'pair': market_pair, 'direction': direction,
                'break_rv': float(break_relative_volume), 'timestamp': timestamp, 'sweep_depth': sweep_depth,
                'concurrent': self._concurrent.get((exchange, direction, timestamp.isoformat())),
                'change_24h': self._change_24h(sub), 'dvol24h': self._dollar_volume_24h(sub),
                'price': float(sub['close'].iloc[-1]),
            })
        return pending

    def _deliver(self, pending: list) -> None:
        """Agrupa los avisos por vela y direccion, y manda UN mensaje por grupo."""
        groups: Dict[tuple, list] = {}
        for item in pending:
            groups.setdefault((item['direction'], item['timestamp']), []).append(item)
        for (direction, timestamp), group in groups.items():
            try:
                self._deliver_group(direction, timestamp, group)
            except Exception as e:
                self.logger.error(f"[WYCKOFF] No se pudo enviar el aviso de {[g['pair'] for g in group]}: {e}")

    def _silent(self, g: dict, direction: str, timestamp, watched, reason: str) -> None:
        self._remember(g['signature'])
        concurrent = g.get('concurrent')
        self.logger.info(f"[WYCKOFF] Registrado (sin Telegram): {g['pair']} {reason} "
                         f"(vela={timestamp}, vol={g['break_rv']:.2f}x, {concurrent}/{watched})")
        self._record_wyckoff(g, direction, timestamp, twitter_result=None)

    def _deliver_group(self, direction: str, timestamp, group: list) -> None:
        watched = DEFAULT_WATCHED if self._watched is None else self._watched
        if direction != 'hot':
            # Upthrust: se registra para validarlo, no entra al chat. La unica alerta es el spring.
            for g in group:
                self._silent(g, direction, timestamp, watched, 'upthrust')
            return
        if self._apply_breadth_gate:
            liquid = [g for g in group if self._is_liquid_event(g)]
            for g in group:
                if g not in liquid:
                    self._silent(g, direction, timestamp, watched, 'spring poco liquido')
            concurrent = group[0].get('concurrent') or 0
            wide = watched > 0 and concurrent / watched >= WIDE_FRACTION
            if not wide or not liquid:
                for g in liquid:
                    self._silent(g, direction, timestamp, watched, 'spring bajo el 20%')
                return
            group = liquid

        items = [AlertItem(pair=g['pair'], direction=direction, price=g['price'], volume_x=g['break_rv'],
                           candle_open=timestamp, concurrent=g['concurrent'], watched=watched,
                           dvol24h=g['dvol24h'], change_24h=g['change_24h']) for g in group]
        elapsed = self._elapsed_hours(timestamp)
        twitter_result = None
        if len(group) == 1:
            ticker = group[0]['pair'].split('/')[0]
            twitter_result = self.twitter_sentiment.analyze(ticker, direction)
            items[0].twitter_section = TwitterSentimentAnalyzer.format_section(twitter_result)

        text = (build_single_buy(items[0], self.timezone_str, elapsed) if len(items) == 1
                else build_group_buy(items, self.timezone_str, elapsed))

        if self.notifier.send_direct_text(text) is False:
            # Telegram no respondio: NO se da por enviado, se reintenta en el ciclo siguiente.
            for g in group:
                failures = self._send_failures.get(g['signature'], 0) + 1
                self._send_failures[g['signature']] = failures
                if failures < SEND_MAX_FAILURES:
                    self.logger.error(f"[WYCKOFF] Aviso de {g['pair']} sin entregar (intento {failures}); se reintenta")
                else:
                    self.logger.error(f"[WYCKOFF] Aviso de {g['pair']} descartado tras {failures} intentos fallidos")
                    self._remember(g['signature'])
                    self._send_failures.pop(g['signature'], None)
            return

        self._archive_sent([g['pair'] for g in group], timestamp, text)
        for g in group:
            self._send_failures.pop(g['signature'], None)
            self._remember(g['signature'])
            self.logger.info(f"[WYCKOFF] Alert sent: {g['pair']} hot (break_relative_volume={g['break_rv']:.2f}x, "
                             f"grupo de {len(group)}, {g['concurrent']}/{watched})")
            self._record_wyckoff(g, direction, timestamp, twitter_result)

    def _record_wyckoff(self, g: dict, direction: str, timestamp, twitter_result) -> None:
        self._record({
            'type': 'wyckoff', 'direction': direction, 'exchange': g['exchange'], 'pair': g['pair'],
            'candle': timestamp.isoformat() if timestamp is not None else None,
            'relative_volume': round(g['break_rv'], 2),
            'sweep_depth_pct': None if g['sweep_depth'] is None else round(float(g['sweep_depth']), 3),
            'concurrent_pairs': g['concurrent'],
            'watched_pairs': self._watched,
            'weekend_close': self._is_weekend_close(timestamp),
            'dvol24h_usd': None if g['dvol24h'] is None else round(g['dvol24h'], 0),
            'change_24h_pct': None if g['change_24h'] is None else round(float(g['change_24h']), 2),
            'mentions_now': (twitter_result or {}).get('current'),
            'mentions_7d_ago': (twitter_result or {}).get('baseline'),
            'ratio': (twitter_result or {}).get('ratio'),
            'sentiment': (twitter_result or {}).get('sentiment_extreme'),
            'micro': self._safe_microstructure(g['exchange'], g['pair']),
            'eligible': self._is_liquid_event(g),
        })

    def _sent_archive_path(self) -> Optional[str]:
        if not self.record_path:
            return None
        directory = os.path.dirname(self.record_path)
        return os.path.join(directory, SENT_ARCHIVE_NAME) if directory else SENT_ARCHIVE_NAME

    def _archive_sent(self, pairs: list, timestamp, text: str) -> None:
        """El HTML que salio a Telegram, para leerlo sin abrir el chat. No reintenta el envio."""
        path = self._sent_archive_path()
        if not path:
            return
        try:
            row = {
                'recorded_at': datetime.now(timezone.utc).isoformat(),
                'kind': 'wyckoff_hot',
                'pairs': pairs,
                'candle': timestamp.isoformat() if timestamp is not None else None,
                'text': text,
            }
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"[RECORD] No se pudo guardar el texto enviado: {e}")

    def _check_rumor_radar(self, exchange: str, market_pair: str, df, timestamp) -> None:
        """
        Radar volumen + rumor (specs/033-rumor-radar/): vela de 4h cerrada con volumen
        extremo SIN evento Wyckoff -> se mira si las menciones en Twitter se aceleran.
        No validado y no es la alerta principal: se registra, no se manda a Telegram.
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

        last = df.iloc[-1]
        candle_change = (last['close'] - last['open']) / last['open'] * 100 if last['open'] else 0.0
        ratio = velocity.get('ratio')
        triggered = ratio is not None and ratio >= self.radar_min_ratio

        twitter_result = None
        if triggered:
            twitter_result = self.twitter_sentiment.analyze(ticker, 'radar', velocity=velocity)
            ratio_txt = "n/a" if ratio is None else f"{ratio:.2f}"
            self.logger.info(f"[RADAR] Registrado (sin Telegram): {market_pair} (vela={timestamp}, "
                             f"rel_vol={rel_vol:.2f}x, menciones_ratio={ratio_txt})")
        self._remember(signature)

        self._record({
            'type': 'radar', 'exchange': exchange, 'pair': market_pair,
            'candle': timestamp.isoformat(), 'relative_volume': round(float(rel_vol), 2),
            'candle_change_pct': round(float(candle_change), 2),
            'mentions_now': velocity.get('current'), 'mentions_7d_ago': velocity.get('baseline'),
            'ratio': ratio, 'max_views': velocity.get('max_views'), 'alert_sent': False,
            'sentiment': (twitter_result or {}).get('sentiment_extreme'),
        })

    def _record(self, event: dict) -> None:
        """Registro para validar despues con datos reales hacia adelante. Nunca rompe el ciclo."""
        if not self.record_path:
            return
        try:
            local_now = datetime.now(timezone.utc)
            # hora del PC y hora del exchange: si difieren, el reloj del PC (o del contenedor) se desfaso
            event = {'recorded_at': local_now.isoformat(),
                     'exchange_time': self._now_utc().isoformat(),
                     'clock_skew_s': round((local_now - self._now_utc()).total_seconds(), 1), **event}
            directory = os.path.dirname(self.record_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.record_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, default=str) + '\n')
        except Exception as e:
            self.logger.error(f"[RECORD] No se pudo registrar el evento {event.get('type', 'evento')}: {e}")

    @staticmethod
    def _change_24h(df) -> Optional[float]:
        """Cambio % de las ultimas 6 velas de 4h cerradas (24h)."""
        if len(df) < 7:
            return None
        before = df['close'].iloc[-7]
        return (df['close'].iloc[-1] - before) / before * 100 if before else None

    def _now_utc(self) -> datetime:
        """Hora UTC corregida con el reloj del exchange si se puede (el del PC/Docker se desfasa al suspender)."""
        now = datetime.now(timezone.utc)
        if self._clock_offset_fn and self._current_exchange:
            try:
                now += timedelta(seconds=float(self._clock_offset_fn(self._current_exchange)))
            except Exception as e:
                self.logger.error(f"[WYCKOFF] No se pudo corregir el reloj: {e}")
        return now

    @staticmethod
    def _dollar_volume_24h(df) -> Optional[float]:
        """Volumen en USD de las ultimas 6 velas de 4h (24h) cerradas."""
        if len(df) < 6:
            return None
        recent = df.iloc[-6:]
        value = float((recent['volume'].astype(float) * recent['close'].astype(float)).sum())
        return value if value == value else None  # descarta NaN

    def _elapsed_hours(self, timestamp) -> Optional[float]:
        """Horas desde el cierre de la vela (con el reloj del exchange si se pudo medir); None si no hay marca de tiempo."""
        if timestamp is None:
            return None
        return (self._now_utc() - (pd.Timestamp(timestamp) + pd.Timedelta(seconds=CANDLE_SECONDS))).total_seconds() / 3600

    @staticmethod
    def _is_weekend_close(timestamp) -> bool:
        """El backtest clasifica por el dia UTC en que CIERRA la vela de confirmacion (= apertura del trade)."""
        if timestamp is None:
            return False
        return (timestamp + pd.Timedelta(seconds=CANDLE_SECONDS)).dayofweek >= 5

    def _safe_microstructure(self, exchange: str, market_pair: str) -> Optional[dict]:
        """Foto de funding/OI/libro para validar hacia adelante; jamas afecta la alerta ya enviada."""
        try:
            return self.microstructure.snapshot(exchange, market_pair)
        except Exception as e:
            self.logger.error(f"[MICRO] Error inesperado en {market_pair}: {e}")
            return None

    def _remember(self, signature: str) -> None:
        self._alerted_signatures[signature] = None
        self._prune_signatures()

    def _prune_signatures(self, max_size: int = MAX_DEDUP_SIGNATURES) -> None:
        # Descarta las mas antiguas (orden de insercion), nunca las recientes.
        while len(self._alerted_signatures) > max_size:
            del self._alerted_signatures[next(iter(self._alerted_signatures))]
