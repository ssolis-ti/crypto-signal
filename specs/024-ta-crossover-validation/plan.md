# Implementation Plan: Validación de cruces TA no probados

**Branch**: `main` | **Date**: 2026-09-29 | **Spec**: `specs/024-ta-crossover-validation/spec.md`

## Summary

Escribir `validate_ta_crossovers.py`: reimplementar vectorizadamente (sobre toda
la serie, no solo la última vela) la lógica de `ma_crossover.py` y `sqzmom.py`,
recolectar eventos sobre el mismo basket/ventana que specs/017-021, evaluar 4
candidatos (los 2 cruces, solos y combinados con el filtro de volumen extremo
>=2.5x que sí funcionó en Wyckoff) con split cronológico 70/30, mismo criterio
de "accionable" (win_rate>=60%, p<0.05, n>=30 en out-of-sample).

## Technical Context

Mismo patrón que slices 007/011/017/019/021: script standalone fuera de
`app/`, ejecutado en Docker, sin dependencias nuevas (reutiliza pandas/numpy/
talib ya pineados). Reimplementación vectorizada necesaria porque
`ma_crossover.py`/`sqzmom.py` originales solo evalúan la última vela (diseño
para uso en vivo, no para backtest histórico) — no se modifica ese código de
producción, solo se replica su lógica en el script de validación.

## Constitution Check

Igual tabla PASS que slices 007/011/017/019/021 (Principios I, II, III, V, VII
relevantes). Principio III aplicado en su forma más estricta: nada se conecta a
producción en este slice pase lo que pase el resultado.

## Project Structure

```
specs/024-ta-crossover-validation/
├── spec.md
├── plan.md                    (this file)
├── tasks.md
└── validate_ta_crossovers.py  (new backtest/search script)
```
