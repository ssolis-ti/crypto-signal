# Tasks: Patrones de vela como filtro adicional sobre el edge Wyckoff

## Phase 1: Implementation

- [X] T001 `validate_candle_patterns.py`: reutilizar `WyckoffPrimitives` de
      `app/` sin modificarla, calcular patrones `CDL*` en la vela de
      confirmación (FR-001, FR-005).
- [X] T002 Split cronológico 70/30, baseline in-sample Y out-of-sample
      reportados lado a lado (FR-002, FR-003).
- [X] T003 Veredicto `confirmed` solo con lift consistente en ambos tramos,
      no solo vara mecánica out-of-sample (FR-004, lección de spec 027).

## Phase 2: Execution

- [X] T004 Ejecutar contra basket real (10 meses, 4h, mismos 15 pares) dentro
      de `crypto-signal:dev`.
- [X] T005 Documentar resultados y veredicto en la sección Convergence.

## Phase 3: Convergence

Ejecutado 2026-09-29 contra basket real (14/15 pares, mismo caso MATIC/USDT
sin datos). Baseline de producción reproducido como control (66.0% a 7d,
62.9% a 14d out-of-sample — igual que specs/017/018/025/027).

| Candidato | in-sample matching | out-of-sample matching | Veredicto |
|---|---|---|---|
| Cualquier patrón CDL* alineado | 149/224 (66%) | 60/97 (62%) | `did_not_replicate` — en 14d el out-of-sample "mejoró" (66.7% vs. baseline 62.9%) pero el in-sample fue PEOR que su propio baseline (57.7% vs. 58.9%) → mismo patrón de inconsistencia que NVI en spec 027, correctamente detectado y descartado por el chequeo automático |
| Patrones "core" (engulfing, hammer, morning/evening star, etc.) alineados | 59/224 | 22/97 | `insufficient_sample` — exigir un patrón de reversión "de manual" sobre el evento ya raro (volumen extremo) deja muy pocos casos en 10 meses |

**Validación del proceso**: el chequeo de consistencia in-sample/out-of-sample
agregado tras la lección de spec 027 funcionó como se esperaba — capturó
automáticamente el mismo tipo de falso positivo (candidato 1 a 14d) sin
necesitar una revisión manual posterior. Se marca explícitamente como
`inconsistent_in_sample_worse` en vez de `confirmed`.

**Conclusión**: ni un filtro amplio (cualquier patrón CDL* reconocido) ni uno
curado (patrones de reversión "core") aportan un edge adicional consistente
sobre el volumen extremo ya validado. Se cierra la tercera y última vía
priorizada en specs/026 (patrones de vela) sin hallazgo. No se conecta nada a
producción (FR-005 cumplido).

**Outcome**: `converged` — hallazgo negativo documentado. Con esto se agotan
las tres vías identificadas en specs/026 sobre el mecanismo ya validado
(candle patterns aquí, volumen de contexto en spec 027, Twitter en spec 028)
sin encontrar ninguna mejora. El volumen extremo en la ruptura, solo en 4h,
sigue siendo el único edge necesario y suficiente del proyecto.
