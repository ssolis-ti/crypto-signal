# Spec 041: horarios, continentes y auditoría del reloj

Brainstorm de opencode (DeepSeek) y agy (Gemini) sobre si el resultado del spring depende de CUÁNDO
cierra la vela de confirmación, más una auditoría independiente del manejo de relojes en el código
(`brainstorm/`). Coincidieron en casi todo; abajo, lo que se decidió.

## Parte A: experimento de horarios (criterio fijado ANTES de correr)

Datos: springs del laboratorio (`WyckoffLab_SpringH72_SL10`, señal, 860 IS / 525 OOS), retorno neto por
trade. "Hora" = hora UTC de apertura del trade = cierre de la vela de confirmación. Los agentes
propusieron hipótesis con direcciones opuestas para las mismas horas (funding), por eso se fija cada
dirección de antemano.

| id | corte | dirección fijada |
|---|---|---|
| H1 | cierre en hora de funding (00/08/16 UTC) vs (04/12/20) | funding PEOR (dif < 0) |
| H2 | cierre 12:00 o 16:00 UTC (apertura Europa/EEUU) vs resto | ese bloque MEJOR (dif > 0) |
| H3 | solo eventos con >= 5 pares simultáneos: cierre 12/16/20/00 UTC (horario occidental) vs 04/08 (Asia) | occidental MEJOR (dif > 0) |
| H4 | fin de semana "puro" (cierre entre sáb 04:00 y dom 16:00 UTC) vs resto | fin de semana PEOR (dif < 0) |
| H5 | inicio/fin de mes (últimos 3 y primeros 3 días UTC) vs resto | inicio/fin MEJOR (dif > 0) |

Familia de k=5 comparaciones: IC bootstrap por DÍA al 99% (percentiles 0.5 / 99.5), 3000 remuestreos.
Aprueba SOLO si, en la dirección fijada: (1) signo correcto en IS y en OOS; (2) IC unido excluye 0;
(3) |diferencia unida| >= 0.5 pp; (4) >= 30 días distintos por celda y por período. Si no cumple todo:
no se aplica; si aprueba, solo se muestra/registra como hipótesis hasta >= 50 alertas reales maduras.

Descriptivo (sin veredicto): media por cada una de las 6 horas; distribución en hora local de Santiago;
reapertura CME (cierre lunes 00:00 UTC), por su n chico.

Pendientes por costo (no en esta ronda): "sesión propia del par" (requiere clasificar pares a priori),
calendario macro, vencimiento de opciones, feriados de Asia (n < 50).

## Parte B: auditoría del reloj

Hallazgos coincidentes de ambos agentes, verificados por mí; ver la sección de resultados abajo.

## Resultado parte A (resultado_horarios.txt)

**Ninguna de las 5 hipótesis aprueba.** Tres invierten el signo entre 2022-24 y 2025-26:
- H1 funding peor: IS -0.05 pp, OOS -1.43 pp, unido -0.58 [IC99% -3.55, +2.12].
- H2 cierre 12/16 UTC mejor: IS +2.94, OOS **-3.28** (signo invertido), IC [-2.93, +4.20].
- H3 clúster >= 5, horario occidental mejor: IS +4.26, OOS **-3.27** (invertido); algunas celdas con 10-12 días (< 30).
- H4 fin de semana puro peor: IS -0.99, OOS -4.10 (mismo signo en ambos, pero solo 29 días de fin de
  semana, IC [-7.12, +0.61] incluye 0). Sigue siendo candidato débil; no se filtra.
- H5 inicio/fin de mes mejor: IS +0.20, OOS **-4.70** (invertido).

Descriptivo: la media por hora UTC de cierre cambia de signo o de orden entre períodos (12:00 UTC:
+6.78% IS vs +1.13% OOS; 16:00 UTC: +2.61% vs -2.51%; 08:00 UTC: +0.10% vs +3.03%): ruido, no estructura.
Reapertura CME (cierre lunes 00:00 UTC): n=22, +3.10% (n muy chico, sin conclusión).

**Dato operativo:** el 31% de los avisos llega entre las 00:00 y las 06:59 hora de Santiago (mientras
el operador duerme), y por el costo medido de la demora (~0.5 pp por 4 h) eso importa más que cualquier
efecto de horario de mercado. Por eso las mejoras del bot van por el lado de mostrar la hora (UTC y
local) en el aviso, no de filtrar por hora.

## Resultado parte B: auditoría del reloj (hallazgos de ambos agentes, verificados)

Corregido en el código (ver commit): 
1. `drop_unclosed_candle` dependía solo del reloj del PC (repintado si adelanta, ceguera si atrasa;
   Docker/WSL2 se desfasa al suspender): ahora usa la hora del exchange, medida cada 10 min (`[RELOJ]` en el log).
2. La alerta no mostraba ninguna hora: ahora dice el cierre en UTC y en hora de Santiago, con día de la semana.
3. `settings.timezone` no llegaba al `MessageBuilder` (`creation_date` siempre en UTC): propagado.
4. Logs sin marca de tiempo: ahora llevan hora UTC.
5. El ciclo dormía 300 s después de cada vuelta (deriva): ahora se alinea al reloj de pared, unos segundos
   después de cada múltiplo de 5 min (las velas de 4 h cierran en múltiplos de 5 min).
6. La hora usada para "ALERTA RETARDADA" ahora también sale del reloj del exchange.
7. `oi_change_24h_pct` se graba solo si el historial cubre >= 23 h.
8. **Con 30 pares corrían 2 workers y el conteo de "pares simultáneos" quedaba partido** (efecto de
   subir `top_n` de 20 a 30 con `market_data_chunk_size: 20): ahora con las alertas Wyckoff activas un solo
   worker cubre todos los pares.
Sin cambio: fin de semana definido por el día UTC de cierre (coherente con el backtest); ahora el día y la hora
aparecen en el aviso, lo que elimina la ambigüedad (una vela vie 20:00-24:00 UTC cierra sáb 00:00 UTC).

## Seguimiento: ¿día/noche por continente cambia el riesgo o la frecuencia? (`sesiones_riesgo.py`)

Pregunta del operador: "en algunos países es de día y en otros de noche, ¿puede haber horarios óptimos?".
Bloques definidos antes de mirar, por hora UTC de entrada: Asia/madrugada UTC (00, 04), Europa (08, 12), EEUU/tarde (16, 20).
Exploratorio (no cuenta como filtro).

- **Frecuencia (lo único con estructura clara):** señales por hora UTC de cierre: 00:00 → 350, 04:00 → 193, 08:00 → 230,
  12:00 → 114, 16:00 → 185, 20:00 → 313. Se concentran en el cierre de EEUU / apertura de Asia (20:00 y 00:00 UTC = 48%)
  y son poco frecuentes en la ventana 12:00 UTC.
- **Riesgo/resultado:** acierto 51-66% y tasa de stop 7.5-19.7% según bloque y período, pero sin patrón estable
  (Europa: 51% acierto / 19.7% stop en IS y 66% / 7.5% en OOS). Diferencias vs el resto: acierto entre -2.1 y +2.4 pp,
  tasa de stop entre -5.1 y +5.2 pp, todos con IC95 por día que incluyen 0.
- **Poder:** la diferencia de retorno medio "Asia vs resto" tiene un IC95 de ancho ~4.6 pp: solo se detectarían efectos
  de horario de ~2.5 pp o más por trade. "No se encontró efecto" significa "no hay uno grande", no "no existe".
