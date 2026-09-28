# Investigación: Método Wyckoff y Temporalidades Fractales para crypto-signal

**Estado**: SOLO INVESTIGACIÓN — no implica ninguna spec, plan ni código todavía. Este documento
existe para que el operador decida si vale la pena convertir alguna parte en un slice real, con la
misma disciplina de validación histórica que ya aplicamos en `specs/007-.../` y
`specs/011-.../` antes de que cualquier heurístico nuevo pueda influir en una alerta real.

**Fecha**: 2026-09-28 | **Motivación**: tras confirmar (slices 007 y 011) que el scoring actual de
`SignalEnhancer` no tiene valor predictivo medible — e incluso anti-correlaciona en macd_cross a 72h
con significancia estadística — el operador propuso explorar el método Wyckoff como una hipótesis
estructural distinta, en vez de seguir ajustando pesos ad-hoc sobre los mismos indicadores.

---

## 1. El método Wyckoff — fundamentos

Richard D. Wyckoff (1873-1934) desarrolló su método observando el comportamiento de los grandes
operadores ("el Operador Compuesto" — un constructo analítico que trata todo el "dinero inteligente"
del mercado como si fuera un solo actor racional acumulando o distribuyendo posición). El método se
apoya en **tres leyes**:

1. **Ley de Oferta y Demanda**: el precio sube cuando la demanda excede la oferta, y baja cuando la
   oferta excede la demanda — la base de cualquier análisis de precio, pero Wyckoff la lee a través
   del volumen, no solo del precio.
2. **Ley de Causa y Efecto**: el "efecto" (la magnitud del movimiento subsiguiente) es proporcional a
   la "causa" acumulada durante un rango de acumulación o distribución previo. La causa se mide
   (históricamente, con Point & Figure; hoy también aproximable con ancho del rango × tiempo/volumen
   acumulado dentro de él).
3. **Ley de Esfuerzo vs. Resultado** ("Effort vs. Result"): el volumen (esfuerzo) y el movimiento de
   precio (resultado) deben ser proporcionales. Cuando divergen — mucho volumen y poco movimiento de
   precio, o viceversa — es una señal de que algo está cambiando bajo la superficie (absorción,
   clímax, agotamiento). **Esta ley es la más directamente computable desde OHLCV crudo**, sin
   necesitar interpretación subjetiva de patrones — es el punto de entrada más objetivo al método.

### Las 4 fases del ciclo de mercado

Acumulación → Markup (tendencia alcista) → Distribución → Markdown (tendencia bajista) → (repite).
Wyckoff sostiene que el precio pasa la mayor parte del tiempo en rangos de acumulación/distribución
(construyendo "causa"), no en tendencia — la tendencia es la liberación breve de esa causa acumulada.

### Los esquemas canónicos (Acumulación y Distribución, Fases A-E)

La formalización moderna del método (popularizada por el Wyckoff Stock Market Institute y ampliamente
documentada) divide cada rango en fases con eventos característicos:

**Acumulación**:
- **Fase A** (detención de la tendencia bajista previa): *Preliminary Support (PS)*, *Selling
  Climax (SC)* — clímax de volumen extremo con reversión de precio —, *Automatic Rally (AR)*,
  *Secondary Test (ST)* del mínimo del SC con volumen decreciente.
- **Fase B** (construcción de la causa): oscilación dentro del rango definido por AR y SC; múltiples
  *ST*; el "Operador Compuesto" acumula posición discretamente.
- **Fase C** (la prueba definitiva): el **Spring** — una ruptura *falsa* por debajo del soporte del
  rango, que rápidamente revierte hacia adentro (barre stops, testea si queda oferta real) — o un
  *Test* menos dramático sin nuevo mínimo. El spring con bajo volumen en la vuelta es la señal más
  citada de acumulación real.
- **Fase D**: *Sign of Strength (SOS)* — un rally con volumen y rango expandido que rompe la
  resistencia del rango —, seguido de un *Last Point of Support (LPS)* — un pullback de bajo volumen
  que no revisita el mínimo.
- **Fase E**: el precio sale del rango en tendencia alcista sostenida (markup).

**Distribución** es el espejo: *Preliminary Supply (PSY)*, *Buying Climax (BC)*, *Automatic Reaction
(AR)*, *Secondary Test (ST)*, el **Upthrust (UT)** (ruptura falsa por ENCIMA de la resistencia que
revierte hacia adentro), *Sign of Weakness (SOW)*, *Last Point of Supply (LPSY)*.

### Por qué esto es "fractal"

Wyckoff mismo señalaba que estos patrones se repiten en toda escala temporal: un spring en el gráfico
semanal tiene la misma estructura lógica que un spring en el gráfico de 15 minutos — solo cambia la
escala. La práctica estándar es **top-down multi-timeframe**:

1. **Temporalidad alta** (ej. 1W/1D): determina el sesgo estructural — ¿estamos en un rango de
   acumulación, distribución, o en tendencia establecida? Este es el contexto que no debería
   contradecirse.
2. **Temporalidad media** (ej. 4h/1D): identifica el rango de trading vigente y dónde está el precio
   dentro de él (¿cerca del soporte tras un spring? ¿en fase D tras un SOS?).
3. **Temporalidad baja** (ej. 1h/15m): timing de entrada preciso — esperar el *test* de bajo volumen
   después del spring/SOS antes de considerar la señal confirmada.

Esto es directamente compatible con la arquitectura actual: `DataManager.get_ohlcv(exchange, pair,
timeframe)` ya soporta cualquier timeframe con caché, así que no hay obstáculo técnico para pedir
1D+4h+1h del mismo par en el mismo ciclo — es una composición de datos ya disponibles, no una
capacidad nueva del pipeline.

---

## 2. Qué es objetivamente computable desde OHLCV (y qué no)

Hay que ser honesto sobre esto, con la misma disciplina que aplicamos al validar `SignalEnhancer`:
gran parte del método Wyckoff es lectura de gráfico basada en gestalt/experiencia (¿esto "parece" un
spring o solo ruido?), no reglas matemáticas exactas. Traducirlo a código siempre produce una
**aproximación operacional**, no "el método real" — el mismo tipo de honestidad que ya aplicamos al
reconocer que el proxy de sentiment en `MarketContext` es una simplificación.

### Alto grado de objetividad (buenos candidatos a computar directamente)

- **Effort vs. Result**: `rango_de_precio / volumen_relativo` (normalizado por promedios móviles) es
  un ratio simple y 100% calculable. Un ratio anormalmente bajo (mucho volumen, poco rango) en una
  tendencia bajista es candidato a *Selling Climax* o *absorción*; en una tendencia alcista, candidato
  a *Buying Climax*.
- **Detección de rango de trading**: ancho de un canal horizontal (máximo/mínimo rolling sobre N
  velas) relativo al ATR — un ancho decreciente sugiere "compresión" (construcción de causa).
- **Spring / Upthrust como patrón de precio**: ruptura de un nivel de soporte/resistencia previamente
  establecido, seguida de un cierre de vuelta *dentro* del rango en K velas — esto es una regla de
  precio explícita, programable sin ambigüedad (con parámetros a calibrar: cuántas velas definen el
  rango, cuántas velas de "vuelta" cuentan, qué tan lejos puede ir la ruptura).
- **Volumen decreciente en el test posterior al spring**: comparar el volumen del spring contra el
  volumen del test subsiguiente — computable directamente.
- **Sign of Strength / Weakness**: vela(s) de rango expandido + volumen sobre el promedio que rompe
  el rango — computable con umbrales relativos (igual que ya hacemos con RSI/EMA).

### Baja objetividad (requieren juicio, alto riesgo de reglas frágiles)

- **Etiquetar la fase exacta (A/B/C/D/E)**: distintos analistas Wyckoff etiquetan el mismo gráfico de
  forma distinta; una máquina de estados rígida va a fallar constantemente en mercados reales que no
  siguen el libro de texto al pie de la letra.
- **Distinguir un spring real de una ruptura real que simplemente continuó bajando**: esto SOLO se
  sabe con certeza en retrospectiva — es el mismo problema de fondo que ya vimos con el scoring
  actual (cualquier heurístico que "suene razonable" necesita validación histórica antes de que se
  confíe en él, no alcanza con que la lógica parezca sólida).
- **El "Operador Compuesto" como narrativa causal**: es un marco mental para interpretar, no algo que
  se mida directamente — el riesgo es construir una historia post-hoc que encaje con cualquier
  resultado.

---

## 3. Cómo encajaría en la arquitectura actual

Sin escribir código todavía, el diseño más natural, dado lo que ya existe:

- **Nuevo módulo `app/analysis/wyckoff_context.py`** (paralelo a `market_context.py`): dado
  `(exchange, pair)`, pide OHLCV en 2-3 temporalidades vía el `DataManager` ya existente, calcula:
  - `effort_result_ratio` por vela (la primitiva más objetiva, ver arriba)
  - rango de trading vigente (soporte/resistencia + ancho relativo al ATR)
  - flags de evento: `spring_detected`, `upthrust_detected`, `sos_detected`, `sow_detected` (reglas
    de precio/volumen explícitas, con parámetros configurables como `config.yml` ya hace con RSI)
  - un `structural_bias` de temporalidad alta: `accumulation` / `distribution` / `trending_up` /
    `trending_down` / `undefined` — **como una clasificación aproximada y explícitamente etiquetada
    como heurística no validada**, nunca como verdad de fondo.
- **Integración con `SignalEnhancer`**: en vez de agregar `wyckoff_bias` como un peso más en la misma
  fórmula ad-hoc ya cuestionada, tendría más sentido probarlo primero como **filtro independiente**
  (¿las señales que coinciden con `structural_bias` favorable performan distinto de las que no?) —
  exactamente la misma pregunta que `validate_signal_enhancer.py` ya sabe responder, aplicada a un
  factor nuevo en lugar de a los pesos existentes.
- **Ningún cambio a `notify_all` ni a ningún gate real** hasta que exista un reporte de validación
  histórica equivalente a los de slices 007/011, mostrando que el factor Wyckoff correlaciona con
  resultado de forma que sobreviva un test de significancia — la misma barra que ya establecimos.

---

## 4. Roadmap propuesto (para discutir, no para ejecutar todavía)

1. **Slice A — Effort vs. Result como feature objetiva**: implementar y testear (unit tests, sin
   backtest todavía) el cálculo del ratio esfuerzo/resultado por vela. Bajo riesgo, alta
   objetividad, reutilizable como insumo de los pasos siguientes.
2. **Slice B — Detección de rango + Spring/Upthrust**: reglas de precio explícitas y parametrizables,
   con tests unitarios sobre fixtures de OHLCV sintético que reproduzcan springs/upthrusts
   conocidos.
3. **Slice C — Validación histórica**: extender la metodología de `validate_signal_enhancer.py` /
   `validate_macd_cross.py` para medir si un evento Spring/UT detectado así predice algo real sobre
   datos históricos de Binance — **este paso decide si algo de esto vale la pena seguir
   construyendo**, antes de integrarlo a `SignalEnhancer` o a cualquier alerta real.
4. **Slice D (condicional a que C muestre señal real)**: composición multi-timeframe (sesgo de 1D
   como filtro de señales de 4h) y, recién ahí, integración con el pipeline de notificaciones.

## 5. Nota sobre el libro

Esta investigación se basa en el cuerpo de conocimiento público y ampliamente documentado del método
Wyckoff (los tres esquemas canónicos y las tres leyes son consistentes entre las fuentes estándar del
Wyckoff Stock Market Institute y la literatura derivada). Si el operador tiene un libro/PDF específico
en mente (por ejemplo, los escritos originales de Wyckoff, *Charting the Stock Market: The Wyckoff
Method*, o material de Wyckoff Analytics/David Weis), compartir el texto permitiría afinar esta
investigación con las definiciones y matices exactos de esa fuente en lugar del resumen general de
arriba.
