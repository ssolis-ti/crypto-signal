# Spec 036: Qué pasa en los minutos críticos después de la alerta

Pregunta del operador: después de recibir una alerta (cierre de vela de 4h), qué pasa en los minutos 1, 3,
5, 10, 15, 30, 1 h y 2 h de la vela siguiente, y cómo aprovecharlo.

## Método

- Brainstorm independiente de opencode/DeepSeek (18 ideas) y agy/Gemini (17 ideas): `brainstorm/`.
- Medición con velas de **1 minuto** de Binance USD-M (endpoint público) de los **2.716 eventos** históricos
  del laboratorio (springs y upthrusts, 2022–2026), desde el cierre de la vela de confirmación hasta +125 min.
  IS = 2022-24, OOS = 2025-26. Bootstrap por día (los eventos comparten velas). Todo relativo a P0 = precio en
  el cierre de la vela; resultado de referencia = precio a las 72 h.
- Scripts en `scripts/`; salidas crudas en `resultado_*.txt`.
- Alcance: crypto-signal es solo de alertas. Freqtrade se usó únicamente como fuente de datos y laboratorio.

## Resultados (springs = long; n = 780 IS / 492 OOS)

| Idea | Resultado | Veredicto |
|---|---|---|
| Recorrido en los primeros minutos | Deriva media ≈ 0 hasta los 10 min; a 2 h +0.3/+0.4%. Excursión adversa mediana −0.2% (5 min), −0.4% (30 min), −0.7% (2 h; p10 −2.3%). El retroceso mediano de −3.6% ocurre a lo largo de los 3 días, no en los primeros minutos | Los primeros minutos son tranquilos |
| Costo del retraso del aviso (~7 min) | Entrar 1–15 min tarde vs. P0: dif −0.10 a +0.03 (IS) y −0.05 a +0.07 (OOS), IC incluye 0. Esperar 1–2 h cuesta −0.34/−0.44 (IS/OOS) | **El retraso de 7 min no cuesta; esperar 1–2 h sí** |
| Esperar confirmación (deriva a favor a los 5/15 min) | No mejora; a los 5 min entrar con deriva en contra rinde igual o más en ambos períodos | Refutada |
| Orden límite retrocediendo 0.3/0.5/1/2% | Se llena 78/66/35/12%. Media si llena mejor, pero EV por señal (no llena = 0) peor: +1.13 a +1.23 vs +1.50 (IS) | Refutada: te perdés los que despegan |
| Orden límite en el soporte barrido | Se llena ~30%; EV por señal +0.46 vs +1.50 (IS), +0.45 vs +1.91 (OOS) | Refutada |
| Segundo barrido / invalidación al perder el mínimo del spring | El mínimo (mediana 4.7% bajo P0) se pierde en 1–4% de los casos en 2 h; salir ahí: dif ≈ 0 [IC incluye 0] | Sin efecto |
| Salir por excursión adversa temprana (0.5%/1%/2%) | 30% de los trades cae 0.5% en 15 min y se recupera; la regla baja la media de +1.50 a +0.64 (IS) | Refutada: destruye valor |
| **Mover el stop a break-even tras +1/2/3%** | Se activa en 87–91% (+1%) y 84–87% vuelve a P0: el acierto cae de 57–59% a 11–15%. Dif −1.57 [−2.91, −0.08] (IS), −1.02 (OOS) | **Confirmada como perjudicial** |
| Toma parcial 50% al +3.5% en 60 min | Se activa en 2–5%; dif ≈ 0 | Irrelevante |
| Flujo taker comprador en los primeros 5 min | Terciles no monótonos (medio > alto ≈ bajo), sin patrón consistente | Ruido (como spec 021) |
| BTC en los primeros 15 min | IS: BTC a favor rinde más (+1.72 vs +1.18); OOS: BTC en contra rinde más (+2.64 vs +1.41) | Ruido: el signo se invierte |
| Hora UTC del cierre (funding, sesiones) | Signos opuestos entre IS y OOS en 08h, 12h y 16h | Ruido |
| Fin de semana (springs) | −0.27/−0.83% vs +1.69/+2.19% en lun–vie; solo 38 días de fin de semana; dif +2.36 [−0.21, +5.92] | Candidato débil: se muestra, no filtra |
| Upthrust (short) | Ninguna regla mejora; el fin de semana se invierte entre períodos | Sin edge en minutos críticos |

No verificable con datos gratis: interés abierto histórico (Binance solo guarda 30 días) y order book histórico.

## Decisión

Solo se llevan al bot las conclusiones sostenidas por los datos, como guía de **ejecución** en la alerta de
spring (el upthrust no tiene edge). Nada filtra alertas. El fin de semana se muestra como hipótesis débil.
