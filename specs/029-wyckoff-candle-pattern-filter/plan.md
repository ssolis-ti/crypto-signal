# Implementation Plan: Patrones de vela como filtro adicional sobre el edge Wyckoff

**Branch**: `main` | **Date**: 2026-09-29 | **Spec**: `specs/029-wyckoff-candle-pattern-filter/spec.md`

## Summary

Escribir `validate_candle_patterns.py`: reutilizar `WyckoffPrimitives` para
generar el mismo set base de eventos que producción, calcular los patrones
`CDL*` de TA-Lib en la vela de confirmación, evaluar dos candidatos ("
cualquier patrón alineado" y "patrones core alineados") contra el baseline,
reportando in-sample y out-of-sample lado a lado explícitamente (corrige el
punto ciego de spec 027, donde el baseline in-sample no se calculó junto al
resto y hubo que revisarlo aparte).

## Technical Context

Mismo patrón que slices 017/025/027: script standalone, Docker, sin
dependencias nuevas (TA-Lib ya pineado trae todos los `CDL*` nativamente).

## Constitution Check

Igual tabla PASS que slices anteriores (Principios I, II, III, V, VII).
Principio III aplicado con la lección explícita de spec 027: un filtro solo
"confirma" si el lift es consistente en ambos tramos, no solo si el
out-of-sample pasa la vara mecánica aislado del in-sample.

## Project Structure

```
specs/029-wyckoff-candle-pattern-filter/
├── spec.md
├── plan.md                        (this file)
├── tasks.md
└── validate_candle_patterns.py    (new backtest/search script)
```
