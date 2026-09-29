# Research: Catálogo amplio de señales candidatas (TA-Lib, order book, patrones de vela)

**Fecha**: 2026-09-29 | Continuación de specs/020 (order flow/social) y specs/024-025
(que mostraron que seguir puliendo el propio mecanismo Wyckoff, o probar cruces de
medias/volatilidad, no rinde más). Este research responde directamente al pedido del
operador de no encerrarse en Wyckoff y mirar también order book, volumen y funciones
de TA-Lib ya disponibles en la imagen.

## 1. Qué hay realmente en la librería TA-Lib pineada (verificado en vivo)

La imagen `crypto-signal:dev` trae una build de TA-Lib bastante más completa que la
"clásica" — 150+ funciones en 9 grupos (verificado con `talib.get_function_groups()`):

| Grupo | Funciones ya usadas en el bot | Funciones sin usar / sin probar (candidatas) |
|---|---|---|
| Momentum | RSI, MACD, MACDFIX(macd_cross), ADX, MFI, STOCHRSI | AROON, CCI, CMO, DX, MOM, ROC, TRIX, ULTOSC, WILLR, KDJ, TSI, VORTEX, AO, FRACTAL, ERI |
| Overlap Studies | EMA, SMA, BBANDS | DONCHIAN, SUPERTREND, KC (Keltner, ya replicado a mano en `sqzmom.py`), HMA, VWMA, ZLEMA, SAR |
| Volume Indicators | OBV (deshabilitado), VWAP (informante) | **AD, ADOSC, CMF, EFI, NVI, PVI, PVO, PVT, RVOL** |
| Pattern Recognition | Ninguna en producción (`candle_recognition.py` existe, deshabilitado) | 60+ patrones de vela (CDLENGULFING, CDLHAMMER, CDLMORNINGSTAR, CDLDOJI, etc.) |
| Volatility | — | ATR (ya se usa dentro de `WyckoffPrimitives.relative_range`), NATR, MASSI, RVI |
| Statistic | — | CORREL, LINEARREG_SLOPE, STDDEV, PERCENTILE/PERCENTRANK |
| Cycle | — | Hilbert Transform (HT_*) — baja prioridad, diseñado para series con ciclicidad estable, cripto no calza bien con ese supuesto |

**Lectura**: hay mucho más disponible de lo que se probó hasta ahora, pero el patrón de
specs/007-025 (todo lo aislado falla holdout; solo el volumen extremo combinado con la
estructura Wyckoff sobrevivió) sugiere que la ganancia no va a venir de un indicador
nuevo solo, sino de indicadores que — como el volumen en Wyckoff — capturan algo
estructural (absorción, agotamiento) en vez de momentum genérico.

### Candidatos priorizados por tesis (no por popularidad)

1. **Volume Indicators sin probar: `CMF` (Chaikin Money Flow), `PVT` (Price Volume
   Trend), `NVI`/`PVI`** — miden acumulación/distribución de forma distinta al volumen
   relativo simple que ya funciona en Wyckoff. Tesis: podrían servir como filtro de
   *contexto* (¿hay acumulación de fondo antes del Spring?) más que como señal aislada
   — evitando el error de specs/017/019 (probar todo como señal standalone en vez de
   contexto).
2. **Patrones de vela ya codificados (`candle_recognition.py`) en la vela de
   confirmación de un Spring/Upthrust** — no como señal propia (specs/007-025 ya
   mostraron que señales aisladas no rinden) sino como filtro adicional sobre el
   mecanismo YA validado, mismo patrón que "volumen extremo" en spec 017. Ej.:
   ¿el Spring confirma además con un Hammer o Engulfing alcista?
3. **CORREL (rolling) ALT vs BTC** — ya existe lógica de correlación en
   `app/analyzers/indicators/derived.py`/config (`correlation.scoring`), pero nunca se
   validó con holdout real como filtro del propio SignalEnhancer (que ya está
   invalidado dos veces). Podría valer la pena aislarlo y probarlo solo, no como parte
   del score compuesto.
4. **SUPERTREND / DONCHIAN** como filtro de régimen (similar tesis que la alineación
   EMA-HTF de spec 017, que fue mayormente redundante) — prioridad baja, ya hay
   evidencia indirecta de que "filtro de tendencia HTF" no aporta.

## 2. Order book / L2 depth — verificado en vivo, con una limitación estructural importante

Se probó `ccxt`'s `fetch_order_book('BTC/USDT', limit=20)` contra Binance en vivo:
**funciona perfectamente** — devuelve bids/asks reales con profundidad configurable,
sin necesidad de credenciales (endpoint público).

**Pero hay un límite duro para este proyecto**: Binance (como la gran mayoría de
exchanges) **no expone un endpoint histórico de profundidad de order book**. Solo se
puede pedir el snapshot ACTUAL. A diferencia de OHLCV (que sí tiene historial completo
vía `fetch_ohlcv`), no hay forma de "pedir el order book de hace 3 meses" — no existe
en la API.

Esto significa que **cualquier señal de order book (imbalance bid/ask, paredes de
liquidez, etc.) no se puede validar con el mismo rigor de holdout 70/30 que usamos en
todo el proyecto hasta ahora**, porque no hay forma de generar el dataset histórico
para probarlo. Las únicas opciones reales son:

1. **Recolectar en vivo desde ahora**: correr un colector que guarde snapshots de
   order book cada N minutos, y recién en unas semanas/meses tener suficiente historia
   propia para backtestear. Costo: tiempo de espera antes de poder validar nada
   (semanas), más almacenamiento.
2. **Comprar datos históricos de un vendor de tick data** (ej. Kaiko, Tardis.dev,
   CryptoDataDownload) — fuera del alcance de "sin custodia, read-only" del proyecto en
   términos de complejidad/costo, y contradice el principio de mantener el proyecto
   simple y sin dependencias externas de pago.
3. **Usarlo solo en vivo, sin backtest** — conectarlo directamente a producción sin
   validación histórica rompería el Principio III de la constitución ("Validate Before
   You Trust a Heuristic"), algo que este proyecto no ha hecho ni una vez en 25 slices.

**Conclusión sobre order book**: la idea es válida y técnicamente factible de
*implementar*, pero no es factible de *validar con el rigor que este proyecto exige*
sin antes invertir semanas en recolección propia. No es un "no", es un "no todavía, y
el costo es tiempo de espera, no complejidad de código".

## 3. Recomendación priorizada

| # | Candidato | Factible de validar YA con datos históricos | Prioridad |
|---|---|---|---|
| 1 | Patrones de vela como filtro adicional sobre Spring/Upthrust confirmado | Sí | **Alta** — mismo patrón exitoso que volumen extremo |
| 2 | CMF/PVT/NVI como filtro de contexto (no señal aislada) sobre Spring/Upthrust | Sí | **Alta** — misma lógica |
| 3 | Twitter event-triggered por altcoin (idea del operador, mensaje anterior) | Sí (datos ya verificados accesibles) | **Alta** — ángulo no técnico, complementa a los dos anteriores |
| 4 | CORREL ALT/BTC aislado | Sí | Media |
| 5 | SUPERTREND/DONCHIAN como filtro de régimen | Sí | Baja (ya hay evidencia indirecta en contra) |
| 6 | Order book imbalance | No todavía — requiere recolección propia semanas/meses | Bloqueada por datos, no descartada |

La diferencia clave respecto a specs/024-025 (que fallaron): ahí probamos indicadores
como señal *standalone*. Los candidatos 1, 2 y 4 aquí se plantean como **filtro
adicional sobre el mecanismo YA validado** (Spring/Upthrust + volumen extremo) — igual
lógica que hizo funcionar el volumen extremo en spec 017. Es la vía con mejor tesis
disponible hoy.
