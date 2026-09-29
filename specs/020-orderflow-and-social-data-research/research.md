# Investigación: Order Flow/Order Book y Datos de Twitter/X para crypto-signal

**Estado**: SOLO INVESTIGACIÓN (con 2 verificaciones concretas ya hechas) — no implica código nuevo
todavía. Continuación natural de `specs/017-019` (donde el volumen extremo en la ruptura quedó como
el único edge validado, y ni TA clásico ni confluencia multi-timeframe agregaron nada más).

**Fecha**: 2026-09-28 | **Motivación**: el operador pidió pensar cómo extraer order flow/order book
y sumar datos de Twitter/X (getxapi.com), de forma eficaz, ordenada e innovadora.

---

## 1. Order Flow / Order Book — qué es real y qué no

### 1.1 Hallazgo clave (verificado, no especulado): ya tenemos order flow real, gratis, retroactivo

Probé directamente el endpoint crudo de Binance (`publicGetKlines`, el mismo que CCXT usa por debajo
de `fetch_ohlcv`) y confirmé que **cada vela ya trae un desglose comprador/vendedor que CCXT descarta
silenciosamente**:

```
[timestamp, open, high, low, close, volume, close_time, quote_volume,
 number_of_trades, taker_buy_base_volume, taker_buy_quote_volume, ignore]
                                            ^^^^^^^^^^^^^^^^^^^^^
                                            esto es lo que perdemos hoy
```

`taker_buy_base_volume` es el volumen que compró agresivamente (cruzando el spread contra vendedores
pasivos) dentro de esa vela. `taker_buy_ratio = taker_buy_base_volume / volume` te dice, para
**cualquier vela histórica de los últimos 10 meses que ya descargamos dos veces**, si el volumen de
esa vela fue dominado por compradores agresivos o por vendedores agresivos — sin necesitar una sola
llamada adicional a la API más de las que ya hacemos, y sin esperar ni un día para empezar a
validarlo.

**Por qué esto importa para Wyckoff específicamente**: nuestro filtro validado (slice 017) mide
"¿hubo mucho volumen en la ruptura?" (`relative_volume >= 2.5`), pero no distingue *quién* generó ese
volumen. Una ruptura falsa (Spring) con mucho volumen dominado por VENTA agresiva que igual no logra
bajar más el precio es una lectura de absorción mucho más fiel al método Wyckoff real que "hubo
volumen alto" a secas — es la diferencia entre "esfuerzo vendedor absorbido por compradores" y
"esfuerzo comprador genuino", algo que el ratio de esfuerzo/resultado actual (`WyckoffPrimitives`) no
puede ver porque solo mira precio y volumen total, nunca la dirección del taker.

### 1.2 Qué NO es recuperable retroactivamente

El order book L2 completo (profundidad de bids/asks) **no se guarda históricamente en ningún
exchange de forma pública y gratuita** — solo existe "ahora". Para tener esa serie histórica hay que
capturarla en vivo desde este momento en adelante (vía WebSocket, `wss://.../depth`), lo que significa
semanas o meses de recolección antes de poder validar nada con el mismo rigor que usamos en 007-019.
Mismo problema con el spread bid-ask histórico.

**Decisión propuesta**: diferir el order book L2 — es la opción más cara y más lenta de validar, y ya
tenemos un proxy de order flow (taker buy/sell ratio) disponible hoy mismo, sin espera.

### 1.3 Bonus disponible (retroactivo, con historia más corta): datos de Futuros

Binance Futures expone públicamente (sin API key) `topLongShortAccountRatio`,
`globalLongShortAccountRatio`, `fundingRate` histórico y `openInterestHist` — retroactivos pero con
ventana de retención más corta que los klines de spot (típicamente 30-180 días según el endpoint, hay
que confirmarlo endpoint por endpoint). Como crypto-signal opera en spot y de solo lectura (Principio
I: nunca custodia ni apalancamiento propio), esto solo serviría como **contexto informativo** (¿el
mercado de futuros está mayoritariamente largo o corto cuando aparece nuestra señal?), nunca para
operar futuros nosotros mismos. Prioridad más baja que 1.1 por la ventana de historia más corta.

---

## 2. Twitter/X vía getxapi — verificado en vivo, no solo leído en la documentación

### 2.1 Hallazgo clave (verificado): SÍ hay búsqueda histórica real, no solo "lo reciente"

Probé `advanced_search_tweets` con operadores `since:`/`until:` apuntando a una fecha de **hace 3
meses** (`$BTC since:2026-07-01 until:2026-07-02`) y devolvió 19 tweets reales de esa fecha exacta —
no un error, no solo contenido reciente. Esto significa que, a diferencia del order book, **sí
podemos backtestear Twitter contra los 330 eventos ya identificados**, no solo monitorear hacia
adelante.

### 2.2 La limitación real no es la profundidad histórica, es el volumen de llamadas

Cada consulta devuelve un puñado de tweets (paginable, pero acotado) y probablemente tiene límites de
tasa/costo como cualquier API de pago. Repetir esto para los 330 eventos × 14 pares × varias ventanas
de tiempo sería centenares o miles de llamadas — no es el punto de partida correcto.

**Decisión propuesta**: pilotear en un subconjunto chico y de alto valor antes de escalar — por
ejemplo, solo los eventos confirmados de BTC/USDT (el par con más volumen de tweets y mejor relación
señal/ruido), midiendo:

1. **Volumen de menciones** (`$BTC` tweet count en las 24h previas al evento, comparado contra el
   promedio de ese par) — "pico de atención" como proxy de que la multitud ya está mirando esa
   moneda, sin necesitar NLP.
2. **Inclinación direccional simple** (conteo de palabras clave: "buy/long/moon" vs "sell/short/dump"
   en esos tweets) antes de invertir en un clasificador de sentimiento más sofisticado — empezar
   simple, con la misma disciplina de "no sobre-construir antes de validar" de todo este proyecto.

### 2.3 Advertencia epistemológica (ya la vimos en los resultados de la prueba)

Los resultados reales de la búsqueda incluyen bots evidentes, contenido de "farming" de engagement, y
al menos una cuenta que literalmente auto-genera "análisis técnico" por keyword — Twitter/X cripto
está lleno de ruido y manipulación coordinada (grupos de pump). Cualquier correlación encontrada
necesita el mismo tratamiento in-sample/out-of-sample que ya aplicamos en 017 y 019, con más
escepticismo todavía que con datos de precio, no menos.

---

## 3. Roadmap propuesto, ordenado por costo/valor

| # | Iniciativa | Costo | Espera para validar | Valor esperado |
|---|---|---|---|---|
| 1 | **Taker buy/sell ratio** en los eventos ya detectados (mismos 330, misma metodología in/out-of-sample de 017/019) | Ninguno — dato ya disponible, cero llamadas nuevas | Inmediato | Alto — mide algo que el filtro actual no ve |
| 2 | **Piloto de atención en Twitter/X** (solo BTC, solo eventos confirmados) vía getxapi | Llamadas a una API de pago, acotadas a un subconjunto chico | Inmediato (historia real disponible) | Medio, incierto — requiere validarlo con el mismo rigor, y el dato es ruidoso |
| 3 | Contexto de Futuros (long/short ratio, funding) | Bajo (endpoints públicos) | Inmediato pero con historia más corta | Bajo-medio, es contexto no una señal propia |
| 4 | Order book L2 / profundidad | Alto (requiere correr un collector en vivo) | Semanas/meses antes de poder validar nada | Desconocido — es la apuesta más cara y más lenta |

**Recomendación de orden**: 1 → 2 → 3 → 4. La opción 1 es la más eficaz posible: no cuesta nada, no
espera nada, y prueba una hipótesis genuinamente nueva (dirección del taker, no solo magnitud del
volumen) sobre datos que ya tenemos. La opción 2 es la más innovadora de las accesibles hoy, pero
debe pilotearse chico antes de escalar el gasto de API. La 3 es un complemento barato pero de bajo
impacto. La 4 se difiere explícitamente por su costo/tiempo de validación.

## Siguiente paso concreto

Si el operador aprueba, el slice 021 implementaría la opción 1 (taker buy/sell ratio) ahora mismo —
no requiere ninguna decisión de costo/API externa, solo extender el fetch que ya hacemos para leer 2
columnas que hoy se descartan, y correr la misma prueba in-sample/out-of-sample de slices 017/019.
La opción 2 (piloto de Twitter) quedaría como slice 022, con alcance explícitamente acotado a BTC
para no gastar de más en la API de getxapi antes de saber si el dato sirve.
