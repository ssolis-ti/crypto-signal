# Tasks: Filtros de contexto de volumen (CMF/PVT/NVI)

## Phase 1: Implementation

- [X] T001 `validate_volume_context.py`: reutilizar `WyckoffPrimitives` de
      `app/` sin modificarla para generar el mismo set de eventos que
      producción (FR-001, FR-002, FR-006).
- [X] T002 Anotar cada evento con CMF(20)/PVT/NVI (TA-Lib nativo) en la vela
      de confirmación (FR-001, FR-002).
- [X] T003 Split cronológico 70/30, z-test de win rate, comparación explícita
      contra baseline de producción (FR-003, FR-004, FR-005, SC-003).

## Phase 2: Execution

- [X] T004 Ejecutar contra basket real (10 meses, 4h, mismos 15 pares) dentro
      de `crypto-signal:dev`.
- [X] T005 Documentar resultados y veredicto en la sección Convergence.

## Phase 3: Convergence

Ejecutado 2026-09-29 contra basket real (14/15 pares, mismo caso MATIC/USDT
sin datos). Baseline de producción (Spring/Upthrust + volumen extremo, sin
filtro adicional) out-of-sample: 66.0% a 7d (n=97, p=0.0016), 62.9% a 14d
(n=97, p=0.0111) — reproduce specs/017/018/025 como control.

| Candidato | in-sample matching | out-of-sample matching | Veredicto mecánico | Veredicto real (ver nota) |
|---|---|---|---|---|
| CMF(20) alineado | 68/224 | 19/97 | `insufficient_sample` | insuficiente |
| PVT tendencia alineada | 14/224 | 13/97 | `insufficient_sample` | insuficiente |
| NVI tendencia alineada | 142/224 | 43/97 | `confirmed` (script) | **`did_not_replicate`** — ver nota |

**Nota importante sobre NVI — el script marcó "confirmed" pero es una lectura
mecánica incompleta.** El filtro exige `win_rate>=60%`, `p<0.05` Y mejora
sobre el baseline **solo en el tramo out-of-sample** (72.1%, n=43, p=0.0038
vs. baseline out-of-sample 62.9%). Pero al comparar contra el baseline
**in-sample** (consultado aparte, no estaba en el script original):
NVI-filtrado in-sample 14d = 55.6% (p=0.1794, no significativo) vs. baseline
in-sample sin filtro = 58.9% (p=0.0075, sí significativo) — **el filtro
EMPEORA el win rate in-sample y solo "mejora" out-of-sample**. Esta es
exactamente la firma de inestabilidad/sobreajuste que specs/017 y 021 ya
identificaron como ruido, no como edge real (el propio estándar del proyecto,
establecido desde spec 017, exige lift *consistente* en ambos tramos, no solo
que el tramo out-of-sample pase la vara mecánica). Se corrige el veredicto
automático del script: **NVI no confirma** bajo el estándar real del
proyecto.

CMF y PVT alineados son demasiado raros (solo 14-19 eventos out-of-sample)
para evaluar con cualquier confianza — el volumen extremo Wyckoff ya es una
condición restrictiva, y exigir además alineación de CMF/PVT dejó muestras
insuficientes en un dataset de 10 meses.

**Conclusión**: ninguno de los 3 filtros de contexto de volumen mejora el
mecanismo ya validado. Se mantiene el volumen extremo en la ruptura como
único filtro necesario y suficiente. No se conecta nada a producción (FR-006
cumplido).

**Outcome**: `converged` — hallazgo negativo documentado, con una corrección
explícita al veredicto mecánico del script (lección: agregar SIEMPRE el
baseline in-sample a los scripts futuros, no solo el out-of-sample, para que
la comparación de consistencia sea automática y no dependa de una revisión
manual posterior).
