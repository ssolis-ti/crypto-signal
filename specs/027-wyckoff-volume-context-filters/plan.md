# Implementation Plan: Filtros de contexto de volumen sobre el edge Wyckoff

**Branch**: `main` | **Date**: 2026-09-29 | **Spec**: `specs/027-wyckoff-volume-context-filters/spec.md`

## Summary

Escribir `validate_volume_context.py`: reutilizar `WyckoffPrimitives` (código
de producción) para generar el mismo conjunto base de eventos que specs/023
(Spring/Upthrust + volumen extremo ≥2.5x, 4h), anotar cada evento con
CMF(20)/PVT/NVI vía TA-Lib en la vela de confirmación, evaluar cada uno como
filtro adicional contra el baseline de producción con split 70/30.

## Technical Context

Mismo patrón que slices 017/018/025: script standalone, Docker, sin
dependencias nuevas (TA-Lib ya pineado trae CMF/PVT/NVI nativamente — no hace
falta reimplementar como en slice 024).

## Constitution Check

Igual tabla PASS que slices anteriores (Principios I, II, III, V, VII).
Principio III: nada se conecta a producción pase lo que pase el resultado.

## Project Structure

```
specs/027-wyckoff-volume-context-filters/
├── spec.md
├── plan.md                        (this file)
├── tasks.md
└── validate_volume_context.py     (new backtest/search script)
```
