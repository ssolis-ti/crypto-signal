[0m
> plan · deepseek-flash
[0m→ [0mRead README.md 
[0m→ [0mRead audit_data/DATOS_LEEME.md 
[0m→ [0mRead specs/035-auditoria-resultados/VERIFICACION_FILTROS.md 
> plan · deepseek-flash
[0m→ [0mRead audit_data 
[0m→ [0mRead specs/035-auditoria-resultados 
[0m→ [0mRead audit_data/lab_trades/INDEX.md 
> plan · deepseek-flash
[0m→ [0mRead specs/035-auditoria-resultados/AUDIT_MEJORAS.md 
[0m→ [0mRead specs/035-auditoria-resultados/AUDIT_RESULTADOS.md 
> plan · deepseek-flash
[0m→ [0mRead audit_data/strategies/wyckoff_lab.py 
[0m$ [0mls "C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\audit_data\strategies" "C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\audit_data\lab_logs" "C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\specs\035-auditoria-resultados\scripts" "C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\specs\035-auditoria-resultados\scripts_estrategia"
C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\audit_data\lab_logs:
LR10_H24_IS_signal.log
LR10_H24_OOS_signal.log
LR15_H24_IS_signal.log
LR15_H24_OOS_signal.log
LR15_H24_SL10_IS_real.log
LR15_H24_SL10_IS_signal.log
LR15_H24_SL10_OOS_real.log
LR15_H24_SL10_OOS_signal.log
LR15_H72_IS_signal.log
LR15_H72_OOS_signal.log
LR15_H72_SL10_IS_real.log
LR15_H72_SL10_IS_signal.log
LR15_H72_SL10_OOS_real.log
LR15_H72_SL10_OOS_signal.log
MR10_H24_IS.log
MR10_H24_OOS.log
MR10_H72_IS.log
MR10_H72_OOS.log
MR15_H24_IS.log
MR15_H24_OOS.log
MR15_H72_IS.log
MR15_H72_OOS.log
MR20_H24_IS.log
MR20_H24_OOS.log
MR20_H72_IS.log
MR20_H72_OOS.log
WyckoffLab_H14D_IS.log
WyckoffLab_H14D_OOS.log
WyckoffLab_H1_IS.log
WyckoffLab_H1_OOS.log
WyckoffLab_H24_IS.log
WyckoffLab_H24_OOS.log
WyckoffLab_H2_IS.log
WyckoffLab_H2_OOS.log
WyckoffLab_H72_IS.log
WyckoffLab_H72_OOS.log
WyckoffLab_H7D_3X_SL10_IS.log
WyckoffLab_H7D_3X_SL10_OOS.log
WyckoffLab_H7D_IS.log
WyckoffLab_H7D_OOS.log
WyckoffLab_H7D_SL10_IS.log
WyckoffLab_H7D_SL10_OOS.log
WyckoffLab_SpringH72_3X_SL10_IS_real.log
WyckoffLab_SpringH72_3X_SL10_OOS_real.log
WyckoffLab_SpringH72_IS_signal.log
WyckoffLab_SpringH72_OOS_signal.log
WyckoffLab_SpringH72_SL10_IS_real.log
WyckoffLab_SpringH72_SL10_IS_signal.log
WyckoffLab_SpringH72_SL10_OOS_real.log
WyckoffLab_SpringH72_SL10_OOS_signal.log
lookahead_SpringH72.log

C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\audit_data\strategies:
config_wyckoff_lab.json
config_wyckoff_real.json
meanrev_lab.py
wyckoff_lab.py

C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\specs\035-auditoria-resultados\scripts:
inspect_zip.py
t12_metrics.py
t1_extra.py
t2d_signal_vs_real.py
t3_biases.py
t4_alerts.py
t5_bootstrap.py
verify_filters.py

C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\specs\035-auditoria-resultados\scripts_estrategia:
01_diagnostico_metodologico.py
02_concentracion_ventaja.py
03_gestion_salida.py
04_capital_chico.py
05_senales_nuevas.py
download_data.py
experimentos_lab.py
> plan · deepseek-flash
[0m→ [0mRead audit_data/bot_alertas_registro.jsonl 
[0m✱ [0mGlob "app/analysis/wyckoff_alerts.py" [90m1 match[0m
> plan · deepseek-flash
[0m→ [0mRead app/analysis/wyckoff_alerts.py 
> plan · deepseek-flash
[0m→ [0mRead specs/035-auditoria-resultados/scripts/t3_biases.py 
[0m→ [0mRead specs/035-auditoria-resultados/scripts/t12_metrics.py 
> plan · deepseek-flash
No pude crear `BRAINSTORM_OPENCODE.md`: estoy en **Plan mode**, que me prohíbe modificar cualquier archivo del repo (la única ruta donde podría escribir es `C:\Users\Proyecto Z\.opencode\plan`). Te dejo el **contenido completo y listo para pegar** abajo. Si cambio de agente (o me lo pedís fuera de Plan mode), lo escribo tal cual en la raíz del clon sin tocar nada más.

---

# BRAINSTORM_OPENCODE.md

## Alcance, fuentes y reglas de lectura

- **Qué es esto**: ideas de investigación (no código, no promesas de rendimiento). crypto-signal es un bot **solo de alertas por Telegram**; el operador opera **a mano** en futuros de Binance. **No asumo su capital ni el tamaño de sus posiciones.** Freqtrade es **otro proyecto** (laboratorio de backtests), no lo operativo.
- **Fuentes leídas**: `audit_data/DATOS_LEEME.md`, `audit_data/lab_trades/INDEX.md`, `README.md`, `specs/035-auditoria-resultados/VERIFICACION_FILTROS.md`, `AUDIT_RESULTADOS.md`, `AUDIT_MEJORAS.md`, `app/analysis/wyckoff_alerts.py`, `audit_data/strategies/wyckoff_lab.py`, `audit_data/bot_alertas_registro.jsonl`, scripts `scripts/t3_biases.py` y `scripts/t12_metrics.py`.
- **Hechos base que cito** (con archivo):
  - Aviso fresco: **6.4–7.1 min** después del cierre (`AUDIT_RESULTADOS.md` §3b).
  - Deslizamiento apertura→aviso (n=6, ccxt 15m): ETH **+0.03%**, XRP **+0.05%**, AVAX **−0.09%**, AAVE **−0.47%**; radar atrasado AVAX **−5.44%** (`AUDIT_RESULTADOS.md` §3b).
  - Caída intermedia: MAE mediana **−3.65% (IS, n=861) / −3.87% (OOS, n=525)**; ≤−10%: **15.8%/12.8%**; cierre por stop **16.1%/12.0%**; por tiempo **83.3%/88.0%** (`AUDIT_RESULTADOS.md` §2e). "Un cuarto de los trades pasa por ≤−7.3%" (§5c).
  - Clustering: **81.0% (IS) / 78.4% (OOS)** de los eventos caen en velas con ≥2 pares; máx **20/23 pares** en una vela; media en clúster **+1.93% vs −0.22%** aislado (IS) y **+2.00% vs +0.88%** (OOS) (`AUDIT_RESULTADOS.md` §2c; `VERIFICACION_FILTROS.md` da aislados −0.22/+0.88 y 5+ pares +2.71/+2.29).
  - Modo real: p=**0.0955 (IS)** / **0.046 (OOS)** (`AUDIT_RESULTADOS.md` §1.1).
  - 1–2h: H1 **44.23%/46.51%** (media −0.10/−0.06); H2 **45.64/49.01** (−0.05/+0.10) (`AUDIT_RESULTADOS.md` §1).
  - Filtros auditados **NO** confirmados por bootstrap por día: barrida ≥1%/1.5%, caída 24h ≤−8%, BTC>EMA200 (`VERIFICACION_FILTROS.md`, todos los IC95% incluyen 0). **No confirmados tampoco** (no pasaron por ese bootstrap): funding negativo, ATR alta, fin de semana, volumen >5x (`AUDIT_MEJORAS.md`, marcados allí como "candidatos").
  - El mensaje ya muestra y registra `sweep_depth_pct`, `concurrent_pairs`, `change_24h_pct` (`app/analysis/wyckoff_alerts.py:346-417`) y marca **"ALERTA RETARDADA"** si pasaron >2h (`:336-343`).
- **Estándar pre-registrado del proyecto (lo aplico a cada idea)**: confirmada solo si **mejora en 2022-24 Y en 2025-26**, con **n≥30 por celda** y el **IC95% de un bootstrap POR DÍA/VELA** (no por trade: los eventos no son independientes). Si mejora solo OOS → **ruido** (lección de specs 027/029/035).
- **Nota de datos**: el registro vivo tiene 18 registros, 6 válidos, y **retornos a 24/72h no verificables** (máx 7h de futuro, `AUDIT_RESULTADOS.md` §4). Casi todo lo de abajo se prueba con `lab_trades` + klines públicas; lo vivo sirve para forward-testing.

### Harness común (para no repetirlo en cada idea)
1. **Reconstruir eventos** con `wyckoff_lab.wyckoff_events()` sobre klines 4h gratis (`binanceusdm`): da por evento el **timestamp de apertura de la vela de entrada**, el **soporte/resistencia barridos** y el **low/high de la vela de ruptura**.
2. **Bajar solo ventanas de 1m** alrededor de cada evento (0–120 min), no el histórico completo: ~2.500 eventos × 120 filas ≈ 300k filas (barato; el histórico completo de 1m serían ~60M filas por 29 pares y es innecesario).
3. **Taker buy/sell**: `taker_buy_base_volume` (índice 9 del kline crudo de `/fapi/v1/klines`); ccxt devuelve 6 columnas, hay que usar el endpoint crudo (verificado en specs 020/021). Funding: `fetch_funding_rate_history`.
4. **Unidad de bootstrap**: re-muestrear **días/velas compartidas**, no trades.

---

## Ranking (por valor esperado × probabilidad de ser real / costo)

| # | Idea | Ángulo | Prioridad |
|---|---|---|---|
| I01 | Curva de los primeros minutos + costo real del retraso de 7 min | entrada / retraso | **Alta** |
| I02 | Invalidación temprana si pierde el mínimo barrido (15–30 min) | invalidación | **Alta** |
| I03 | Entrada límite en el nivel barrido (retest / caza del mechazo) | entrada | **Alta** |
| I04 | Confirmación intra-4h (primera 5/15m y micro-ruptura del extremo) | entrada | **Alta** |
| I05 | Clúster: líder vs rezagado y BTC en los primeros 15 min | clúster | Media-Alta |
| I06 | Volumen de los primeros minutos: expansión vs contracción | micro | Media-Alta |
| I07 | Frecuencia del "segundo barrido" del mínimo barrido (reflexividad MM) | otro planeta | Media-Alta |
| I08 | Taker flow de los primeros 15 min (ángulo nuevo vs spec 021) | micro | Media-Alta |
| I09 | No entrar si hay gap adverso en la apertura | cuándo NO | Media |
| I10 | No entrar si desplome inmediato con volumen alto | cuándo NO | Media |
| I11 | Break-even tras +X% y parciales (resuelto con 1m) | salidas | Media |
| I12 | Qué hacer con el aviso tardío (>2h) | retraso | Media |
| I13 | Mensajes de seguimiento del bot a 5/15/60 min | bot ayuda | Media |
| I14 | Sesgo por hora UTC / ventana de funding | calendario | Media-Baja |
| I15 | Fin de semana | calendario | Media-Baja |
| I16 | Volumen ≥5x o clúster gigante (>10) como "no entrar" | cuándo NO | Media-Baja |
| I17 | Proxy de spread/volatilidad de los primeros minutos | micro | Baja |
| I18 | Artefacto de orden de aviso (el bot recorre pares en orden) | otro planeta | Baja |

---

## I01 — Curva de los primeros minutos y costo real del retraso de 7 min

**(a)** Nombre: "La primera hora después del aviso".
**(b)** Hipótesis y mecanismo: el aviso llega ~7 min después de la apertura (`AUDIT_RESULTADOS.md` §3b). Si en springs de capitulación el precio suele **caer primero** (MAE mediana −3.6%), entrar a mercado tarde puede ser *mejor* precio en promedio, pero también puede significar entrar justo antes de seguir cayendo. Para upthrust, al revés. Mecanismo: tras una liquidación, hay "vacío" de liquidez y el libro tarda en rearmarse → mechazos en los primeros minutos.
**(c)** Cómo probarla: para cada evento, klines **1m** en [t0, t0+120min] (`t0` = `open_timestamp` del trade). Series: `ret(k) = (close_1m[t0+k] − open_rate)/open_rate` para k=1,3,5,7,10,15,30,60,120; también `min`/`max` acumulados hasta cada k. Comparar contra `profit_ratio` final y contra `open_rate`. Reportar mediana y distribución por dirección (`is_short`) y por tamaño de clúster.
**(d)** Criterio pre-registrado: la idea "esperar 7 min es mejor" se confirma si la media de `ret(7)` es **favorable** (para longs, <0) en IS y OOS con IC95% por día excluyendo 0, y si entrar en `ret(7)` mejora la media por trade ≥ +0.2% frente a `open_rate`. Se descarta si el signo cambia entre períodos o el IC incluye 0.
**(e)** Tamaño esperado: **chico**. El deslizamiento medido en n=6 fue ±0.5% (`AUDIT_RESULTADOS.md` §3b); esperaría efectos de ~0.1–0.4% por trade, no más.
**(f)** Ruido: **MEDIO** (ventanas cortas son ruidosas; el signo puede invertirse por régimen).
**(g)** Costo: **bajo** (~3–5 h de código/datos; reusa el harness).

## I02 — Invalidación temprana si pierde el mínimo barrido

**(a)** "Si pierde el mínimo del spring, el patrón falló".
**(b)** Mecanismo: el mínimo barrido es imán de liquidez (stops). Si el precio lo pierde **con volumen** en los primeros 15–30 min, es continuación del tramo bajista, no absorción. Si lo defiende, es el escenario Wyckoff clásico. Ataca directamente la cola mala (stop −10%, 12–16% de los trades).
**(c)** Con klines 1m: `min_1m` en [t0, t0+15/30/60min] vs `low` de la vela de ruptura (nivel barrido, reconstruido en el harness). Comparar `profit_ratio` de los grupos "perdió el nivel" vs "lo defendió"; medir además cuántos de los que "perdieron" habrían tocado el stop −10% igual.
**(d)** Pre-registrado: confirmada si el grupo que pierde el nivel tiene media **peor en IS y OOS** (n≥30 cada uno, IC por día sin 0) y si salir en ese punto evita ≥ la mitad de los stops −10% **sin** cargarse la media de los que sí ganaban. Descartada si la mejora se debe a recortar ganadores (whipsaw).
**(e)** Tamaño esperado: **potencialmente el más grande de todos** (el stop −10% se toca en 12–16%: `AUDIT_RESULTADOS.md` §2e), pero el beneficio neto depende de cuántos rebotes sanos tocan el mínimo de nuevo primero (el stop estructural bajo el mínimo ya dio <50% de acierto en `AUDIT_MEJORAS.md` §3 → el "segundo barrido" es frecuente; ver I07).
**(f)** Ruido: **MEDIO-ALTO** (el óptimo de 15 vs 30 vs 60 min es fácil de sobreajustar).
**(g)** Costo: **medio** (~6–10 h; exige manejar trayectoria 1m y definir el nivel con cuidado).

## I03 — Entrada límite en el nivel barrido (retest / "caza del mechazo")

**(a)** "Orden límite en el nivel barrido en vez de market".
**(b)** Mecanismo: el mercado institucional suele re-testea el extremo barrido antes de despegar; si el resorte es real, el retest sostiene. Un límite captura mejor precio; si no vuelve, no entrás (menos señales, mejor calidad de fill).
**(c)** Con 1m: para cada evento, ¿el precio vuelve a tocar `nivel_barrido` (long) o `nivel_barrido` (short) dentro de [t0, t0+2h]? Serie: `touched`, `t_fill`, `open_rate_fill = nivel ± tick`. Comparar media de los "fill" contra media a mercado.
**(d)** Pre-registrado: confirmada si entrar solo en el retest **mejora la media por trade ≥ +0.3% en IS y OOS** con n≥30 por período, y la tasa de fill es suficiente para que el retorno total sea positivo en ambos. Descartada si el fill captura mayormente los fallos (selección adversa: "solo te llenan cuando va a seguir cayendo").
**(e)** Tamaño esperado: **medio** (mejor fill ~0.5–1.5% en los casos que llenan), pero se pierden los que nunca vuelven → neto incierto.
**(f)** Ruido: **MEDIO** (selección adversa clásica; hay que medirla explícitamente).
**(g)** Costo: **bajo-medio** (~5 h).

## I04 — Confirmación intra-4h (primera 5/15m y micro-ruptura del extremo)

**(a)** "No entrar hasta ver la primera vela de 5/15 min".
**(b)** Mecanismo: exige que la absorción se confirme dentro de la vela de 4h; reduce entradas en "cuchillo cayendo".
**(c)** Con 1m (agregar a 5m/15m): `signo_5m`/`signo_15m` (close vs open) y si el precio **rompe el máximo de la vela de confirmación** (long) o el mínimo (short). Comparar `profit_ratio` de "hubo confirmación" vs "no hubo"; calcular media y tasa de stop.
**(d)** Pre-registrado: confirmada si la confirmación **reduce la tasa de stop ≥3 pp y sube la media ≥+0.2%** en IS y OOS (n≥30, IC por día sin 0). Descartada si solo baja la media (entrar más caro) sin reducir stops.
**(e)** Tamaño esperado: **chico-medio** (~0.1–0.5% por trade; el costo de confirmar es entrar más arriba).
**(f)** Ruido: **MEDIO** (múltiples variantes de "confirmación" invitan a p-hacking; hay que fijar una sola regla).
**(g)** Costo: **bajo-medio** (~5 h).

## I05 — Clúster: líder vs rezagado y BTC en los primeros 15 min

**(a)** "El primero que se mueve manda".
**(b)** Mecanismo: en capitulaciones de todo el mercado el edge es en gran parte beta común (`AUDIT_RESULTADOS.md` §2c). Si BTC (y los majors) muestran signo alcista en los primeros 15 min, los springs rezagados limpian; si BTC sigue bajando, los springs tempranos son trampas. Además, ordenar por quién reacciona primero podría elegir el mejor par.
**(c)** Con 1m: agrupar eventos por `open_timestamp` compartido; calcular `ret_BTC(15m)` (BTC/USDT:USDT) y `ret_i(15m)` de cada par; correlación con `profit_ratio` de los rezagados. Definir "líder" = mayor `ret(15m)` o mayor caída previa.
**(d)** Pre-registrado: confirmada si "entrar solo si `ret_BTC(15m)` > 0" o "elegir el líder" mejora la media **en ambos períodos** (n≥30, bootstrap por vela/día). Descartada si reproduce solo el efecto "clúster grande es mejor" ya conocido (hay que hacer el test *condicional al tamaño de clúster*).
**(e)** Tamaño esperado: **medio** (filtrar por beta podría explicar buena parte del +2% de los clústeres), pero puede ser solo re-descubrir que "todo el mercado rebota".
**(f)** Ruido: **MEDIO-ALTO** (el n efectivo es bajo: ~131 velas IS, `AUDIT_RESULTADOS.md` §2c).
**(g)** Costo: **medio** (~6–8 h).

## I06 — Volumen de los primeros minutos: expansión vs contracción

**(a)** "Sin volumen de continuación, el resorte se apaga".
**(b)** Mecanismo: la absorción Wyckoff requiere que el volumen se **sostenga** tras el evento; una deriva con volumen decreciente es simple rebote de cortos.
**(c)** Con 1m: `vol_5m`, `vol_15m`, `vol_30m` y su ratio vs la media de la misma franja horaria de los días previos; contra la `break_relative_volume` de la vela de ruptura. Buckets por ratio; comparar `profit_ratio`.
**(d)** Pre-registrado: confirmada si el cuartil de mayor expansión de volumen a 15/30 min supera al de menor expansión **en IS y OOS** (n≥30, IC por día sin 0). Descartada si el signo se invierte.
**(e)** Tamaño esperado: **chico-medio** (probablemente +0.2–0.8% de diferencia entre cuartiles).
**(f)** Ruido: **MEDIO** (estacionalidad horaria del volumen; hay que normalizar por hora del día).
**(g)** Costo: **bajo** (~4 h; los datos ya se bajan en I01).

## I07 — Frecuencia del "segundo barrido" (reflexividad de market maker)

**(a)** "La mecha del resorte es un imán, no un piso".
**(b)** Mecanismo (visión MM/institucional): el mínimo barrido concentra stops y órdenes límite; el MM tiene incentivo a volver a tocar esa zona para llenar tamaño antes de mover. Predice exactamente la MAE mediana −3.6% y que el stop estructural bajo el mínimo rinda <50% (`AUDIT_MEJORAS.md` §3). Es un **diagnóstico** que informa I02/I03.
**(c)** Con 1m: por evento, ¿el precio vuelve a tocar `±0.1%` alrededor del nivel barrido dentro de [0,2h]? Serie: `second_sweep` (bool), `t`, `profundidad` (cuánto lo penetra de nuevo). Comparar resultado final y MAE de los que re-tocan vs no.
**(d)** Pre-registrado (es medición, no filtro): confirmada como hecho si la frecuencia de re-toque es **>40% en IS y OOS** y el re-toque se asocia a peor MAE. Se descarta si la frecuencia es baja (<20%), en cuyo caso I02/I03 pierden base.
**(e)** Tamaño esperado: la *frecuencia* es el hallazgo (si es alta, es grande y accionable); el efecto sobre el retorno, indirecto.
**(f)** Ruido: **BAJO** (es una medición descriptiva; difícil de inventar, fácil de verificar).
**(g)** Costo: **bajo** (~3 h; comparte datos con I01/I02).

## I08 — Taker buy/sell de los primeros 15 min

**(a)** "Absorción en las primeras velas".
**(b)** Mecanismo: el agresor vendedor debe agotarse. Spec 021 probó taker flow en la **vela de ruptura** y fue inconcluso (signo invertido). Ángulo **nuevo**: mirar el imbalance **después** del aviso, en los primeros 15 min de la vela de entrada.
**(c)** Con endpoint crudo: `imbalance = taker_buy_base_volume / volume` en los primeros 5/15 min; bucket por imbalance; comparar `profit_ratio`.
**(d)** Pre-registrado: confirmada si imbalance alto (compradores dominan tras un spring) mejora media **en IS y OOS** (n≥30, IC por día sin 0). Descartada si invierte signo entre períodos (como en spec 021).
**(e)** Tamaño esperado: **chico** (spec 021 no encontró nada estable; no esperaría más de 0.2–0.5%).
**(f)** Ruido: **ALTO** (ya falló una vez con el mismo insumo).
**(g)** Costo: **bajo-medio** (~4–6 h; ojo con el endpoint crudo, no ccxt estándar).

## I09 — No entrar si hay gap adverso en la apertura

**(a)** "Si la vela de entrada abre lejos del cierre de confirmación, no entres".
**(b)** Mecanismo: un gap grande contra la señal indica continuación, no absorción. El laboratorio entra al `open` sin modelar el gap respecto al cierre previo (`wyckoff_lab.py:10-12`), pero el operador sí lo ve.
**(c)** Con `open_rate` del trade vs `close` de la vela de confirmación (klines 4h): `gap_pct = (open_rate − close_conf)/close_conf`. Buckets; comparar `profit_ratio`, separando gap a favor y en contra.
**(d)** Pre-registrado: confirmada si gaps adversos >X% tienen media peor **en IS y OOS** y excluirlos mejora la media (n≥30, IC por día). Descartada si el gap adverso se asocia a mejor retorno (mean reversion).
**(e)** Tamaño esperado: **chico** (los gaps de 4h en futuros suelen ser <1% salvo eventos extremos).
**(f)** Ruido: **MEDIO**.
**(g)** Costo: **bajo** (~3 h; datos 4h).

## I10 — No entrar si desplome inmediato con volumen alto

**(a)** "Primeros 15 min rojos con volumen = salir del radar".
**(b)** Mecanismo: captura la combinación de I02+I06, pero como regla de "no entrar" en vez de stop.
**(c)** Con 1m: `ret_15m < −Y%` **y** `vol_15m > Z×` la media → marcar; comparar `profit_ratio` del grupo.
**(d)** Pre-registrado: confirmada si el grupo marcado tiene media negativa **en IS y OOS** (n≥30) y excluirlo sube la media del resto ≥+0.3%. Descartada si el grupo marcado tiene peor MAE pero igual media (los que rebotan).
**(e)** Tamaño esperado: **medio** (junto con I02 es donde veo más chance).
**(f)** Ruido: **MEDIO-ALTO** (dos umbrales = más sobreajuste).
**(g)** Costo: **bajo** (~3 h, reusa I01).

## I11 — Break-even tras +X% y parciales (resuelto con 1m)

**(a)** "Mover el stop a break-even tras +X%; tomar parcial en +Y%".
**(b)** Mecanismo: la mediana sufre −3.6% antes de resolverse y hay pocos días que concentran todo el resultado (`AUDIT_RESULTADOS.md` §2a). Un BE demasiado temprano corta los grandes ganadores (que son todo el PnL); demasiado tarde no protege.
**(c)** **No** se puede medir con `min_rate`/`max_rate` (path-dependency, `AUDIT_MEJORAS.md` §3). Hay que resolver con klines 1m: simular trayectoria, definir BE tras +X% y parcial 1/3 en +Y%, comparar contra el baseline 72h/stop −10% con `profit_ratio` neto.
**(d)** Pre-registrado: confirmada si alguna combinación fija (X,Y pre-definidos **antes** de mirar resultados) mejora media **en IS y OOS** (n≥30, IC por día sin 0) **y** no destruye la cola de ganadores. Descartada si el mejor resultado aparece solo al optimizar X/Y (sobreajuste).
**(e)** Tamaño esperado: **chico** (concentración en 5 días hace que cualquier recorte tienda a restar).
**(f)** Ruido: **ALTO** (dos parámetros libres sobre pocos días efectivos).
**(g)** Costo: **medio** (~6–8 h; ya existe infra de simulación en `scripts_estrategia/experimentos_lab.py`).

## I12 — Qué hacer con el aviso tardío (>2h)

**(a)** "Alerta retardada: ¿esperar o descartar?".
**(b)** Mecanismo: si el bot estuvo apagado, el precio ya se movió. El bot ya marca "ALERTA RETARDADA" (>2h, `wyckoff_alerts.py:336-343`), pero no dice qué hacer. El único caso medido (radar AVAX) tuvo −5.44% de deslizamiento (`AUDIT_RESULTADOS.md` §3b).
**(c)** Con 1m y klines 4h: **simular** el retraso artificialmente sobre cada evento del laboratorio, entrando a `open_rate` + 15/60/120/240 min en vez del open; medir degradación de media y stop.
**(d)** Pre-registrado: confirmada la regla "si >2h, no entrar" si la media de entradas a +240 min es ≤0 o pierde ≥0.5% frente al baseline **en IS y OOS** (n≥30). Descartada si el retraso no degrada (mercado lateral tras el evento).
**(e)** Tamaño esperado: **potencialmente grande en el caso tardío** (el −5.44% sugiere cola fea), pero es un escenario poco frecuente.
**(f)** Ruido: **BAJO-MEDIO**.
**(g)** Costo: **bajo** (~4 h; reusa I01).

## I13 — Mensajes de seguimiento del bot a 5/15/60 min

**(a)** "Estado del plan: sigue válido / invalidado".
**(b)** Mecanismo: no es un edge, es **reducir el error humano**. El bot ya conoce el nivel barrido y el stop; puede re-chequear la última vela de 5/15m y avisar "perdió el mínimo del spring (invalidado, según la regla X)" o "sin cambios".
**(c)** No requiere backtest: es un **envelope informativo**. Implementable con los datos que el bot ya trae cada ciclo. Reglas de "válido/invalidado" deben salir de I02 (pre-registradas), no inventarse.
**(d)** Criterio: no es estadístico; se evalúa por **usabilidad** (¿el operador actuó mejor?) y por no inventar datos ni prometer rendimiento. Toda etiqueta debe citar la regla y ser "hipótesis no confirmada en vivo" mientras no haya ≥50 alertas (`VERIFICACION_FILTROS.md`, decisión final).
**(e)** Tamaño esperado: no aplica (mejora de ejecución, no de señal).
**(f)** Ruido: **BAJO** como idea de producto; **ALTO** si las reglas de invalidación no están validadas.
**(g)** Costo: **medio** (más de producto que de datos).

## I14 — Sesgo por hora UTC / ventana de funding

**(a)** "Las 00/08/16 UTC (funding) cambian el comportamiento".
**(b)** Mecanismo: funding y liquidaciones concentran flujo en 00/08/16; las aperturas de sesión (00 Asia, 08 Londres, 12/16 NY) pueden sesgar el rebote.
**(c)** Con `open_timestamp` de los trades (ya está en los zips: 6 velas posibles) y funding history: buckets por hora UTC y por "dentro/fuera de ventana funding ±15 min". Comparar `profit_ratio`.
**(d)** Pre-registrado: confirmada solo si **una** hora (o la ventana funding) mejora en IS **y** OOS con n≥30 e IC por día sin 0. Descartada si hay inversión de signo. **Ojo**: `AUDIT_MEJORAS.md` ya reporta "Horas UTC individuales: inversión de signo cruzada" → probable ruido.
**(e)** Tamaño esperado: **muy chico o nulo**.
**(f)** Ruido: **ALTO** (6 buckets × 2 períodos = falso positivo casi seguro).
**(g)** Costo: **bajo** (~2 h), pero poca prioridad.

## I15 — Fin de semana

**(a)** "Sábado/domingo drenan el resultado".
**(b)** Mecanismo: menos liquidez y sin expansión institucional; `AUDIT_MEJORAS.md` reporta fines de semana casi nulos (+0.20%/+0.37%) pero **sin** pasar por el bootstrap por día.
**(c)** Con `open_timestamp`: `weekday`; comparar media/win IS y OOS.
**(d)** Pre-registrado: confirmada si excluir sáb/dom mejora la media en **ambos** períodos con n≥30 (¡ojo: n de fin de semana es 73/50, `AUDIT_MEJORAS.md`, cerca del piso!). Descartada si el IC por día incluye 0 (muy probable con ese n).
**(e)** Tamaño esperado: **chico** si es real.
**(f)** Ruido: **ALTO** (n bajo + comparación múltiple).
**(g)** Costo: **bajo** (~2 h).

## I16 — Volumen ≥5x o clúster gigante (>10) como "no entrar"

**(a)** "Demasiado volumen puede ser desliste, no absorción".
**(b)** Mecanismo: `AUDIT_MEJORAS.md` §2a reporta que `RV ≥5x` colapsa en OOS (−3.84%, n=26, win 34.6%); y clústeres de 20-23 pares pueden ser "todo el mercado se cae" más que capitulación.
**(c)** Con `relative_volume` (recalculable) y `concurrent_pairs` (del harness): buckets ≥5x y clúster >10; comparar.
**(d)** Pre-registrado: **muy exigente** dado el n: confirmada solo si la media del bucket es peor en IS y OOS con IC por día sin 0 y **n≥30**; si no llega a 30, se declara "sugerente, no concluyente" (como el propio audit).
**(e)** Tamaño esperado: **posiblemente grande en la cola**, pero con n insuficiente.
**(f)** Ruido: **ALTO** (n=26/28; exactamente el tipo de celda que el proyecto ya descartó).
**(g)** Costo: **bajo** (~2 h), pero baja probabilidad de llegar a conclusión.

## I17 — Proxy de spread/volatilidad de los primeros minutos

**(a)** "Spread ensanchado = mal fill".
**(b)** Mecanismo: en el vacío post-liquidación el spread se ensancha y el fill empeora (no es un edge, es **costo**). El order book histórico **no** existe gratis (`README.md` línea 175, spec 026), así que hay que usar un proxy.
**(c)** Proxy con 1m: `(high−low)/close` de los primeros 1/5 min, o diferencia entre cierres de 1m consecutivos; comparar contra la media de la franja.
**(d)** Pre-registrado: es diagnóstico de costo; se usa para **ajustar el slippage** del backtest, no como filtro. Confirmado si el proxy predice el deslizamiento real (cuando haya ejecuciones reales).
**(e)** Tamaño esperado: **chico** pero honesto (0.05–0.2% por trade).
**(f)** Ruido: **MEDIO** (el proxy no es el spread).
**(g)** Costo: **bajo** (~2 h).

## I18 — Artefacto de orden de aviso (el bot recorre pares en orden)

**(a)** "¿El orden en que el bot avisa sesga el resultado?".
**(b)** Mecanismo: el bot itera `pairs_data` en orden de diccionario/whitelist (`wyckoff_alerts.py:145`) y los avisos salen a segundos de distancia (registro: 15:55:27→:32→:38→:44). En el laboratorio, el modo señal toma todos, pero en modo real entran los primeros slots (elegidos por orden de par, `AUDIT_RESULTADOS.md` §2d: las mejores 513 señales quedan afuera). Sospecha: el "orden de par" correlaciona con el resultado por un artefacto del arranque/whitelist, no por mérito.
**(c)** Con lab_trades en modo señal: asignar `rank_whitelist` (posición en `config_wyckoff_lab.json:6-14`) y correlacionar con `profit_ratio`; con el registro vivo, correlacionar `recorded_at` rank con el resultado (hoy n=1 vela, insuficiente).
**(d)** Pre-registrado: confirmada si el rank correlaciona con el resultado **en IS y OOS** (IC por día sin 0). Si correlaciona, es una **advertencia metodológica** (el "+92%" del modo real es artefacto de orden), no un edge.
**(e)** Tamaño esperado: **desconocido**; si aparece, es importante por su implicancia sobre el modo real.
**(f)** Ruido: **MEDIO-ALTO**.
**(g)** Costo: **muy bajo** (~1–2 h, solo mirar zips y config).

---

## Top-5 recomendado para probar PRIMERO

1. **I01 (curva de los primeros minutos + costo del retraso)** — es literalmente la pregunta del operador, cuesta poco y con klines 1m por ventana se responde en días. Además habilita I02/I10/I12.
2. **I02 (invalidación temprana por pérdida del mínimo barrido)** — máximo potencial para recortar la cola mala (stop −10% en 12–16%). Riesgo de whipsaw, pero es donde puede haber plata real.
3. **I03 (entrada límite en el nivel barrido)** — aprovecha I07; si el retest es frecuente, mejora el fill sin cambiar la tesis.
4. **I05 (líder/rezagado + BTC primeros 15 min)** — ataca directamente el hecho de que el edge es beta de capitulación; filtrar por BTC en los primeros minutos puede ser el filtro más honesto de todos.
5. **I13 (mensajes de seguimiento del bot)** — alto valor operativo, costo medio, y obliga a pre-registrar las reglas de "válido/invalidado" (evita inventar datos).

## Las 3 ideas más tentadoras que probablemente sean RUIDO

1. **I14 (sesgo por hora UTC / ventana de funding)** — 6 buckets × 2 períodos con `AUDIT_MEJORAS.md` ya mostrando inversión de signo: candidata número uno a falso positivo.
2. **I16 (volumen ≥5x / clúster gigante)** — números llamativos (−3.84% OOS) sobre **n=26**, justo el tipo de celda que el proyecto ya refutó (`VERIFICACION_FILTROS.md`).
3. **I11 (break-even / parciales optimizados)** — dos parámetros libres sobre un resultado concentrado en ~5 días (`AUDIT_RESULTADOS.md` §2a): fácil de "encontrar" algo que no replica.

*(I08 taker-flow y I15 fin de semana quedan justo detrás: tienen una razón de ser, pero ya fallaron o tienen n demasiado bajo como para creerles sin el bootstrap por día.)*

## Aclaraciones de honestidad
- Las ideas marcadas como **especulación sin dato** son: **I07** (frecuencia del segundo barrido — mecanismo plausible, dato no medido aún), **I14** (funding/hora, con dato débil y de signo invertido), **I17** (spread: uso un **proxy**, no hay order book histórico) e **I18** (artefacto de orden). Todo lo demás parte de cifras citadas de `lab_trades`/auditorías.
- **No inventé cifras**: cada número sale de los archivos listados al inicio. Donde el dato es de `AUDIT_MEJORAS.md` (Gemini) lo marco como **no confirmado por el bootstrap por día** de `VERIFICACION_FILTROS.md`.
- **Limitación dura**: retornos 24/72h de alertas vivas **no verificables** hoy; el forward-test requiere ≥50 alertas reales (`VERIFICACION_FILTROS.md`).

---

### Nota final de modo

No escribí `BRAINSTORM_OPENCODE.md` porque estoy en **Plan mode** (no puedo modificar archivos del repo). Lo anterior es el documento íntegro: si cambiás a un agente normal y me decís "escribilo", lo creo en `BRAINSTORM_OPENCODE.md` en la raíz del clon sin tocar ningún otro archivo. Si preferís, también puedo dejarlo en la ruta permitida de Plan mode (`C:\Users\Proyecto Z\.opencode\plan`).
