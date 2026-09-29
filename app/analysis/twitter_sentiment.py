"""
Twitter/X en vivo para crypto-signal (specs/031-wyckoff-twitter-sentiment/ y
specs/033-rumor-radar/).

Dos mediciones sobre los tweets recientes de un ticker (GetXAPI, docs.getxapi.com):

1. Velocidad de menciones: la busqueda devuelve una pagina fija de ~20 tweets, asi que
   en vez de contar se mide cuanto tiempo abarcan (20 tweets en 10 min = ticker
   hirviendo; en 12 h = quieto). Se compara contra la misma medicion de hace 7 dias
   usando `until_time:` (corte exacto en el pasado, verificado en vivo).
2. Clasificacion del contenido con Gemini (esquema de specs/030): capitulacion /
   euforia / mixto / nada, pico social confirmado por terceros, catalizador presente.

Todo es informativo y NO validado estadisticamente (Principio III): nunca decide si
una alerta Wyckoff se envia. Degrada seguro: cualquier error se loguea y el metodo
retorna None o un resultado parcial (p. ej. velocidad sin clasificacion si Gemini cae).
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone

import requests
import structlog

GETXAPI_BASE_URL = "https://api.getxapi.com"
GETXAPI_SEARCH_PATH = "/twitter/tweet/advanced_search"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"
REQUEST_TIMEOUT_SECONDS = 25
MAX_TWEETS_FOR_PROMPT = 15
MAX_TWEET_TEXT_CHARS = 240
BASELINE_DAYS = 7
ACCELERATING_RATIO = 2.0
VIRAL_VIEWS = 50_000
TWITTER_DATE_FORMAT = "%a %b %d %H:%M:%S %z %Y"

CLASSIFICATION_PROMPT_TEMPLATE = """Sos un analista de sentimiento de mercados cripto. A continuacion hay hasta {n} tweets recientes sobre {ticker}, recolectados porque el precio tuvo un pico de volumen inusual.

Clasifica el conjunto segun este esquema y responde SOLO con un JSON valido, sin texto adicional ni markdown:

{{
  "sentiment_extreme": "capitulation" | "euphoria" | "mixed" | "none",
  "social_spike_confirmed": true | false,
  "catalyst_present": true | false,
  "summary": "una frase corta en espanol resumiendo lo que dicen los tweets"
}}

Definiciones:
- "capitulation": lenguaje de rendicion/panico/venta, gente dandose por vencida con el activo.
- "euphoria": lenguaje de euforia/FOMO viral, "a la luna", entusiasmo extremo sostenido.
- "mixed": señales de ambos tipos mezcladas, sin un tono dominante claro.
- "none": conversacion normal, sin sentimiento extremo en ningun sentido.
- social_spike_confirmed: true SOLO si algun tweet menciona explicitamente una herramienta de analitica social reportando un pico (ej. "Galaxy Score", "trending", "FOMO alert", "social activity spiking").
- catalyst_present: true SOLO si hay una noticia/evento concreto (partnership, buyback, listing, voto regulatorio, movimiento de ballena, hackeo) mencionado, no solo opinion de precio.

Tweets:
{tweets_block}
"""

SENTIMENT_LABELS = {
    'capitulation': '🩸 Capitulación',
    'euphoria': '🎉 Euforia',
    'mixed': '🔀 Mixto',
    'none': '➖ Sin señal clara',
}


class TwitterSentimentAnalyzer:
    """Velocidad de menciones + clasificacion de contenido. Informativo, nunca un gate."""

    def __init__(self, enabled: bool = False):
        self.logger = structlog.get_logger()
        self.enabled = enabled
        self.getxapi_key = os.environ.get('GETXAPI_API_KEY', '').strip()
        self.gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
        self.gemini_model = os.environ.get('GEMINI_MODEL', DEFAULT_GEMINI_MODEL).strip()

    def mention_velocity(self, ticker: str, now: datetime = None):
        """
        Retorna {'current', 'baseline', 'ratio', 'max_views', 'tweets'} (menciones/hora
        ahora vs. hace BASELINE_DAYS) o None si esta deshabilitado, falta la key o falla.
        """
        if not self.enabled:
            return None
        if not self.getxapi_key:
            self.logger.error("[TWITTER] habilitado pero falta GETXAPI_API_KEY")
            return None
        try:
            now = now or datetime.now(timezone.utc)
            baseline_cut = int((now - timedelta(days=BASELINE_DAYS)).timestamp())
            current_tweets = self._search(f"${ticker}")
            baseline_tweets = self._search(f"${ticker} until_time:{baseline_cut}")
            current = self._mentions_per_hour(current_tweets)
            baseline = self._mentions_per_hour(baseline_tweets)
            ratio = current / baseline if current and baseline else None
            max_views = max((t.get('viewCount') or 0 for t in current_tweets), default=0)
            return {'current': current, 'baseline': baseline, 'ratio': ratio,
                    'max_views': max_views, 'tweets': current_tweets}
        except Exception as e:
            self.logger.error(f"[TWITTER] Error midiendo velocidad de {ticker}: {e}")
            return None

    def analyze(self, ticker: str, direction: str, velocity: dict = None):
        """
        Velocidad + clasificacion. Retorna None si no hay datos de Twitter; si Gemini
        falla o no hay key, retorna solo la velocidad (sentiment_extreme = None).
        """
        velocity = velocity or self.mention_velocity(ticker)
        if not velocity or not velocity.get('tweets'):
            return None

        result = {k: v for k, v in velocity.items() if k != 'tweets'}
        result.update({'sentiment_extreme': None, 'social_spike_confirmed': False,
                       'catalyst_present': False, 'summary': ''})
        if not self.gemini_key:
            return result
        try:
            classification = self._classify(ticker, self._texts(velocity['tweets']))
            if classification:
                result.update(classification)
        except Exception as e:
            self.logger.error(f"[TWITTER] Error clasificando {ticker}: {e}")
        return result

    def _search(self, query: str):
        response = requests.get(
            f"{GETXAPI_BASE_URL}{GETXAPI_SEARCH_PATH}",
            headers={"Authorization": f"Bearer {self.getxapi_key}"},
            params={"q": query, "product": "Latest"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get('tweets') or []

    @staticmethod
    def _mentions_per_hour(tweets):
        times = []
        for t in tweets:
            try:
                times.append(datetime.strptime(t['createdAt'], TWITTER_DATE_FORMAT))
            except (KeyError, TypeError, ValueError):
                continue
        if len(times) < 2:
            return None
        span_hours = (max(times) - min(times)).total_seconds() / 3600
        if span_hours <= 0:
            return None
        return (len(times) - 1) / span_hours

    @staticmethod
    def _texts(tweets):
        texts = [t.get('text', '').strip()[:MAX_TWEET_TEXT_CHARS] for t in tweets if t.get('text')]
        return texts[:MAX_TWEETS_FOR_PROMPT]

    def _classify(self, ticker: str, tweets):
        tweets_block = "\n".join(f"- {t}" for t in tweets)
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            n=len(tweets), ticker=ticker, tweets_block=tweets_block
        )

        response = requests.post(
            f"{GEMINI_API_BASE}/{self.gemini_model}:generateContent",
            headers={"x-goog-api-key": self.gemini_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        raw_text = data['candidates'][0]['content']['parts'][0]['text']
        parsed = self._parse_json_response(raw_text)
        if parsed is None:
            self.logger.error("[TWITTER] Respuesta de Gemini no parseable como JSON")
            return None
        return {
            'sentiment_extreme': parsed.get('sentiment_extreme', 'none'),
            'social_spike_confirmed': bool(parsed.get('social_spike_confirmed', False)),
            'catalyst_present': bool(parsed.get('catalyst_present', False)),
            'summary': parsed.get('summary', ''),
        }

    @staticmethod
    def _parse_json_response(raw_text: str):
        cleaned = re.sub(r'^```(json)?|```$', '', raw_text.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def format_section(result) -> str:
        """Seccion de Twitter para el mensaje de Telegram, o '' si no hay resultado."""
        if result is None:
            return ''
        lines = ["🐦 <b>Twitter</b> (informativo, sin validar estadísticamente)"]

        current, baseline, ratio = result.get('current'), result.get('baseline'), result.get('ratio')
        if ratio is not None:
            trend = " 🔥 acelerando" if ratio >= ACCELERATING_RATIO else ""
            lines.append(f"Menciones: {current:.1f}/h ahora vs {baseline:.1f}/h hace "
                         f"{BASELINE_DAYS} días ({ratio:.1f}x){trend}")
        elif current is not None:
            lines.append(f"Menciones: {current:.1f}/h ahora")
        if (result.get('max_views') or 0) >= VIRAL_VIEWS:
            lines.append(f"📣 Tweet viral: {result['max_views']:,} vistas")

        if result.get('sentiment_extreme'):
            label = SENTIMENT_LABELS.get(result['sentiment_extreme'], SENTIMENT_LABELS['none'])
            lines.append(f"Sentimiento: {label}")
        if result.get('social_spike_confirmed'):
            lines.append("📡 Pico de actividad social confirmado por terceros")
        if result.get('catalyst_present'):
            lines.append("📰 Hay un catalizador/noticia concreta circulando")
        if result.get('summary'):
            lines.append(f"<i>{result['summary']}</i>")

        return "\n".join(lines) if len(lines) > 1 else ''
