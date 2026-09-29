# Implementation Plan: Piloto de Twitter/X event-triggered por altcoin

**Branch**: `main` | **Date**: 2026-09-29 | **Spec**: `specs/028-twitter-event-triggered-pilot/spec.md`

## Summary

Generar la lista de eventos Wyckoff de altcoins (BTC excluido) con resultado
conocido (`generate_altcoin_events.py`, reutiliza `WyckoffPrimitives` de
`app/`), tomar una muestra estratificada de 20 eventos (10 ganadores/10
perdedores a 14d), y consultar `advanced_search_tweets` con un query angosto
(ticker + ventana corta) alrededor de cada uno para ver si `tweet_count` varía
de forma útil por debajo del tope conocido (~19, spec 022).

## Hallazgo temprano — mismo patrón de parada honesta que spec 022

Las primeras 3 consultas diagnósticas (antes de gastar las 20 planeadas)
mostraron el mismo patrón que invalidó spec 022, ahora con una variable
controlada distinta:

| Query | Ticker | Ventana | tweet_count | has_more |
|---|---|---|---|---|
| `$DOGE since:2026-07-06 until:2026-07-08` | DOGE (top-10, alta cap) | 2 días | 18 | false |
| `$ATOM since:2026-07-08 until:2026-07-09` | ATOM (media cap) | 1 día | 19 | false |
| `$NEAR since:2026-09-11 until:...20:00 UTC` | NEAR (media cap) | ventana horaria angosta | 19 | false |

**El tope de ~18-19 persiste sin importar el tamaño de la moneda ni el ancho
de la ventana** — incluso acotando a horas en vez de días. Esto descarta la
hipótesis específica de esta corrección (que angostar a altcoin+evento
evitaría el tope que sí afectaba a `$BTC` en spec 022). El comportamiento
real observado: `advanced_search_tweets` con `product=Latest` devuelve una
página fija de los tweets más recientes antes de `until:` (~18-19), sin
ofrecer `next_cursor` (siempre `null`) — es un límite duro de la API, no un
artefacto del volumen de la consulta.

Por la misma disciplina que spec 022 (parar temprano cuando el patrón ya es
inequívoco, no repetir el mismo resultado 17 veces más), se detuvo la
recolección en 3/20 consultas.

## Constitution Check

Igual que spec 022 (Principios I, III, V). No se conecta nada a producción.

## Project Structure

```
specs/028-twitter-event-triggered-pilot/
├── spec.md
├── plan.md                        (this file)
├── tasks.md
├── generate_altcoin_events.py     (generador de eventos, ejecutado)
├── altcoin_events.json            (67 eventos altcoin con resultado conocido)
└── sample_events.json             (muestra de 20 para el piloto — no se completó)
```
