# Spec: Validación de cruces TA no probados (ma_crossover, sqzmom)

## Contexto

El bot ya tiene implementados (pero sin conectar a alertas en producción, y sin
validar con la misma disciplina que Wyckoff) dos indicadores de cruce con tesis
razonable para complementar la baja frecuencia de alertas Wyckoff
(specs/023-wyckoff-live-alerts/):

- `app/analyzers/indicators/ma_crossover.py`: golden/death cross EMA rápida vs
  lenta (configurable, por defecto EMA10/EMA50).
- `app/analyzers/indicators/sqzmom.py`: Squeeze Momentum (Bollinger vs Keltner) —
  señala liberación de compresión de volatilidad con dirección de momentum.

Todo lo demás probado en el arco Wyckoff (specs/007, 011, 017, 019, 021) como
señal aislada no sobrevivió el holdout out-of-sample. Este slice aplica la misma
vara a estos dos candidatos antes de considerar conectarlos a producción.

## Objetivo

Determinar, con el mismo estándar que specs/017 (split cronológico 70/30,
`win_rate >= 60%`, `p < 0.05`, `n >= 30` en el tramo out-of-sample), si alguno de
estos dos cruces aporta un edge direccional real y accionable — solo o combinado
con un filtro de volumen extremo (el único mecanismo que sí funcionó en Wyckoff).

## Alcance

- Basket, timeframe (4h) y ventana histórica (10 meses) idénticos a
  specs/017/018/019/021 para comparabilidad directa.
- Horizontes de evaluación: 24h, 72h, 7d, 14d (mismos que spec 015).
- Candidatos:
  1. `ma_crossover` (EMA10/EMA50) solo.
  2. `ma_crossover` + volumen extremo (>=2.5x) en la vela del cruce.
  3. `sqzmom` (liberación de squeeze con momentum direccional) solo.
  4. `sqzmom` + volumen extremo (>=2.5x) en la vela de liberación.
- Fuera de alcance: conectar cualquier resultado a alertas de producción (eso
  queda para un slice posterior SOLO si algo confirma aquí, igual que 016 quedó
  condicionado a 015).

## Requisitos funcionales

- FR-001: Recolectar eventos de cruce (`ma_crossover`) y de liberación de squeeze
  (`sqzmom`) sobre el basket completo, reimplementando la lógica de forma
  vectorizada (no solo la última vela) para poder evaluar histórico.
- FR-002: Calcular retorno direccional esperado (a favor de la señal) en cada
  horizonte, sin look-ahead (igual método que specs anteriores).
- FR-003: Split cronológico 70/30 in-sample/out-of-sample, nunca mezclado.
- FR-004: Reportar win rate, media de retorno, y significancia (z-test normal)
  por candidato y horizonte, en ambos tramos.
- FR-005: Veredicto explícito por candidato: `confirmed` solo si
  out-of-sample cumple `win_rate >= 60%` Y `p < 0.05` Y `n >= 30`.
- FR-006: No modificar código de producción en este slice (script standalone,
  igual que specs/017/019/021).

## Criterios de éxito

- SC-001: Los 4 candidatos evaluados en los 4 horizontes, con números
  reproducibles (script versionado).
- SC-002: Veredicto claro (`confirmed` / `did_not_replicate` /
  `insufficient_sample`) por candidato, documentado en tasks.md Convergence.
- SC-003: Si algo confirma, queda un hallazgo activable para un slice de
  implementación; si nada confirma, el hallazgo negativo queda documentado
  (evita repetir el trabajo).
