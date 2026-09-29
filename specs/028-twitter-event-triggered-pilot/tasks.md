# Tasks: Piloto de Twitter/X event-triggered por altcoin

## Phase 1: Implementation

- [X] T001 `generate_altcoin_events.py`: generar eventos Wyckoff de altcoins
      (excluye BTC) con resultado conocido (ret_7d/ret_14d), reutilizando
      `WyckoffPrimitives` de `app/` (FR-001).
- [X] T002 Seleccionar muestra estratificada (10 ganadores/10 perdedores a
      14d) de los 67 eventos encontrados.
- [X] T003 Consultar `advanced_search_tweets` con query angosto (ticker +
      ventana corta) por evento (FR-002).

## Phase 2: Execution — detenida temprano (misma disciplina que spec 022)

- [X] T004 3 consultas diagnósticas ejecutadas (DOGE, ATOM, NEAR — alta y
      media capitalización, ventanas de 2 días a horas) antes de completar
      las 20 planeadas.
- [X] T005 Verificar si el conteo está por debajo del tope conocido (~19)
      (FR-003) — **no lo está: las 3 consultas devolvieron 18-19 con
      `has_more: false`**, igual patrón que spec 022.

## Phase 3: Convergence

Ejecutado 2026-09-29. Detenido en 3/20 consultas planeadas por el mismo
motivo que justificó parar spec 022 temprano: el patrón ya es inequívoco y
seguir no cambiaría la conclusión.

**Resultado: la corrección del operador (angostar a altcoin + ventana del
evento en vez de un conteo diario genérico de `$BTC`) NO resuelve el problema
de fondo.** Las 3 consultas — DOGE (top-10 cap, ventana 2 días), ATOM (media
cap, ventana 1 día), NEAR (media cap, ventana de horas) — devolvieron todas
18-19 tweets con `has_more: false` y `next_cursor: null`. El patrón es
idéntico al de spec 022 independientemente de:
- Tamaño de la moneda (DOGE tiene mucho más volumen de conversación que
  ATOM/NEAR, y aun así el conteo fue igual de plano).
- Ancho de la ventana (2 días vs. 1 día vs. unas pocas horas — sin
  diferencia).

**Lectura correcta del comportamiento de la API**: `advanced_search_tweets`
con `product=Latest` no cuenta ni pagina el total de tweets que matchean en
la ventana — devuelve una página fija de ~18-19 tweets más recientes antes de
`until:`, punto. No hay manera de que el conteo refleje volumen real de
conversación con este endpoint, sin importar cómo se acote el query.

**Conclusión**: la idea de fondo (Twitter como confirmación de un rumor antes
de la viralización, específica para altcoins) sigue sin estar descartada —
pero **este endpoint específico (`advanced_search_tweets`) no sirve para
medirla, ni con la corrección propuesta por el operador**. spec 022 ya había
recomendado revisar si `getxapi` tiene un endpoint dedicado de conteo/volumen
distinto de búsqueda de tweets individuales — esa recomendación se reafirma
con más evidencia ahora (2 intentos distintos, mismo resultado). No se
recolectó la muestra completa de 20 eventos porque el método de medición ya
está descartado, no el dataset.

**Outcome**: `converged` — hallazgo negativo confirmado con evidencia
adicional. Los 67 eventos altcoin generados (`altcoin_events.json`) quedan
disponibles para un futuro intento SI aparece un endpoint de conteo/volumen
real en getxapi, o si se decide explorar `get_trends`/`get_trend_locations`
(trending topics de X, no búsqueda de tweets) como señal alternativa — no
explorado en este slice. No se conecta nada a producción (FR-005 cumplido).