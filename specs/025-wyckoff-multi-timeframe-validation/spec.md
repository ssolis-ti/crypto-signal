# Spec: Validación del edge Wyckoff en otros timeframes

## Contexto

El único edge validado del proyecto (Spring/Upthrust con volumen extremo en la
ruptura ≥2.5x, specs/017-018) solo corre en producción en **4h**
(specs/023-wyckoff-live-alerts/). Slice 024 confirmó que sumar otros
indicadores como señal independiente no aporta nada nuevo. La vía que sí tiene
evidencia a favor (el mecanismo ya probado funciona) es preguntar si el MISMO
mecanismo — no uno nuevo — también sostiene en otros timeframes, lo que
aumentaría la frecuencia de oportunidades sin inventar una señal nueva.

## Objetivo

Determinar en qué timeframes, además de 4h, el filtro "Spring/Upthrust +
volumen extremo en la ruptura ≥2.5x" (`WyckoffPrimitives`, ya en producción,
sin reimplementar) sostiene con el mismo rigor que specs/017/018: split
cronológico 70/30, win_rate≥60%, p<0.05, n≥30 en el tramo out-of-sample.

## Alcance

- Reutilizar `WyckoffPrimitives.detect_springs`/`detect_upthrusts` de
  `app/analyzers/indicators/wyckoff.py` TAL CUAL (código de producción, no se
  reimplementa — a diferencia de slice 024 donde los candidatos no estaban en
  producción).
- Timeframes a probar: **1h, 2h, 8h, 1d** (4h ya validado, se incluye como
  referencia/control).
- Mismo basket de 15 pares, misma ventana de 10 meses.
- Horizontes de evaluación expresados en tiempo real (24h, 72h, 7d, 14d),
  convertidos a velas según el timeframe de cada corrida.
- Fuera de alcance: conectar cualquier timeframe adicional a producción — eso
  es un slice de implementación posterior SOLO si algo confirma aquí (mismo
  patrón que 016 condicionado a 015, y 023 condicionado a 017/018).

## Requisitos funcionales

- FR-001: Descargar OHLCV real para cada timeframe candidato sobre el basket
  completo (10 meses).
- FR-002: Aplicar `WyckoffPrimitives` sin modificar su código ni su firma.
- FR-003: Filtrar eventos por volumen extremo en la ruptura (≥2.5x), igual
  umbral que producción.
- FR-004: Split cronológico 70/30 in-sample/out-of-sample por timeframe.
- FR-005: Reportar win rate, media de retorno y significancia (z-test) por
  timeframe y horizonte, en ambos tramos.
- FR-006: Veredicto explícito por timeframe: `confirmed` solo si
  out-of-sample cumple `win_rate≥60%` Y `p<0.05` Y `n≥30` en al menos un
  horizonte.
- FR-007: No modificar código de producción en este slice (script standalone).
- FR-008: Si algún timeframe confirma, reportar también la frecuencia de
  eventos (eventos/par/mes) para poder decidir si el volumen de alertas
  resultante es manejable para el operador.

## Criterios de éxito

- SC-001: Los timeframes candidatos evaluados en los 4 horizontes, con
  números reproducibles (script versionado).
- SC-002: Veredicto claro por timeframe, documentado en tasks.md Convergence.
- SC-003: Si algo confirma, queda un hallazgo activable con su frecuencia de
  eventos estimada; si nada confirma, el hallazgo negativo queda documentado.
