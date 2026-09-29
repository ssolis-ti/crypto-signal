# Implementation Plan: Validación del edge Wyckoff en otros timeframes

**Branch**: `main` | **Date**: 2026-09-29 | **Spec**: `specs/025-wyckoff-multi-timeframe-validation/spec.md`

## Summary

Escribir `validate_wyckoff_timeframes.py`: reutilizar `WyckoffPrimitives`
(código de producción, sin reimplementar) sobre 4 timeframes candidatos
(1h, 2h, 8h, 1d) más 4h como control, descargar OHLCV real de cada uno,
filtrar por volumen extremo ≥2.5x en la ruptura, evaluar con split
cronológico 70/30 igual que specs/017/018/024.

## Technical Context

Mismo patrón que slices 017/018/021/024: script standalone fuera de `app/`,
ejecutado en Docker, sin dependencias nuevas. A diferencia de slice 024, aquí
SÍ se importa `WyckoffPrimitives` directamente desde `app/analyzers/indicators/
wyckoff.py` (no se reimplementa) porque el mecanismo ya es código de
producción validado — el objetivo es solo variar el timeframe de entrada, no
la lógica de detección.

Nota de horizonte por timeframe: los horizontes (24h/72h/7d/14d) se expresan
en velas según el timeframe de cada corrida (p.ej. 14d = 14 velas en 1d, 336
velas en 1h) para mantener comparabilidad en tiempo real entre timeframes.

## Constitution Check

Igual tabla PASS que slices 017/018/021/024 (Principios I, II, III, V, VII
relevantes). Principio III aplicado igual que siempre: ningún timeframe se
conecta a producción en este slice pase lo que pase el resultado — eso queda
para un slice de implementación posterior, condicionado a que algo confirme.

## Project Structure

```
specs/025-wyckoff-multi-timeframe-validation/
├── spec.md
├── plan.md                        (this file)
├── tasks.md
└── validate_wyckoff_timeframes.py (new backtest/search script)
```
