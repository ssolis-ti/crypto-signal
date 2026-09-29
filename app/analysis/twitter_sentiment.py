"""
Clasificador de sentimiento de Twitter/X para alertas Wyckoff en vivo
(specs/031-wyckoff-twitter-sentiment/), continuacion del piloto cualitativo de
specs/030-twitter-sentiment-classifier/.

Por cada evento Wyckoff que ya califica (volumen extremo, specs/023), consulta
tweets recientes del ticker via GetXAPI (docs.getxapi.com) y le pide a Gemini que
los clasifique segun el esquema definido en specs/030 (sentiment_extreme,
social_spike_confirmed, catalyst_present). Es puramente informativo -- se agrega
como seccion extra al mensaje de Telegram, NUNCA decide si se envia o no la
alerta (Principio III de la constitucion: el volumen extremo es el unico edge
validado con holdout; este modulo es un hallazgo cualitativo de n=5, no
estadisticamente probado -- ver specs/030/tasks.md).

Degrada seguro: cualquier error (credenciales faltantes, API caida, respuesta
invalida) se loguea y el metodo retorna None -- la alerta base se envia igual,
sin la seccion de Twitter.
"""
import json
import os
import re

import requests
import structlog

GETXAPI_BASE_URL = "https://api.getxapi.com"
GETXAPI_SEARCH_PATH = "/twitter/tweet/advanced_search"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
REQUEST_TIMEOUT_SECONDS = 10
MAX_TWEETS_FOR_PROMPT = 15
MAX_TWEET_TEXT_CHARS = 240

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
    """
    Enriquecimiento OPCIONAL e informativo de las alertas Wyckoff con contenido de
    Twitter/X, clasificado por un LLM. No forma parte del edge validado
    (specs/017/018) y nunca decide si una alerta se envia o no.
    """

    def __init__(self, enabled: bool = False):
        self.logger = structlog.get_logger()
        self.enabled = enabled
        self.getxapi_key = os.environ.get('GETXAPI_API_KEY', '').strip()
        self.gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
        self.gemini_model = os.environ.get('GEMINI_MODEL', DEFAULT_GEMINI_MODEL).strip()

    def analyze(self, ticker: str, direction: str):
        """
        Retorna un dict {sentiment_extreme, social_spike_confirmed, catalyst_present,
        summary} o None si esta deshabilitado, faltan credenciales, no hay tweets, o
        algo falla. Nunca lanza -- ver docstring del modulo.
        """
        if not self.enabled:
            return None
        if not self.getxapi_key or not self.gemini_key:
            self.logger.error(
                "[TWITTER_SENTIMENT] habilitado pero faltan GETXAPI_API_KEY/GEMINI_API_KEY"
            )
            return None
        try:
            tweets = self._fetch_tweets(ticker)
            if not tweets:
                return None
            return self._classify(ticker, tweets)
        except Exception as e:
            self.logger.error(f"[TWITTER_SENTIMENT] Error analizando {ticker}: {e}")
            return None

    def _fetch_tweets(self, ticker: str):
        response = requests.get(
            f"{GETXAPI_BASE_URL}{GETXAPI_SEARCH_PATH}",
            headers={"Authorization": f"Bearer {self.getxapi_key}"},
            params={"q": f"${ticker}", "product": "Latest"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        tweets = data.get('tweets') or []
        texts = [t.get('text', '').strip()[:MAX_TWEET_TEXT_CHARS] for t in tweets if t.get('text')]
        return texts[:MAX_TWEETS_FOR_PROMPT]

    def _classify(self, ticker: str, tweets):
        tweets_block = "\n".join(f"- {t}" for t in tweets)
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            n=len(tweets), ticker=ticker, tweets_block=tweets_block
        )

        response = requests.post(
            f"{GEMINI_API_BASE}/{self.gemini_model}:generateContent",
            params={"key": self.gemini_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        raw_text = data['candidates'][0]['content']['parts'][0]['text']
        parsed = self._parse_json_response(raw_text)
        if parsed is None:
            self.logger.error("[TWITTER_SENTIMENT] Respuesta de Gemini no parseable como JSON")
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
        """Arma la seccion opcional de Twitter para el mensaje de Telegram, o '' si no hay resultado."""
        if result is None:
            return ''
        label = SENTIMENT_LABELS.get(result['sentiment_extreme'], SENTIMENT_LABELS['none'])
        lines = [
            "🐦 <b>Twitter</b> (informativo, sin validar estadísticamente -- specs/030)",
            f"Sentimiento: {label}",
        ]
        if result['social_spike_confirmed']:
            lines.append("📡 Pico de actividad social confirmado por terceros")
        if result['catalyst_present']:
            lines.append("📰 Hay un catalizador/noticia concreta circulando")
        if result.get('summary'):
            lines.append(f"<i>{result['summary']}</i>")
        return "\n".join(lines)
