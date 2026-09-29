# Spec: Filtros de contexto de volumen (CMF/PVT/NVI) sobre el edge Wyckoff

## Contexto

specs/024 y 025 mostraron que probar indicadores nuevos como señal *aislada* no
rinde. El único mecanismo que sobrevivió holdout (specs/017-018) fue volumen
extremo **como filtro adicional** sobre una estructura ya identificada
(Spring/Upthrust). specs/026 catalogó CMF/PVT/NVI (Volume Indicators de
TA-Lib, sin probar en este proyecto) como candidatos con la misma lógica:
¿hay acumulación/distribución de fondo *antes* del evento que ya alertamos en
producción, y eso mejora el win rate?

## Objetivo

Determinar si CMF, PVT o NVI, evaluados en la vela de confirmación de un
Spring/Upthrust que YA califica (volumen extremo ≥2.5x, el filtro en
producción), aportan una mejora adicional sobre ese baseline — con el mismo
rigor que specs/017/018/025: split cronológico 70/30, win_rate≥60%, p<0.05,
n≥30 en el tramo out-of-sample.

## Alcance

- Base: los mismos eventos que ya están en producción (specs/023) — Spring/
  Upthrust + volumen extremo ≥2.5x, 4h, mismo basket y ventana de 10 meses.
- Reutilizar `WyckoffPrimitives` de `app/` sin modificar (igual que slice 025).
- Candidatos de contexto, evaluados en la vela de confirmación:
  1. **CMF(20) alineado**: CMF > 0 para eventos `hot`, CMF < 0 para `cold`.
  2. **PVT en tendencia alineada**: PVT(i) vs PVT(i-20) subiendo para `hot`,
     bajando para `cold`.
  3. **NVI en tendencia alineada**: mismo criterio que PVT pero con NVI
     (índice de "smart money" — acumulación en días de volumen bajo).
- Comparación: baseline = todos los eventos que ya califican en producción
  (sin filtro adicional) vs. cada candidato aplicado como filtro extra.
- Fuera de alcance: conectar cualquier resultado a producción (slice de
  implementación posterior, solo si algo confirma).

## Requisitos funcionales

- FR-001: Calcular CMF(20), PVT y NVI sobre cada par del basket usando
  TA-Lib directamente (sin reimplementar).
- FR-002: Sobre los eventos base (Spring/Upthrust + volumen extremo, ya
  producidos por `WyckoffPrimitives`), anotar cada uno con los 3 indicadores
  de contexto en la vela de confirmación.
- FR-003: Split cronológico 70/30 in-sample/out-of-sample.
- FR-004: Evaluar baseline (sin filtro) y cada candidato como filtro
  adicional, en los 4 horizontes (24h/72h/7d/14d), con z-test de win rate.
- FR-005: Veredicto explícito por candidato: `confirmed` solo si mejora sobre
  el baseline out-of-sample Y cumple `win_rate≥60%`, `p<0.05`, `n≥30`.
- FR-006: No modificar código de producción en este slice.

## Criterios de éxito

- SC-001: Los 3 candidatos evaluados en los 4 horizontes, con números
  reproducibles.
- SC-002: Veredicto claro por candidato, documentado en tasks.md Convergence.
- SC-003: Comparación explícita contra el baseline de producción (no solo
  contra 50%), para saber si realmente suma algo o es redundante.
