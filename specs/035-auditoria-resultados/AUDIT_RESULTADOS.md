# AUDITORÍA DE RESULTADOS — bot crypto-signal

**Rol:** auditor cuantitativo escéptico (resultados, no estrategia).
**Pregunta central:** ¿cada número que el bot le muestra al operador es verdadero, está bien calculado y es representativo de operar con 100 USDT?
**Fecha de la auditoría:** 2026-09-29 ~19:15 UTC. Todos los cálculos corren en el contenedor `crypto-signal:dev` (Freqtrade/Python/ccxt), solo lectura de `audit_data/`. No se modificó nada en `app/` ni en `tests/`.

## 0. Método y trazabilidad

Cada cifra de este informe se recalculó desde los trades crudos (`lab_trades/*.zip`) o se cita una línea de log. Los scripts están en `audit/`:

| Script | Qué calcula |
|---|---|
| `audit/inspect_zip.py` | estructura de un zip (campos de trade) |
| `audit/t12_metrics.py` | Tareas 1 y 2a/2c/2e: win-rate, media/mediana, retorno, DD, top-10 trades, top-5 días, concentración por par/año, clustering, MAE, stop vs tiempo |
| `audit/t1_extra.py` | Tarea 1: split Spring/Upthrust a 72h (n y medias por tag) |
| `audit/t2d_signal_vs_real.py` | Tarea 2d: subconjunto de trades que el modo real sí toma |
| `audit/t3_biases.py` | Tarea 3a/3b/3c: supervivencia, latencia de aviso, funding/comisiones |
| `audit/t4_alerts.py` | Tarea 4: registro real, descarte de inválidos/duplicados, precios ccxt |
| `audit/t5_bootstrap.py` | Tarea 5c y 2f: bootstrap de 5.000 caminos, mínimos de orden Binance |

Salidas numéricas: `audit/out_t12.json`, `out_t3.json`, `out_t4.json`, `out_t5.json`.

**Límite de datos duro:** el registro de alertas reales es de hoy (2026-09-29) y la hora actual es 19:14 UTC. La vela de 12:00 UTC cerró a las 16:00 UTC. Existe como máximo **7 h de precio posterior** al evento más viejo y **3 h** al más nuevo. Por lo tanto **los retornos a 24h y 72h en vivo son NO VERIFICABLES** con este paquete (el futuro no existe todavía en los datos); más abajo se marca explícitamente.

---

## 1. Conciliación de afirmaciones

Fuente del texto: `app/analysis/wyckoff_alerts.py:44-57` (`SPRING_PLAN`, `UPTHRUST_PLAN`). Todo lo "recalculado por mí" sale de `audit/t12_metrics.py` y `audit/t1_extra.py` sobre los zips de `audit_data/lab_trades/` (comisiones y funding incluidos por Freqtrade).

Periodos: **IS = 2022-01-01 → 2025-01-01**; **OOS = 2025-01-01 → 2026-09-22** (`audit_data/lab_trades/INDEX.md`).
Modo **señal** = stake 100, sin límite real de posiciones (config `config_wyckoff_lab.json`, `max_open_trades:100`). Modo **real** = 100 USDT, 3 posiciones de 30 (config `config_wyckoff_real.json`).

| # | Afirmación del mensaje | Fuente (zip/log) | Valor recalculado por mí (n) | Veredicto | Corrección sugerida |
|---|---|---|---|---|---|
| 1 | "Acierto 56-58%" | `WyckoffLab_SpringH72` (sin stop, modo señal) IS/OOS | **56.23% (n=827) / 57.96% (n=509)** | IMPRECISO | Es el acierto de modo **señal sin stop**. Con el stop −10% que el propio mensaje recomienda: 55.05% (n=861) / 56.95% (n=525). En el setup de "3 posiciones de 30" cae a **49.6% (n=353) / 56.2% (n=210)**. Decir "49-58% según formato". |
| 2 | "ganancia media +1.5% a +1.8% por trade (1x, con comisiones)" | `WyckoffLab_SpringH72` (sin stop) IS/OOS | **+1.518% (n=827) / +1.756% (n=509)** | IMPRECISO | Es modo señal sin tope. Con stop −10% señal: +1.688/+1.685. En **modo real**: **+0.95% (n=353) / +1.04% (n=210)**. Decir "~+1%/trade en el setup de 3 posiciones". |
| 3 | "Stop sugerido: -10% en precio" | `wyckoff_lab.py:156-162`; salidas `stop_loss` | Trades con stop salen a **−10.06% (n=139) / −10.05% (n=63)** a 1x; a 3x la misma orden = −30% de margen | VERIFICADO | Aclarar que el stop se ejecuta a **mark price y a mercado**: puede deslizar (peor que −10%). A 1x usarlo como corte; a 3x es −30% del margen. |
| 4 | "+92% en 2022-24, +63% en 2025-26 con 100 USDT (3 posiciones de 30) a 1x" | `WyckoffLab_SpringH72_SL10` real IS/OOS | **+91.85% (n=353) / +62.95% (n=210)** sobre balance 100 (final 191.85 / 162.95) | VERIFICADO (con salvedades) | Es **suma de PnL con stake fijo de 30, sin interés compuesto y sin reinvertir**; no es un CAGR. Ver punto 2d: el modo real **descarta 513/317 señales** que en modo señal promediaban +2.14%/+2.08%. |
| 5 | "caída máxima 19-27% (a 3x: hasta 46%)" | real 1x y 3x IS/OOS | 1x: **26.72% (IS) / 18.85% (OOS)**. 3x: **46.21% (IS) / 32.16% (OOS)** | VERIFICADO | Está bien, pero es el **máximo de un único camino**. El bootstrap (5.000 caminos, `out_t5.json`) da DD p95 = 46% (IS 1x) y **hasta 284%** en el peor camino a 3x → ruina. Decir "el peor DD histórico fue X; en un camino malo puede ser mayor". |
| 6 | "Operar de 1-2h NO funciona: 44-49% de acierto y pierde con comisiones" | `WyckoffLab_H1/H2` IS/OOS | H1: **44.23% (n=2200) / 46.51% (n=1161)**, media −0.10%/−0.06%. H2: **45.64% (n=2200) / 49.01% (n=1161)**, media −0.05%/+0.10% | VERIFICADO | Correcto como rango agregado. |
| 7 | Upthrust: "Acierta la caída 57-61%" | `WyckoffLab_H72` por `enter_tag=upthrust` | **56.8% (n=972) / 60.6% (n=472)** | VERIFICADO (borde) | 56.8 redondea a 57; el límite inferior real es 56.8, no 57. |
| 8 | Upthrust: "en 2022-24 los rebotes se comieron la ganancia" | upthrust IS | media **−0.186%** (n=972) con mediana **+1.163%** | VERIFICADO (dirección) | La media es negativa por colas de squeeze; la mediana es positiva. "Pierde en promedio por colas", no "pierde casi siempre". |
| 9 | Upthrust: "en 2025-26 fue positivo (+0.6% por trade a 72h)" | upthrust OOS | media **+0.628%** (n=472) | VERIFICADO | Correcto, pero el mismo mensaje ya dice que no es edge confiable. |
| 10 | "No es asesoría financiera / Backtest Freqtrade 2022-2026" | spec 032 | Backtest IS+OOS con comisiones y funding; `lookahead_SpringH72.log`: **"no bias detected", 40 señales, 0 sesgadas** | VERIFICADO | Correcto. |

### 1.1 El problema de fondo (mezcla de modos)

El mensaje junta, en el mismo párrafo, cifras de **tres objetos distintos**:

1. **Acierto 56-58%** y **+1.5/+1.8%/trade** → modo **señal, sin stop, sin tope de posiciones** (`WyckoffLab_SpringH72`, n=827/509).
2. **Stop −10%** → modo señal con stop (`..._SL10`, n=861/525) o real.
3. **+92%/+63% y DD 19-27%** → modo **real en 100 USDT con 3 posiciones de 30** (`..._SL10` real, n=353/210), que es otra muestra.

Ninguna de las tres describe lo mismo, y el operador leerá las tres como si fueran una sola. Además, el **p-valor de la media por trade colapsa** al pasar al formato real (cifras de los propios logs):

| Experimento | p-valor media/trade (log) | n |
|---|---|---|
| Señal sin stop IS | 6.318e-06 | 827 |
| Señal sin stop OOS | 1.726e-06 | 509 |
| Señal con stop IS | 7.381e-08 | 861 |
| Señal con stop OOS | 4.033e-06 | 525 |
| **Real 1x IS** | **0.09554** | 353 |
| **Real 1x OOS** | **0.04622** | 210 |
| Real 3x IS / OOS | 0.09343 / 0.04294 | 354 / 210 |

Fuente: `audit_data/lab_logs/WyckoffLab_SpringH72*_*_*.log` (campo "Mean profit p-value"). En el formato que el operador va a usar, **IS no es significativo al 5%** y OOS queda al borde. El "56-58%" del mensaje esconde esto.

---

## 2. Calidad del backtest del edge

Base: springs 72h. Modo señal `WyckoffLab_SpringH72` (n=827 IS / 509 OOS) y `..._SL10` (861/525); modo real `..._SL10` (353/210).

### (a) Distribución de ganancias

| Dataset (n) | media | mediana | ganadores | top-10 trades (% del neto) | top-5 días (% del neto) |
|---|---|---|---|---|---|
| señal IS (827) | +1.52% | +1.10% | 56.2% | +31.9% | **+88.6%** |
| señal OOS (509) | +1.76% | +1.19% | 58.0% | +33.4% | **+107.9%** |
| real IS (353) | +0.95% | **−0.01%** | 49.6% | **+119.6%** | **+101.4%** |
| real OOS (210) | +1.04% | +0.54% | 56.2% | **+96.2%** | **+90.6%** |

Lectura: la media es apenas mayor que la mediana (sesgo positivo por pocos trades grandes), y **el resultado está extremadamente concentrado**: en modo real los 10 mejores trades explican ~el 100% de la ganancia neta y los 5 mejores días ~90-100%. Es decir, **la mayor parte del "+92%/+63%" viene de unos poquísimos días**; el resto de los días apenas compensa las pérdidas. (Recalculado en `audit/t12_metrics.py`; los top-5 días usan `daily_profit` del zip.)

### (b) Concentración por par y por año

- **Mejores pares real IS**: XRP +25.8, MANA +23.1, GALA +20.5, SOL +18.0, UNI +16.3 USDT. Peores: FIL −16.8, ADA −12.1, TRX −6.4.
- **Por año (recalculado, real 1x)**: 2022 **+33.3**, 2023 **+20.7**, 2024 **+39.6**, 2025 **−1.8**, 2026 **+24.8** USDT (OOS dividido en 2025 +38.1 / 2026 +24.8).
- Ningún par domina el neto en modo real (el mayor es XRP con +25.8, ~28% del neto IS y DOGE ~16% del neto OOS), pero **el resultado por año sí depende de 2024** (39.6 de 91.85 en IS = 43% del total del IS).

### (c) Clustering (eventos simultáneos en varios pares)

| Dataset | eventos | timestamps distintos | timestamps con ≥2 pares | eventos en cluster | máx. pares misma vela | media en cluster vs solo |
|---|---|---|---|---|---|---|
| señal IS (827) | 827 | 288 | 131 | **670 (81.0%)** | **20** | **+1.93% vs −0.22%** (win 58.2% vs 47.8%) |
| señal OOS (509) | 509 | 177 | 67 | **399 (78.4%)** | **23** | **+2.00% vs +0.88%** (win 59.9% vs 50.9%) |

Consecuencia estadística dura: **los 827 trades no son 827 observaciones independientes**; el 81% cae en 131 velas compartidas por varios pares (hasta 20-23 pares en la misma vela de 4h). Son esencialmente **pocos episodios de mercado** repetidos en 20 monedas. El n efectivo es mucho menor que el n reportado, así que los p-valores de modo señal están sobreestimados. Los eventos en cluster promediaron *mejor* que los aislados, lo que sugiere que gran parte del edge es **beta de mercado en rebotes amplios**, no una señal idiosincrática por par.

### (d) Modo señal vs modo real — por qué rinden distinto

`audit/t2d_signal_vs_real.py` empareja trades por `(par, timestamp de apertura)`:

| | señal n / media / acierto | real n / media / acierto | trades reales dentro de señal | **señales que señal SÍ tomó y real NO** |
|---|---|---|---|---|
| IS | 861 / +1.69% / 55.1% | 353 / +0.95% / 49.6% | 348 / +1.02% / 49.7% | **513 / +2.14% / 58.7%** |
| OOS | 525 / +1.69% / 57.0% | 210 / +1.04% / 56.2% | 208 / +1.09% / 56.2% | **317 / +2.08% / 57.4%** |

Esto es lo más importante de toda la auditoría: en modo real **solo 348/861 (40%) de las señales caben** (3 posiciones x 72h) y **las 513 descartadas eran las mejores** (+2.14% medio, 58.7% acierto, contra +1.02% de las que sí entran). Con 3 posiciones, cuando el mercado dispara 20 springs a la vez, solo entran las 3 primeras por orden de par, y sistemáticamente quedan afuera las mejores. El "+92%" del laboratorio es el resultado del **subset peor**; el "+2.14%" que se pierde es un costo de oportunidad no mencionado en el mensaje. (Freqtrade registra `rejected_signals` 2181 en IS y 1412 en OOS, aunque ese contador infla: cuenta cada vela en que una señal estuvo bloqueada.)

El resultado en modo real depende fuertemente de **cuándo arranca la simulación** (qué par ocupa cada slot). Es frágil: cambiar el orden de evaluación de pares cambia qué 3 entran.

### (e) Profundidad de la caída (MAE) y stop vs tiempo

| Dataset (n) | cerró por stop | cerró por tiempo | MAE ≤ −10% | MAE mediana | peor MAE |
|---|---|---|---|---|---|
| señal SL10 IS (861) | **139 (16.1%)** | 717 (83.3%) | 136 (15.8%) | −3.65% | −22.22% |
| señal SL10 OOS (525) | **63 (12.0%)** | 462 (88.0%) | 67 (12.8%) | −3.87% | −14.81% |
| señal sin stop IS (827) | 0 | 822 (99.4%) | 132 (16.0%) | −3.59% | **−66.31%** |

Responde directo a "¿el stop −10% se toca seguido?": **sí, en 12-16% de los trades**, y son exactamente la mayoría de las pérdidas relevantes. Antes de resolverse, la mediana del trade pasa por **−3.6% de caída**; un cuarto de los trades pasa por ≤ −7.3%. La gran mayoría de los trades **sufre una caída intermedia de varios por ciento** antes de ganar. Sin stop (modo señal), un trade llegó a **−66%** de excursion adversa: con 3x habría liquidado.

### (f) Tamaño de posición vs orden mínima de Binance (`audit/t5_bootstrap.py`, ccxt `load_markets`)

Con **30 USDT y 1x (notional 30 USDT)**: de los 29 pares vivos, **BTC/USDT:USDT no es ejecutable** (mín. notional **50 USDT** y mín. 0.001 BTC ≈ 83 USDT; la orden de 30 USDT no llega). Con 3x (notional 90 USDT) BTC sí entra. ETH/LINK/LTC/ETC/BCH tienen mínimo 20 USDT (30 alcanza); el resto, 5 USDT. **EOS ya no cotiza** (el log lo removió: "EOS/USDT:USDT is not compatible… removing from whitelist", `WyckoffLab_SpringH72_SL10_IS_real.log:82`).

Nota práctica: en modo real a 1x, 3 posiciones de 30 = **90 USDT comprometidos de una wallet de 100** (90% de utilización); el buffer es 10 USDT. Si el bot emite una señal de BTC a 1x, el operador no puede ejecutarla con 30 USDT.

---

## 3. Sesgos

### (a) Supervivencia / historia incompleta

- La whitelist del laboratorio es de **30 pares que existen HOY** (`audit_data/strategies/config_wyckoff_lab.json:6-14`). EOS fue removido por incompatibilidad (log:82), quedando **29 pares efectivos**.
- Sin historia completa en 2022 **2 de 29**: **ICP** (datos desde 2022-09-27) y **APE** (desde 2022-03-17), según las advertencias de los logs (`WyckoffLab_SpringH72_SL10_IS_real.log:84-85`).
- **NO VERIFICABLE**: no hay datos de pares que cotizaban en 2022 y luego se delistaron o cayeron a cero (p. ej. el universo point-in-time de 2022 no está en el paquete). Por lo tanto **no se puede medir** el sesgo de supervivencia; solo se puede afirmar que la lista es retrospectiva (elige monedas que sobrevivieron hasta 2026). El backtest tampoco incluye eventos en pares muertos.

### (b) Retraso de ejecución

`audit/t3_biases.py` sobre `audit_data/bot_alertas_registro.jsonl`:

- **4 registros con latencia −4.5 min** (avisados a las 15:55 sobre la vela de 12:00, que cierra 16:00): son la vela **sin cerrar** (bug ya documentado en `DATOS_LEEME.md:11`). El bot avisó antes de que la vela cerrara → el evento podía repintar. El operador **ya recibió** esos avisos.
- Avisos **válidos y frescos**: **6.4 a 7.1 min** después del cierre (16:06-16:07). El laboratorio asume entrada a la **apertura de la vela siguiente** al cierre, o sea 0 min de retraso.
- Avisos **radar de la vela 08:00**: 240 min (4 h) tarde respecto de su cierre (12:00), porque el bot estaba apagado/reiniciado. El radar no tiene aviso de "alerta retardada" (solo el Wyckoff lo tiene, `wyckoff_alerts.py:250-257`).
- **Costo medido** (ccxt 15m, `out_t4.json`): para avisos frescos el deslizamiento apertura→momento del aviso fue **+0.03% (ETH), +0.05% (XRP), −0.09% (AVAX), −0.47% (AAVE)**; para el radar atrasado de AVAX fue **−5.44%**. Con n=6 no se concluye una cifra general, pero el caso atrasado muestra que el retraso **no es despreciable** cuando el bot estuvo caído.

### (c) Funding y comisiones

Están incluidos, verificado por dos vías:

- Los logs cargan `funding_rate` de la exchange (`WyckoffLab_SpringH72_IS_signal.log:88`) y fijan comisión **0.05% por lado** (`..._SL10_IS_real.log:83`: "Using fee 0.0500% - worst case fee").
- En los trades, `fee_open = fee_close = 0.0005` en el 100% de los casos, y `funding_fees ≠ 0` en **858/861** (señal IS), **525/525** (señal OOS), **348/353** (real IS), **210/210** (real OOS); en total el funding pesa entre **−0.37% y +0.45% del bruto** (`out_t3.json`). Es pequeño pero está.

Salvedad: el backtest asume **comisión de 0.05% (tier más bajo)**, que es el caso conservador de Binance; a 1x el impacto es ~0.1% por trade (ida+vuelta) sobre ~+1%: **una décima parte de la ganancia media**. Si el operador paga más fees, come margen.

### (d) Comparaciones múltiples

El README documenta **33 slices** (`README.md:148-182`), de los cuales ~18 buscan edge de estrategia (007, 011, 015, 017-019, 021-022, 024-033). El conteo de configuraciones evaluadas es de **cientos**: 60+ patrones de vela (slice 029), 150+ funciones TA-Lib propuestas (slice 026), 4 timeframes extra (025), 6 horizontes x 2 direcciones = 12 en la ronda 1 de 032, más filtros 019/027. Con ~200 pruebas y α=0.05, la aritmética espera **~10 falsos positivos** por azar; que el spring 72h haya quedado como único superviviente es tanto un mérito (pasó holdout OOS) como el resultado esperable de una búsqueda amplia.

**Advertencia de holdout:** el horizonte (72h) y el stop (−10%) se eligieron mirando la tabla que contiene **IS y OOS a la vez** (spec 032, tabla "Ronda 2"). El OOS 2025-26 **no es un holdout limpio** para esa elección: sirvió para elegir. Sí es evidencia independiente de que el mecanismo sigue positivo, pero no de que la magnitud (+92%/+63%) esté libre de selección.

---

## 4. Alertas reales del bot (`audit_data/bot_alertas_registro.jsonl`)

`audit/t4_alerts.py`. **18 registros** totales.

**Inválidos / descartados (12):**
- **4 "vela sin cerrar"** (avisados 15:55 sobre la vela 12:00 que cierra 16:00): ETH, XRP, AAVE (radar) y **AVAX (Wyckoff cold)**.
- **8 "duplicados por reinicio"** del mismo `(par, tipo, dirección, vela)`: AVAX wyckoff cold 12:00 y los radar ETH/XRP/AAVE 12:00 repetidos a las 16:10 y 17:45. Confirman el bug de dedup descrito en `DATOS_LEEME.md:11`.

**Válidos únicos (6):** 1 Wyckoff (**AVAX cold/upthrust**, vela 12:00, rel_vol 2.83, avisado 16:06:46) + 5 radar (AVAX y AAVE vela 08:00; ETH, XRP, AAVE vela 12:00).

**Retornos a 24h/72h: NO VERIFICABLE** — la hora actual (19:14 UTC) solo deja 3-7 h de precio posterior. Lo que sí se pudo medir:

| Evento | entrada (apertura vela sig.) | máx. adverso / favorable en lo disponible | stop −10% |
|---|---|---|---|
| AVAX wyckoff cold (short), 16:00 | 11.207 | 1.79% a favor / 1.18% en contra | no |
| radar AVAX 16:00 | 11.841 | −7.05% / +1.40% | no |
| radar AAVE 16:00 | 171.27 | −4.02% / +2.90% | no |
| radar ETH 16:00 | 2672.83 | −0.26% / +0.97% | no |
| radar XRP 16:00 | 1.5174 | −2.77% / +0.40% | no |

**Chequeo de cordura (NO rendimiento):** el único evento Wyckoff vivo es un **upthrust short**, justo la dirección que el laboratorio marca "sin edge confiable"; a 3 h iba +0.63%. Con **n=1** no se concluye nada, y así debe leerse. El comportamiento es compatible con la dispersión esperada (MAE medianas de −3 a −4% en el laboratorio).

**Radar:** el mensaje pide comparar el movimiento posterior contra una vela de volumen normal. Solo 2 de 5 eventos dieron comparación válida: AVAX se movió 4.75% (vs 3.41% de una vela normal) y AAVE 3.43% (vs 11.08%). **n=2 → NO CONCLUSIVO**; no hay evidencia de que el radar anticipe movimientos mayores. El radar sigue correctamente etiquetado como "NO validado" en el mensaje.

---

## 5. Veredicto final

### (a) Las 5 afirmaciones con más riesgo de engañar (ordenadas)

1. **"Acierto 56-58%" junto a "Plan… stop −10%" y "+92%/+63% con 100 USDT".** Mezcla modo señal (sin tope, sin stop) con modo real (3 posiciones, con stop). En el formato que usará el operador el acierto es **49-58%** y la media **~+1%**, no 56-58% / +1.5-1.8%. Es el engaño más costoso porque fija expectativas.
2. **"+92% / +63% con 100 USDT".** Verificado, pero se presenta como si fuera una tasa de la estrategia y omite que (i) es suma con stake fijo de 30, sin interés compuesto; (ii) ese modo **descarta las 513 señales que promediaban +2.14%**; (iii) depende del arranque y del orden de pares. Induce a creer que cualquier spring renta igual.
3. **"caída máxima 19-27% (a 3x hasta 46%)".** Es el peor DD de **un solo camino histórico**. El bootstrap da DD p95 de 46% (IS 1x) y caminos de 3x con **drawdown de 100-284%** (ruina). Decir "19-27%" como expectativa normal subestima la cola mala.
4. **La aparente robustez estadística (no expresada pero implícita).** En modo real, IS **p=0.0955** (no significativo) y OOS **p=0.046** (al borde); además el "n=827" es en realidad ~131 episodios de mercado (81% de eventos en clusters de hasta 20-23 pares). La significancia de modo señal está inflada por falta de independencia.
5. **Upthrust "Acierta la caída 57-61%" / "+0.6% por trade".** Cierto como número, pero invita a operar short un mecanismo que en 2022-24 dio media **−0.19%** y que el propio spec llama "sin edge confiable". Un acierto alto con media negativa es una trampa clásica de colas.

### (b) Mensaje reescrito (solo cifras verificadas, español, mismo tono)

**Spring:**
> 📈 **Plan validado: long, mantener ~72h, stop −10% en precio (mark).**
> Backtest 30 pares, comisiones y funding, 1x: **56-58% de acierto y +1.5-1.8% medio por trade** sin tope de posiciones.
> Con **100 USDT en 3 posiciones de 30**: **+92% (2022-24) y +63% (2025-26)**; caída máxima **27% y 19%** (a 3x: **46% y 32%**).
> En ese formato real el acierto baja a **49.6-56.2%** y la media a **~+1%/trade**; la significancia es débil (p=0.10 en 2022-24).
> ⚠️ **1-2h NO funciona: 44-49% y pierde con comisiones.**

**Upthrust:**
> ⚠️ **Short con edge débil.** Acierta la caída **56.8% (2022-24) / 60.6% (2025-26)** a 72h, pero en 2022-24 la media por trade fue **−0.19%** (squeezes) y en 2025-26 **+0.6%**.
> Si lo operás: tamaño chico y stop ajustado. **No es el edge validado.**

(7 líneas en total, ≤12.)

### (c) Lo que el operador debe saber antes de arriesgar plata (calculado de los trades)

- **Racha perdedora normal:** en modo real la peor racha fue **10 trades seguidos perdiendo (IS)** y **6 (OOS)**. El bootstrap da p95 = **11 pérdidas seguidas** y máximos de 16-22. Con ~1 trade cada 3 días, una racha de 10 puede durar **~1 mes**.
- **Proporción de perdedores:** **50.4% (IS) / 43.8% (OOS)**: casi la mitad de los trades cierran en rojo.
- **Drawdown esperable (100 USDT):** observado **−26.7% (IS) / −18.9% (OOS)**; el bootstrap p95 es **−46% (IS) / −27% (OOS)**, con caminos peores. Con 100 USDT eso es bajar a ~53-73 USDT en una mala racha, y la racha puede durar **meses** (el DD del IS duró 188 días).
- **A 3x:** el stop de precio −10% = **−30% de margen por trade**; 3 trades simultáneos malos ≈ **−27% del capital**. El bootstrap de 3x tiene caminos con **drawdown >100% (ruina)**. Con 100 USDT, **3x no es prudente** (el propio spec 032 lo admite, `spec.md:62`).
- **Aprovechamiento real:** 3 posiciones x 30 = **90 de 100 USDT (90%)**; el buffer de 10 USDT se lo comen funding y slippage. Y el bot puede mandar una señal de **BTC a 1x que no es ejecutable con 30 USDT** (mínimo 50 USDT).
- **Costo de selección:** si el operador imita "3 posiciones", debe asumir que en clusters grandes (hasta 20-23 pares a la vez) **verá solo 1-3 señales de las mejores**; la mediana del trade pasa por **−3.6%** antes de ganar y **13-20% de los trades cierran por stop** (70/353 IS, 28/210 OOS).
- **Concentración:** ~**90-100% del beneficio neto viene de solo 5 días**; no esperar ganancias repartidas ni mes a mes.

### (d) Nivel de confianza global: **MEDIO**

Razón: el **mecanismo** (spring 4h con volumen de ruptura ≥2.5x) tiene respaldo real y no trivial: IS y OOS positivos, sin lookahead (`lookahead_SpringH72.log`: 40 señales, 0 sesgadas), comisiones y funding incluidos, n grande (827/509) y p-valor de modo señal pequeño. Pero **como expectativa operativa con 100 USDT la confianza baja** por cuatro razones verificadas: (1) significancia débil en el modo real (p=0.0955 IS / 0.046 OOS); (2) resultado concentrado en ~5 días y en clusters de beta de mercado (n efectivo ~131, no 827); (3) el tope de 3 posiciones descarta sistemáticamente las mejores señales (+2.14% medio); (4) el OOS no es un holdout limpio del horizonte/stop elegidos. Es un edge plausible y modesto, **no** un "+92% reproducible".

---

### Resumen de NO VERIFICABLE

- Retornos a **24h/72h** de las alertas reales: el futuro no existe en los datos (máx. 7 h transcurridas).
- **Sesgo de supervivencia** (pares delistados 2022-2026): no hay universo point-in-time en el paquete.
- **Deslizamiento histórico de órdenes** (más allá de los 6 eventos de hoy): no hay registro de ejecuciones reales.
- **Rendimiento del radar**: n=2 comparaciones válidas, sin horizonte completo.
