# Tasks: Enriquecimiento de alertas Wyckoff con sentimiento de Twitter

## Phase 1: Investigación previa (bloqueante)

- [X] T001 Verificar en vivo el contrato REST real de GetXAPI (base URL, auth,
      endpoint de búsqueda) contra `docs.getxapi.com` antes de escribir
      código — no se adivinó ningún detalle.

## Phase 2: Implementation

- [X] T002 `app/analysis/twitter_sentiment.py`: `TwitterSentimentAnalyzer` —
      `analyze()` (GetXAPI + Gemini, degradación segura completa),
      `format_section()` (armado del texto opcional del mensaje) (FR-001,
      FR-002, FR-004, FR-005, FR-006).
- [X] T003 `app/analysis/wyckoff_alerts.py`: `WyckoffAlerter` construye un
      `TwitterSentimentAnalyzer` propio, gana `twitter_sentiment_enabled`
      (default `False`), y apila la sección opcional al mensaje ya validado
      en `_send_alert` (FR-003).
- [X] T004 `app/behaviour/core.py`: lee
      `wyckoff_alerts.twitter_sentiment.enabled` y lo pasa al constructor.
- [X] T005 `app/defaults.yml`, `config-clean.yml`, `config.yml`,
      `.env.example`: nuevo flag anidado y variables de entorno
      documentadas.

## Phase 3: Tests

- [X] T006 `tests/analysis/test_twitter_sentiment.py` (14 tests): camino
      feliz, JSON envuelto en fence de markdown, deshabilitado, credenciales
      faltantes, sin tweets, error de red en GetXAPI, error de red en
      Gemini, JSON inválido de Gemini, `format_section` con/sin resultado.
- [X] T007 `tests/analysis/test_wyckoff_alerts.py`: 3 tests nuevos de
      wiring — deshabilitado por defecto no cambia el mensaje, habilitado
      con resultado agrega la sección, habilitado sin resultado (analyzer
      devuelve `None`) no agrega nada.
- [X] T008 Suite completa: 169/169 passing en `crypto-signal:dev` (155
      previos + 14 nuevos).

## Phase 4: Convergence

Completado 2026-09-29. Integración construida sobre el hallazgo cualitativo
de specs/030, con el contrato de GetXAPI verificado en vivo (no adivinado) y
sin dependencias nuevas de Python (`requests` ya pineado cubre ambas APIs).

**Diseño deliberado**: la sección de Twitter es puramente informativa y
nunca es un gate de envío — el volumen extremo en la ruptura sigue siendo el
único edge con holdout validado (specs/017/018/023). Cualquier fallo (sin
API keys, red caída, JSON inválido) degrada silenciosamente: se loguea y la
alerta base se envía igual, exactamente como se comportaba antes de este
slice.

**Pendiente del operador, fuera de este slice**: completar `GETXAPI_API_KEY`
y `GEMINI_API_KEY` en el `.env` real (no en este repo, nunca en git). Sin
esas credenciales, `twitter_sentiment.enabled: true` en `config.yml` no
hace nada dañino — solo loguea un error una vez por alerta y sigue sin la
sección extra (FR-004 cubre exactamente este caso, con test dedicado).

**Outcome**: `converged` — 169/169 tests passing, cero regresión en el
comportamiento ya validado, primera integración de LLM del proyecto,
explícitamente separada del pipeline de decisión (Principio III).