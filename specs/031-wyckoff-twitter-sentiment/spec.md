# Spec: Enriquecimiento de alertas Wyckoff con sentimiento de Twitter (LLM en vivo)

## Contexto

specs/030 encontró, con lectura manual de 6 eventos, un patrón cualitativo
coherente con Wyckoff: capitulación genuina en springs ganadores, euforia
sostenida en upthrusts perdedores. El operador decidió integrarlo en vivo en
vez de seguir ampliando el piloto manual. Esto es un cambio de arquitectura
real (Principio IV: secretos nunca en VCS) — dos integraciones externas
nuevas, cada una con su propia API key:

- **GetXAPI** (docs.getxapi.com): REST con Bearer key, `GET
  /twitter/tweet/advanced_search?q=$TICKER&product=Latest`, $0.001/consulta.
  Contrato verificado en vivo contra la documentación oficial (base URL
  `https://api.getxapi.com`, auth `Authorization: Bearer <key>`).
- **Google Gemini**: clasifica el contenido según el esquema de specs/030.

## Decisión de diseño clave: informativo, nunca un gate

El volumen extremo en la ruptura sigue siendo el ÚNICO edge validado con
holdout (specs/017/018). El hallazgo de Twitter es cualitativo, n=5, sin
z-test ni split in-sample/out-of-sample posible con tan pocos casos. Por lo
tanto:

- Esta integración SOLO agrega una sección informativa al mensaje de
  Telegram ya validado (specs/023) — nunca decide si la alerta se envía o no.
- Cualquier fallo (credenciales faltantes, API caída, respuesta no
  parseable) degrada silenciosamente: la alerta base se envía igual, sin la
  sección de Twitter.
- Costo acotado: solo se consulta por evento que YA calificó (volumen
  extremo, ~2-3 eventos/mes en todo el basket de producción) — nunca por
  ciclo ni por par sin evento.

## Requisitos funcionales

- FR-001: `TwitterSentimentAnalyzer.analyze(ticker, direction)` consulta
  GetXAPI (`advanced_search`, query `$TICKER`, `product=Latest`) y clasifica
  el contenido con Gemini según el esquema de specs/030 (`sentiment_extreme`,
  `social_spike_confirmed`, `catalyst_present`, `summary`).
- FR-002: Ambas API keys (`GETXAPI_API_KEY`, `GEMINI_API_KEY`) se leen solo
  de variables de entorno (`.env`, gitignored) — nunca de `config.yml`.
- FR-003: Deshabilitado por defecto (`wyckoff_alerts.twitter_sentiment.
  enabled: false`), independiente del flag principal `wyckoff_alerts.enabled`.
- FR-004: Cualquier excepción (red, parseo, credenciales faltantes) se
  captura y loguea; `analyze()` retorna `None` y `WyckoffAlerter` envía la
  alerta base sin la sección adicional — nunca rompe el envío.
- FR-005: La sección de Twitter se etiqueta explícitamente como
  "informativo, sin validar estadísticamente" en el propio mensaje.
- FR-006: No se agregan dependencias nuevas de Python (`requests` ya está
  pineado — se usa para ambas APIs, sin SDKs adicionales).

## Criterios de éxito

- SC-001: Tests con `requests` mockeado cubren el camino feliz y cada modo
  de fallo (sin credenciales, sin tweets, error de red, JSON inválido).
- SC-002: `WyckoffAlerter` con `twitter_sentiment_enabled=False` (default)
  no cambia el mensaje ya validado en producción — cero regresión.
- SC-003: Suite completa pasando en `crypto-signal:dev`.
