# Tasks: Validación del edge Wyckoff en otros timeframes

## Phase 1: Implementation

- [X] T001 `validate_wyckoff_timeframes.py`: reutilizar `WyckoffPrimitives` de
      `app/` sin modificarla, iterar sobre 1h/2h/4h(control)/8h/1d (FR-001,
      FR-002, FR-007).
- [X] T002 Filtrar por volumen extremo ≥2.5x en la ruptura, mismo umbral que
      producción (FR-003).
- [X] T003 Convertir horizontes reales (24h/72h/7d/14d) a velas según el
      timeframe de cada corrida.
- [X] T004 Split cronológico 70/30 por timeframe, z-test de win rate, veredicto
      por horizonte y frecuencia de eventos/par/mes (FR-004, FR-005, FR-006,
      FR-008).

## Phase 2: Execution

- [X] T005 Ejecutar contra basket real (10 meses, mismos 15 pares) dentro de
      `crypto-signal:dev`.
- [X] T006 Documentar resultados y veredicto en la sección Convergence.

## Phase 3: Convergence

Ejecutado 2026-09-29 contra basket real (14/15 pares — MATIC/USDT sin datos en
todos los timeframes, mismo caso que slice 024, probable rename a POL/USDT).
10 meses, 5 timeframes (1h, 2h, 4h control, 8h, 1d).

**Resultado: solo 4h (el timeframe ya en producción) confirma.** Ningún otro
timeframe sostiene el mismo mecanismo (Spring/Upthrust + volumen extremo
≥2.5x) con el rigor exigido:

| Timeframe | Eventos totales | Frecuencia (ev/par/mes) | Veredicto out-of-sample |
|---|---|---|---|
| 1h | 1737 | ~12.41 | `did_not_replicate` — ningún horizonte significativo out-of-sample |
| 2h | 754 | ~5.39 | `did_not_replicate` — in-sample se veía bien (24h/72h *sig*) pero no sostiene out-of-sample |
| **4h (control)** | 321 | ~2.29 | **`confirmed`** — 7d: 66.0% (n=97, p=0.0016); 14d: 62.9% (n=97, p=0.0111) |
| 8h | 133 | ~0.95 | `did_not_replicate` — ninguna significancia en ningún tramo |
| 1d | 38 | ~0.27 | `insufficient_sample` — muy pocos eventos incluso antes del split |

**Lectura**: el control (4h) reproduce el hallazgo de specs/017-018
(win_rate>=60%, p<0.05 en 7d y 14d out-of-sample), confirmando que el método
es sólido. Los timeframes más rápidos (1h, 2h) generan muchos más eventos
(5-12x más que 4h) pero el filtro de volumen extremo pierde su poder
predictivo — probablemente porque en velas cortas el "volumen extremo" es más
ruido de microestructura que una señal real de absorción institucional. El
timeframe más lento (1d) es demasiado escaso en 10 meses para siquiera
evaluar (38 eventos totales en 14 pares).

**Conclusión**: 4h no es una elección arbitraria — es el único timeframe,
entre los 5 probados, donde el mecanismo Wyckoff de volumen extremo sostiene
holdout real. No hay evidencia para sumar otro timeframe a producción. La vía
de "más frecuencia de oportunidades sin inventar señal nueva" tampoco tiene
sustento aquí — igual que slice 024 con otros indicadores, el resultado
honesto es negativo. No se conecta nada a producción (FR-007 cumplido).

**Outcome**: `converged` — hallazgo negativo documentado, ningún código de
producción modificado. Con esto se cierran las dos vías más prometedoras
post-slice-023 (nuevos indicadores en 024, nuevos timeframes en 025) sin
encontrar nada adicional; cualquier expansión futura de frecuencia de alertas
necesitaría una hipótesis genuinamente nueva, no una variación del mecanismo
ya validado.
