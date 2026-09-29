# Tasks: Clasificador de sentimiento/narrativa de Twitter

## Phase 1: Piloto cualitativo (lectura manual)

- [X] T001 Releer el contenido (no el conteo) de los eventos ya consultados
      en spec 028 (DOGE, ATOM, NEAR, BCH) y consultar 2 adicionales (BNB,
      LINK) para tener casos ganadores y perdedores en ambas direcciones.
- [X] T002 Documentar el contenido observado por evento y clasificar
      informalmente según el esquema propuesto (sentiment_extreme,
      social_spike_confirmed, catalyst_present).
- [X] T003 Identificar el patrón descriptivo (capitulación en springs
      ganadores, euforia sostenida en upthrusts perdedores) — explícitamente
      NO como hallazgo estadístico (n=5), sino como hipótesis a probar con
      más casos.

## Phase 2: Diseño del esquema formal

- [X] T004 Definir el esquema de clasificación de 4 campos
      (`sentiment_extreme`, `social_spike_confirmed`, `catalyst_present`,
      `wyckoff_aligned`) en `spec.md`.
- [X] T005 Documentar la asimetría detectada: para eventos `hot`, buscar
      capitulación; para eventos `cold`, la euforia SOSTENIDA invalida la
      señal en vez de confirmarla (no es un esquema simétrico simple).

## Phase 3: Decisión de escalado — devuelta al operador

- [X] T006 Documentar las dos opciones de arquitectura (manual por lotes vs.
      integración de LLM en el pipeline en vivo) con sus costos reales
      (secretos nuevos, costo variable, dependencia externa) sin implementar
      ninguna sin decisión explícita (FR/Constitution Principio IV).

## Phase 4: Convergence

Completado 2026-09-29. Se corrigió el error de specs/022/028 (medir conteo en
vez de contenido) tras señalamiento directo del operador. El piloto de 6
eventos (5 válidos, NEAR descartado por retorno anómalo -100.8%, posible
artefacto de datos) mostró un patrón cualitativo coherente con la teoría
Wyckoff: capitulación genuina en springs ganadores (LINK +9.98%, BCH +48.58%)
vs. sentimiento aún esperanzado en el spring perdedor (DOGE -6.23%); euforia
sostenida y viral en el upthrust perdedor (BNB -15.80%, siguió subiendo).

**Esto NO es una validación estadística** — n=5 no permite ningún z-test ni
split in-sample/out-of-sample como el resto del proyecto. Es un hallazgo
cualitativo que justifica invertir en escalarlo, no una confirmación.

**Decisión pendiente del operador**: escalar por lectura manual en lotes
(sin cambios de arquitectura) vs. integrar una llamada a LLM en el pipeline
de `WyckoffAlerter` para clasificación en vivo (requiere nueva dependencia +
API key + costo variable — cambio de arquitectura real, no un script de
validación más).

**Outcome**: `converged` con decisión pendiente — no se modificó código de
producción. El hallazgo cualitativo queda documentado como la primera pista
concreta y no descartada de todo el arco Twitter (022/028/030) — a
diferencia de esos dos, aquí SÍ hay una señal visible en los datos, solo que
todavía no está medida con rigor suficiente para confiar en ella.