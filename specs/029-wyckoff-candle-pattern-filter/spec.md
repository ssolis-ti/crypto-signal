# Spec: Patrones de vela como filtro adicional sobre el edge Wyckoff

## Contexto

Último candidato priorizado en specs/026 (item 1), siguiendo la misma lógica
que hizo funcionar el volumen extremo (spec 017): probar patrones de vela
(`app/analyzers/indicators/candle_recognition.py`, ya codificado con 60+
patrones TA-Lib pero deshabilitado) **como filtro adicional** sobre el
mecanismo YA validado (Spring/Upthrust + volumen extremo), no como señal
aislada — evitando el error de specs/024.

## Objetivo

Determinar si la vela de confirmación de un evento que ya califica en
producción (Spring/Upthrust + volumen extremo ≥2.5x) confirma ADEMÁS con un
patrón de vela de reversión alineado a la dirección esperada, y si eso mejora
el baseline — con el mismo rigor de specs/017/018/027: split cronológico
70/30, comparación explícita contra baseline en AMBOS tramos (lección de
spec 027: no alcanza con que solo el tramo out-of-sample pase la vara
mecánica).

## Alcance

- Base: mismos eventos que producción (specs/023) — Spring/Upthrust +
  volumen extremo, 4h, mismo basket y ventana de 10 meses.
- Reutilizar `WyckoffPrimitives` de `app/` sin modificar.
- Dos candidatos, evaluados en la vela de confirmación vía TA-Lib `CDL*`:
  1. **Cualquier patrón reconocido alineado**: de los 60+ patrones
     disponibles, ¿alguno dispara con signo alineado a la dirección del
     evento (positivo/alcista para `hot`, negativo/bajista para `cold`)?
  2. **Patrones de reversión "core" alineados**: subconjunto curado de mayor
     conocimiento (engulfing, hammer/hanging man, morning/evening star,
     piercing/dark cloud cover, shooting star) — evita diluir la señal con
     patrones débiles o poco documentados.
- Fuera de alcance: conectar cualquier resultado a producción.

## Requisitos funcionales

- FR-001: Calcular los patrones TA-Lib `CDL*` en la vela de confirmación de
  cada evento base.
- FR-002: Split cronológico 70/30 in-sample/out-of-sample.
- FR-003: Evaluar baseline (sin filtro) y ambos candidatos en los 4
  horizontes, reportando **in-sample Y out-of-sample explícitamente uno junto
  al otro** (no solo out-of-sample) para poder juzgar consistencia real.
- FR-004: Veredicto `confirmed` solo si el candidato muestra lift consistente
  sobre el baseline en AMBOS tramos (no solo mecánicamente en el
  out-of-sample) — aplicando directamente la lección de spec 027.
- FR-005: No modificar código de producción en este slice.

## Criterios de éxito

- SC-001: Ambos candidatos evaluados en los 4 horizontes, con números
  reproducibles.
- SC-002: Veredicto honesto por candidato, con el chequeo de consistencia
  in-sample/out-of-sample explícito (no solo el resultado mecánico).
