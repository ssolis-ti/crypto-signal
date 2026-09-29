# Implementation Plan: Enriquecimiento de alertas Wyckoff con sentimiento de Twitter

**Branch**: `main` | **Date**: 2026-09-29 | **Spec**: `specs/031-wyckoff-twitter-sentiment/spec.md`

## Summary

Nuevo módulo `app/analysis/twitter_sentiment.py::TwitterSentimentAnalyzer`,
inyectado en `WyckoffAlerter` (specs/023) como enriquecimiento opcional del
mensaje ya enviado — nunca como filtro de envío. Usa `requests` (ya pineado)
para llamar GetXAPI y Gemini directamente por HTTP, sin SDKs nuevos.

## Technical Context

- Contrato de GetXAPI verificado en vivo contra `docs.getxapi.com` antes de
  escribir código (base URL, auth header, path, formato de respuesta) — no
  se adivinó ningún detalle de la API.
- Modelo de Gemini configurable vía `GEMINI_MODEL` (default
  `gemini-2.0-flash`) para poder actualizarlo sin tocar código si Google
  cambia su catálogo de modelos.
- `WyckoffAlerter.__init__` gana un parámetro opcional
  `twitter_sentiment_enabled` (default `False`) — no rompe la firma para
  quien ya lo instancia solo con `enabled`.

## Constitution Check

- Principio I (solo lectura): GetXAPI y Gemini son ambas consultas de
  lectura, sin custodia ni escritura.
- Principio III (validar antes de confiar): la sección de Twitter se marca
  explícitamente como no validada estadísticamente en el propio mensaje; no
  decide si la alerta base (sí validada) se envía.
- Principio IV (secretos nunca en VCS): `GETXAPI_API_KEY`/`GEMINI_API_KEY`
  solo en `.env` (gitignored), nunca en `config.yml` ni en el código.
- Principio VI (tests): nuevo módulo con tests unitarios, `requests`
  mockeado en el 100% de los casos — cero llamadas de red reales en la
  suite.
- Principio VII (deps pineadas): sin dependencias nuevas — `requests==2.34.2`
  ya está pineado y cubre ambas integraciones.

## Project Structure

```
app/analysis/twitter_sentiment.py       (new)
app/analysis/wyckoff_alerts.py          (modified: wiring opcional)
app/behaviour/core.py                   (modified: lee el nuevo flag anidado)
app/defaults.yml                        (modified: nuevo flag, default false)
config-clean.yml, config.yml            (modified: flag documentado/activado)
.env.example                            (modified: nuevas vars opcionales)
tests/analysis/test_twitter_sentiment.py (new)
tests/analysis/test_wyckoff_alerts.py    (modified: 3 tests nuevos de wiring)
specs/031-wyckoff-twitter-sentiment/{spec.md, plan.md, tasks.md}
```
