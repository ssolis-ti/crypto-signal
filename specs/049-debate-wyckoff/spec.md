# Spec 049: debate sobre Wyckoff (opencode, agy y Claude) y el test que discrimina "estructura" vs "rebote de beta"

Origen: el operador pidió un debate-brainstorm sobre Wyckoff (técnicas, libros, contenido, sucesores), con matemática y estadística, y con la perspectiva de la tradición
china (opencode/DeepSeek: 威科夫, 庄家 吸筹-洗盘-拉升-出货, 缠论, 筹码分布) frente a la formalización matemática y los sucesores occidentales (agy/Gemini: VSA, Weis Wave,
Market Profile, ICT/SMC). Ronda 1 y 2 en `brainstorm/`.

## Desacuerdo central de la ronda 1
- opencode: el edge del spring probablemente NO es Wyckoff sino "reversión de canasta tras una liquidación" (beta de las alts); la parte Wyckoff (rango, fases, causa) no agregó nada medible.
- agy: el método está mal medido: una campaña de días/semanas se reduce a un gatillo de una vela de 4h con retención fija de 72 h y stop -10%; barras de tiempo son arbitrarias.

## Test discriminante (criterio fijado ANTES de correr)
En cada vela de capitulación amplia (>= 20% de los pares elegibles con spring, universo de spec 044: 49 pares + 177 deslistados, >= 20M USD/24h), comparar el retorno a 72 h
(largo, stop -10%, 0.1% comisión) de:
- A: los pares CON spring confirmado en esa vela (lo que avisa el bot);
- B1: los pares elegibles SIN spring y con retorno de 24 h <= -5% (igual de golpeados, sin la estructura);
- B2: los pares SIN spring que rompieron su mínimo de 20 velas con volumen >= 2.5x en las 3 velas previas pero NO recuperaron el nivel (ruptura sin confirmación: "cuchillo").
Unidad: la vela (comparación pareada dentro de la misma vela), agrupada por día en el bootstrap. Hipótesis (dirección fijada): A > B1 y A > B2 (la estructura/confirmación agrega información
más allá de "estar golpeada"). Familia de k=2 (A-B1, A-B2), IC bootstrap por DÍA al 97.5%.
Aprueba (la estructura aporta) SOLO si, para cada comparación: diferencia media >= +0.5 pp en 2022-24 y en 2025-26 y el IC unido excluye 0. Si A ~ B1: el edge es beta de "alts golpeadas"
(opencode tiene razón) y la confirmación no agrega nada. Se reporta también en todas las velas (no solo capitulación amplia) como control.

## Resultado del test discriminante (resultado_estructura_vs_beta.txt)
56 velas de capitulación amplia (47 días): retorno a 72 h de A (springs) +1.91%, B1 (alts golpeadas 24 h <= -5% sin spring) **+0.78%**, B2 (ruptura con volumen sin recuperar el nivel) **+1.58%**.
- A - B1: +1.14 pp (2022-24 +1.35, 2025-26 +0.90), IC97.5% por día [-0.19, +2.44]. A - B2: +0.41 pp (+0.67 / +0.11), IC [-1.03, +1.74]. Ambos NO aprueban (IC incluye 0).
- Lectura: **en esos días hasta las alts golpeadas sin spring y las que rompieron sin recuperar rinden +0.8% a +1.6%** (la media incondicional del largo es -0.44%). La mayor parte de la ventaja
  es del DÍA (beta de la capitulación) y la estructura del spring aporta un extra de +0.4 a +1.1 pp no significativo. Con la media incondicional como base (-0.44%): el spring explica +2.35 pp,
  de los cuales "estar golpeada / romper el mínimo" ya da +1.2 a +2.0 pp, es decir, la estructura aporta ~14% a ~48%. Coincide con las apuestas de los agentes: agy 85% beta / 15% estructura,
  opencode ~80% / ~20%.

## Convergencia del debate (ronda 2)
- Ambos coinciden en que el edge es sobre todo rebote de beta de las alts tras liquidaciones forzadas (microestructura), no acumulación institucional multiescala. La parte "Wyckoff" (fases,
  Composite Man, causa-efecto) no agregó nada medible; el Composite Man es inobservable. agy conserva una crítica de diseño válida: una vela de 4h + retención fija de 72 h + stop -10% no es el método
  tal como se practica (validez de constructo), pero el onus de la prueba es de la estructura.
- Potencia: con 47 días independientes el MDE es ~1.6 pp (2.0 con corrección); por período 2.2 (27 días) y 2.5 pp (20 días). Todo filtro con efecto esperado < 1.6 pp nace muerto en el conjunto de
  capitulaciones amplias; solo tiene potencia lo medido sobre los ~3,400 springs.
- Descartados por ambos: HMM (40+ parámetros con 47 días), Weis Wave (zigzag discrecional), taker en 15 m, Chan 三买 (≈ LPS, ya falsado en spec 047),筹码分布 sin tick data (indistinguible del VWAP con este n).
- Tradición china (opencode): 洗盘 (lavado) ≠ spring exacto (el spring es 挖坑/诱空, trampa bajista); 庄家 es una metáfora que en cripto (MM + arbitraje + CEX/DEX) no describe a un actor único;
  缠论 es codificable pero con evidencia de foros; el respaldo empírico chino/asiático real es de comportamiento (efecto disposición, herding, límites de precio), no de Wyckoff.
  Momentum y reversión de corto plazo cripto (Liu, Tsyvinski, Wu, 2022) tienen respaldo académico; las reglas de Wyckoff no.

## Seguimiento pre-registrado: predictores de estructura sobre todos los springs (`predictores.py`; potencia alta: ~3,400 eventos)
Universo de spec 044 (49 pares + 177 deslistados, >= 20M USD/24h), simulador de spec 043. Variables medidas SIN mirar el futuro, terciles congelados con 2022-24:
- H1 esfuerzo-resultado: residuo estandarizado z_eps de la regresión de Huber ln(rango/cierre) ~ ln(volumen en USD) + ln(ATR14/cierre) sobre las 100 velas previas, evaluado en la vela de ruptura; dirección: tercil de z MÁS BAJO (absorción) rinde más que el más alto.
- H2 causa: KER30 (Kaufman) de las 30 velas previas a la ruptura; dirección: tercil de KER más bajo (rango, ruido) rinde más que el más alto (caída direccional).
- H3 fuerza relativa: retorno de las 12 velas previas a la confirmación menos el de BTC; dirección: tercil más ALTO (aguantó mejor) rinde más que el más bajo.
- H4 momentum: retorno de 30 días (180 velas) menos el de BTC; dirección: tercil más ALTO rinde más que el más bajo.
Familia de k=4, IC bootstrap por DÍA al 98.75%. Aprueba SOLO si: signo correcto en 2022-24 y en 2025-26; IC unido excluye 0; |dif| >= 0.5 pp; >= 30 días distintos por celda y período.
Si aprueba: no filtra el bot; se muestra/registra. Si no: la estructura de Wyckoff no aporta más allá del día de capitulación.

## Resultado del seguimiento (resultado_predictores.txt): ninguna aprueba (3,426 springs, potencia alta)
| Hipótesis (dirección fijada) | 2022-24 (mejor - peor) | 2025-26 | unido (IC98.75% por día) |
|---|---|---|---|
| H1 esfuerzo-resultado: z bajo (absorción) mejor | **-3.51 pp** | +1.18 pp | -2.29 [-6.04, +1.39] |
| H2 causa: KER30 bajo (rango previo) mejor | -0.09 pp | +0.83 pp | +0.01 [-3.57, +3.61] |
| H3 fuerza relativa 48 h: alta mejor | **-2.69 pp** | **-1.71 pp** | -2.36 [-5.77, +0.78] |
| H4 momentum 30 d: alto mejor | -0.25 pp | -1.77 pp | -0.62 [-3.61, +2.48] |

- **La estructura de Wyckoff no predice el resultado del spring.** El rango previo ordenado (KER) no aporta (+0.01 pp); el momentum de 30 días tampoco.
- **Dos señales van al revés de la doctrina, y H3 con el mismo signo en los dos períodos:** los springs de las alts que MÁS cayeron frente a BTC en las 48 h previas rinden más
  (2022-24 +3.34% vs +0.66%; 2025-26 +0.55% vs -1.16%). La regla clásica ("comprar la que aguanta") no se cumple; lo que se ve es reversión de las más golpeadas (rebote de beta),
  coherente con el resto del debate. Como la dirección pre-registrada era la contraria, es una observación exploratoria: el IC unido incluye 0 y no se actúa.
  Queda como hipótesis a validar hacia adelante (el bot registra el cambio de 24 h; falta registrar la fuerza relativa vs BTC).
- Correlación de rangos con el retorno a 72 h: z +0.10 (2022-24 +0.17, 2025-26 -0.08: invierte), KER +0.03, RS -0.06, momentum -0.02: todas ~0.

## Conclusión del debate
Tres líneas independientes (el test discriminante, el debate de los dos agentes y los predictores de estructura) coinciden: **la ventaja del spring es en su mayor parte rebote de beta de las alts
tras liquidaciones forzadas en días de capitulación amplia**; la estructura de Wyckoff (rango previo, esfuerzo-resultado, fuerza relativa, fases) aporta a lo sumo un extra pequeño no medible con la potencia
disponible. El método de lectura de Wyckoff sigue siendo válido como descripción, pero este proyecto no encuentra que agregue información predictiva en cripto 4h más allá de "capitulación amplia + rebote confirmado".
Ideas del corpus que quedan sin probar por potencia o costo: VAL-reclaim con perfil de volumen (potencia suficiente, costo medio), barras de volumen en vez de tiempo (crítica de agy), conteo de causa P&F.
