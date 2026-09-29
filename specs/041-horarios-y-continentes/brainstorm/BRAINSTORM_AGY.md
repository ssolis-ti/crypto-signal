# Auditoría Cuantitativa de Horarios y Revisión de Código del Reloj

**Rol:** Ingeniero cuantitativo y auditor de código.  
**Entorno:** `crypto-signal` (bot de alertas Telegram; operador manual en Binance futuros, zona horaria `America/Santiago`).  
**Modo:** Solo lectura (sin modificaciones a archivos, sin lectura de `.env` ni `config.yml`).

---

# PARTE A — BRAINSTORM: TIPO DE HORA Y CONTINENTES

### Contexto Cuantitativo de Partida (Hechos Medidos en el Repo)
1. **Muestra total disponible:** 1.385 eventos Spring en 29 pares de Binance futuros (860 en IS 2022–2024 y 525 en OOS 2025–2026).
2. **Medición previa en spec 036 ([resultado_m1.txt](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/specs/036-minutos-criticos/resultado_m1.txt#L99-L105)):** El desglose por hora UTC individual mostró **inversión de signos** entre IS y OOS en las velas de 08:00 UTC (IS $-0.98\%$ vs OOS $+3.61\%$) y 16:00 UTC (IS $+3.11\%$ vs OOS $-1.83\%$). La hora 12:00 UTC tuvo apenas $n=52$ (IS) y $n=50$ (OOS). Fue catalogado como **ruido por sobreajuste y fragmentación muestral**.
3. **Fin de semana:** En spec 036, lun–vie rindió $+1.69\%/+2.19\%$ vs sáb–dom $-0.27\%/-0.83\%$, pero con solo 38 días distintos de fin de semana el IC95% bootstrap por día fue $[-0.21, +5.92\%]$ (incluye 0 $\rightarrow$ candidato débil, no filtra).
4. **Regla de oro metodológica:** Un filtro temporal no puede aprobar por correlación espuria; debe tener un mecanismo microestructural claro, dirección pre-fijada, pasar IS y OOS, y resistir bootstrap por **DÍA** (los eventos en la misma vela comparten destino macro).

---

## Catálogo de Ideas (16 Propuestas Concretas y Distintas)

### 1. Ventana de Liquidación de Funding (Velas 00, 08, 16 UTC vs 04, 12, 20 UTC)
- **Definición operativa:** Columna booleana `is_funding_candle = (close_hour_utc in [0, 8, 16])`.
- **Hipótesis y Dirección:** `is_funding_candle == True` rinde **MENOR** retorno medio (diferencia $< 0$) y sufre mayor excursión adversa temprana (peor MAE a 2h).
- **Mecanismo microestructural:** En Binance futuros, la tasa de funding se liquida en el segundo 00 de las 00, 08 y 16 UTC. Los arbitrajistas de carry (spot-futuros) y creadores de mercado cierran o rotan inventario en los minutos previos al cierre para evitar el pago, inflando artificialmente el volumen (disparando el filtro $\ge 2.5\times$) por razones mecánicas y no por absorción Wyckoff genuina.
- **Muestra ($n$):** Funding: ~740 eventos (~450 IS / ~290 OOS). No-funding: ~645 eventos (~410 IS / ~235 OOS). Muestra balanceada (~53% vs ~47%).
- **Riesgo comparaciones múltiples:** Bajo (partición binaria $1:1$ pre-especificada).

---

### 2. Solapamiento Europa–EEUU (Cierre 16:00 UTC corregido por DST)
- **Definición operativa:** Vela de 4h que finaliza a las 16:00 UTC en horario de verano boreal (EDT) o 17:00 UTC / vela equivalente según apertura de Wall Street ($13:30$ a $16:00$ hora de Nueva York).
- **Hipótesis y Dirección:** Rinde **MENOS** que el baseline (retorno $< +1.5\%$) o sufre mayor tasa de stop-out al $-10\%$.
- **Mecanismo microestructural:** Durante el solapamiento Londres/Nueva York se concentra el volumen institucional global de fondos macro y algoritmos VWAP. Los rompimientos de soporte en esta ventana son con frecuencia rupturas tendenciales reales con gran profundidad de libro ("breakouts"), en lugar de trampas de liquidez minorista fáciles de absorber.
- **Muestra ($n$):** IS $n=108$, OOS $n=62$ (Total: 170 eventos, ~12% del total). **Advertencia: celda pequeña**.
- **Riesgo comparaciones múltiples:** Medio (aislar una de 6 velas sufre del sesgo ya visto en spec 036).

---

### 3. Reapertura de Futuros CME de Bitcoin (Vela Domingo 20:00 UTC $\rightarrow$ Lunes 00:00 UTC)
- **Definición operativa:** Cierre exactamente a las 00:00 UTC del lunes (vela formada domingo 20:00–24:00 UTC).
- **Hipótesis y Dirección:** Rinde **MÁS** que los springs del fin de semana (acercándose o superando la media de días hábiles $+1.8\%$).
- **Mecanismo microestructural:** Los futuros de BTC en CME reabren los domingos a las 22:00 UTC (18:00 ET). Aunque ocurre durante el domingo del operador, el flujo institucional ya regresó dos horas antes de que cierre la vela de 00:00 UTC. La absorción aquí se apoya en la formación del gap semanal de CME.
- **Muestra ($n$):** ~55 eventos totales (~35 IS / ~20 OOS). **Advertencia: muestra muy pequeña (~4% de los eventos)**.
- **Riesgo comparaciones múltiples:** Alto por tamaño muestral pequeño.

---

### 4. Fin de Semana "Puro" (Sábado 04:00 UTC a Domingo 16:00 UTC)
- **Definición operativa:** Velas cuyo cierre ocurre entre sábado 04:00 UTC y domingo 16:00 UTC inclusive (6 velas donde los mercados tradicionales de todo el mundo están cerrados sin solapamiento).
- **Hipótesis y Dirección:** Rinde **MENOS** que días hábiles (retorno $\le 0\%$, win rate $< 50\%$).
- **Mecanismo microestructural:** Ausencia de creadores de mercado institucionales y mesas OTC bancarias; libros delgados donde picos de volumen de $2.5\times$ corresponden a cazas de stops locales de cuentas particulares, sin capital grande que defienda el nivel durante los 3 días posteriores.
- **Muestra ($n$):** Fin de semana puro: ~140 eventos (~85 IS / ~55 OOS). Días hábiles: ~1.245 eventos.
- **Riesgo comparaciones múltiples:** Medio-Bajo (refina la hipótesis ya explorada en spec 036 quitando las velas de frontera).

---

### 5. Coincidencia con Vencimiento Semanal de Opciones Deribit (Viernes 08:00 UTC)
- **Definición operativa:** Vela cerrada el viernes a las 08:00 UTC (vela 04:00 a 08:00 UTC del viernes).
- **Hipótesis y Dirección:** Retorno superior a la media en 72h ($> +2.5\%$) y menor excursión adversa.
- **Mecanismo microestructural:** Más del 80% del open interest de opciones de BTC y ETH vence los viernes a las 08:00 UTC en Deribit. Los creadores de mercado mantienen fijado ("pinning") el precio antes del corte para minimizar el valor intrínseco (teoría de Max Pain). Inmediatamente tras las 08:00 UTC, la descompresión de gamma y el desmonte de coberturas libera compras al contado/perpetuos.
- **Muestra ($n$):** Solo ~45 eventos en todo el historial (~28 IS / ~17 OOS). **Advertencia: muestra diminuta**.
- **Riesgo comparaciones múltiples:** Muy alto. Inviable como filtro duro sin caer en minería de datos.

---

### 6. Home Session del Par (Sesión Asiática vs Sesión Occidental)
- **Definición operativa:** Clasificar previamente los 29 pares en dos categorías según su volumen horario histórico 2021–2023:
  - *Pares Asiáticos* (pico de volumen en 00:00–08:00 UTC, ej. CFX, NEO, VET, FIL).
  - *Pares Occidentales/Globales* (pico en 12:00–20:00 UTC, ej. BTC, ETH, SOL, LINK, AVAX).
  - Regla: `is_home_session = True` si el spring del par ocurre durante su ventana de volumen predominante.
- **Hipótesis y Dirección:** `is_home_session == True` tiene **MAYOR** rentabilidad y win rate que fuera de ella.
- **Mecanismo microestructural:** Un spring en un par asiático ocurrido a las 16:00 UTC ocurre con libro vacío en Asia; cuando despierta su mercado local, el nivel no es respetado. En cambio, si ocurre en su sesión nativa, los creadores de mercado especializados absorben el flujo.
- **Muestra ($n$):** ~650 eventos en sesión nativa, ~735 fuera. Buen balance.
- **Riesgo comparaciones múltiples:** Medio (exige fijar la clasificación de pares *a priori* sin mirar los trades).

---

### 7. Corrección Higiénica por Horario de Verano (DST de EEUU y Europa)
- **Definición operativa:** Normalizar las velas de 4h según la hora de Nueva York (Eastern Time: EDT UTC-4 / EST UTC-5). La apertura bursátil (09:30 ET) cae a las 13:30 UTC en verano boreal pero a las 14:30 UTC en invierno boreal.
- **Hipótesis y Dirección:** Reduce la varianza intra-sesión y elimina la inconsistencia observada en spec 036 entre IS y OOS en las velas de 12h y 16h UTC.
- **Mecanismo microestructural:** La liquidez real se mueve por el reloj solar/laboral de las ciudades financieras (Londres/NY), no por el meridiano de Greenwich. La hora UTC fija de Binance fragmenta de manera distinta el inicio de Wall Street en marzo/noviembre.
- **Muestra ($n$):** No crea celdas nuevas; reclasifica las ~1.385 alertas en etiquetas de sesión dinámicas.
- **Riesgo comparaciones múltiples:** Bajo (es una corrección metodológica previa, no un filtro adicional).

---

### 8. Feriados Bancarios en Asia (Año Nuevo Chino y Golden Week)
- **Definición operativa:** Eventos ocurridos durante los 7 días oficiales del Año Nuevo Lunar (móvil: enero/febrero) y Golden Week (1–7 octubre en China).
- **Hipótesis y Dirección:** Rendimiento inferior (media $< +0.5\%$, similar a fin de semana).
- **Mecanismo microestructural:** Cierre total de mesas OTC y escritorios institucionales en Hong Kong, Singapur y China continental. Caída del volumen neto en altcoins.
- **Muestra ($n$):** Menos de 40 eventos en 5 años. **Advertencia: $n$ estadísticamente inviable**.
- **Riesgo comparaciones múltiples:** Muy alto. Descartar como filtro; solo para registro cualitativo.

---

### 9. Efecto Fin de Mes / Inicio de Mes (Turnaround Institucional)
- **Definición operativa:** Eventos ocurridos en los dos últimos días del mes ($d \ge D_{max} - 1$) vs los dos primeros días ($d \in [1, 2]$) en UTC.
- **Hipótesis y Dirección:** Inicio de mes rinde **MÁS** que fin de mes (diferencia $> 0$).
- **Mecanismo microestructural:** Entradas netas de capital fresco a principios de mes (planes de ahorro, DCA institucional, asignación mensual de tesorerías) apoyan la recuperación del precio tras una barrida; el fin de mes sufre presiones de rebalanceo y ventas tributarias/de comisiones.
- **Muestra ($n$):** Fin de mes: ~90 eventos. Inicio de mes: ~95 eventos. Resto del mes: ~1.200 eventos.
- **Riesgo comparaciones múltiples:** Medio. Muestra de borde modesta.

---

### 10. Gap de Fin de Semana en Futuros CME (Alineación con el Spring)
- **Definición operativa:** Medir la diferencia porcentual entre el precio de cierre de CME del viernes (21:00 UTC) y el precio en la reapertura del domingo a las 22:00 UTC. Si $P_{spot} < CME_{close} - 0.5\%$, clasificar como `bullish_cme_gap = True`.
- **Hipótesis y Dirección:** Springs en domingo noche / lunes con `bullish_cme_gap == True` tienen un EV a 24h y 72h sustancialmente mayor ($> +2.5\%$).
- **Mecanismo microestructural:** Fenómeno empírico de alta recurrencia en cripto: los creadores de mercado arbitran el gap de CME llevándolo al precio de cierre del viernes en las primeras 24–48 horas de la semana.
- **Muestra ($n$):** Apenas ~40 a 50 eventos coinciden con springs en esa ventana.
- **Riesgo comparaciones múltiples:** Alto por muestra acotada.

---

### 11. Coincidencia con Comunicados Macro de EEUU (CPI, FOMC, NFP)
- **Definición operativa:** Vela de 4h que encierra o sigue inmediatamente a un dato de IPC (12:30/13:30 UTC), Nóminas No Agrícolas (primer viernes de mes) o rueda de prensa de FOMC (18:00/18:30 UTC).
- **Hipótesis y Dirección:** Rinde **MENOS** y tiene una tasa de fallo mucho mayor (win rate $< 45\%$).
- **Mecanismo microestructural:** La volatilidad en noticias macro es producto de liquidaciones algorítmicas forzadas y retiro transitorio de liquidez en el libro. El volumen de ruptura $\ge 2.5\times$ refleja desapalancamiento violento, no acumulación intencional de dinero inteligente Wyckoff.
- **Muestra ($n$):** ~110 eventos coinciden con ventanas de noticias macro en los 5 años.
- **Riesgo comparaciones múltiples:** Medio (etiquetado histórico objetivo vía calendario económico).

---

### 12. Interacción Hora UTC $\times$ Clúster de Mercado (Pares Simultáneos $\ge 5$)
- **Definición operativa:** Cruzar la hora de cierre UTC con la condición validada de capitulación general de mercado (`concurrent >= 5`).
- **Hipótesis y Dirección:** El edge masivo de $+2.5\%$ de los clústeres ocurre casi exclusivamente en velas donde participa el mercado americano o en el cierre diario (16:00, 20:00 o 00:00 UTC); los clústeres en horas asiáticas ilíquidas (04:00 UTC) tienen menor seguimiento.
- **Mecanismo microestructural:** Una capitulación generalizada requiere cascadas masivas de liquidación en BTC, las cuales son disparadas por los derivados y mesas de negociación con sede en Occidente.
- **Muestra ($n$):** En los 1.385 eventos, los clústeres abarcan ~400 trades distribuidos en las 6 horas.
- **Riesgo comparaciones múltiples:** Bajo (construye sobre el único edge macro validado del proyecto).

---

### 13. El Lado del Operador: La Ventana de "Alerta Dormida" en Santiago (Chile)
- **Definición operativa:** Velas de confirmación que cierran de madrugada en hora local de Chile (`America/Santiago`):
  - *Invierno (UTC-4, CLT):* Velas de 04:00 UTC (00:00 local) y 08:00 UTC (04:00 local).
  - *Verano (UTC-3, CLST):* Velas de 04:00 UTC (01:00 local) y 08:00 UTC (05:00 local).
- **Hipótesis y Dirección:** El edge intrínseco del mercado es irrelevante si la fricción humana destruye la rentabilidad: entrar con 4 horas de retraso al despertar cuesta $\sim 0.5$ pp de rentabilidad media (medido en spec 039).
- **Mecanismo operativo:** El operador duerme. Una alerta de las 04:00 UTC operada a las 08:00 local lleva 3–4 horas de retraso. A 12h de retraso el acierto cae a 47–52%.
- **Acción cuantitativa:** La alerta debe calcular el retraso respecto a la hora local de Santiago y advertir explícitamente el costo de demora si el operador la lee por la mañana.
- **Muestra ($n$):** Representa exactamente $2/6 = 33.3\%$ de todas las alertas emitidas (~460 eventos).
- **Riesgo comparaciones múltiples:** Cero (no es un filtro de mercado, es gestión de ejecución humana).

---

### 14. Lunes "Low of the Week" (Vela 00:00 a 04:00 UTC del Lunes)
- **Definición operativa:** Vela cerrada a las 04:00 UTC del lunes (primera vela completa de día hábil en Asia/Europa tras el fin de semana).
- **Hipótesis y Dirección:** Rendimiento superior al baseline ($> +2.0\%$).
- **Mecanismo microestructural:** Patrón común en algoritmos de market making: barrer los mínimos establecidos durante la baja liquidez del fin de semana durante las primeras horas de Londres/Tokio para establecer el mínimo semanal ("weekly low") y expandir al alza.
- **Muestra ($n$):** ~55 eventos en total. **Advertencia: muestra chica**.
- **Riesgo comparaciones múltiples:** Alto.

---

### 15. "Valle" de Liquidez Inter-Sesión (Cierre 20:00 UTC)
- **Definición operativa:** Vela de 16:00 a 20:00 UTC (Wall Street cerrando, Europa cerrada, Asia aún no abre).
- **Hipótesis y Dirección:** Mayor tasa de falsos rompimientos en comparación con velas de alta actividad.
- **Mecanismo microestructural:** Período de transición donde el spread se ensancha y el flujo institucional cesa. Sin embargo, en spec 036 acumuló $n=184$ (IS) y $n=110$ (OOS) con retorno positivo consistente ($+0.57\%$ y $+2.64\%$).
- **Muestra ($n$):** 294 eventos en total (~21% de la muestra).
- **Riesgo comparaciones múltiples:** Bajo.

---

### 16. Cierre Diario UTC (Vela 20:00 a 00:00 UTC)
- **Definición operativa:** Vela cerrada a las 00:00:00 UTC (coincide con el cambio de fecha de Binance y cierre de vela 1D).
- **Hipótesis y Dirección:** Rendimiento positivo y consistente en IS y OOS (ya verificado preliminarmente en spec 036: IS $+2.12\%$, OOS $+1.15\%$).
- **Mecanismo microestructural:** Máxima concentración de rebalanceos diarios de fondos y cierres de derivados a nivel global.
- **Muestra ($n$):** IS $n=209$, OOS $n=102$ (311 eventos, la celda más poblada del dataset con 22.5% del total).
- **Riesgo comparaciones múltiples:** Bajo.

---

## Ordenamiento de Ideas por Ratio de Eficiencia Cuantitativa

Ordenadas de mayor a menor por el ratio:
$$\text{Score} = \frac{\text{Valor Esperado (EV)} \times P(\text{Efecto Real})}{\text{Costo de Probar}}$$

| Puesto | Idea | Justificación del Ratio |
|---|---|---|
| **1** | **Idea 13: Gestión de la Ventana de Sueño en Santiago** | $P(\text{real}) = 100\%$ (hecho humano). Costo = 0. Protege directamente el $\sim 0.5$ pp por cada 4h de demora ya medido en spec 039. |
| **2** | **Idea 1: Ventana de Liquidación de Funding (00/08/16 vs 04/12/20 UTC)** | Muestra balanceada (740 vs 645), mecanismo microestructural limpio, datos de funding ya en el repo (`specs/037`), costo de probar bajísimo. |
| **3** | **Idea 12: Interacción Hora UTC $\times$ Clúster de Mercado ($\ge 5$ pares)** | Se monta sobre el único edge masivo validado ($+2.5\%$). Costo analítico bajo con los scripts de spec 035/036. |
| **4** | **Idea 7: Corrección Higiénica por DST en Sesiones EEUU/Europa** | No agrega parámetros; corrige la contaminación que distorsionó las velas de 12h y 16h en spec 036. |
| **5** | **Idea 4: Fin de Semana Puro (Sáb 04h a Dom 16h UTC)** | Mecanismo claro; mejora la definición débil previa de spec 036. Muestra modesta pero integrable. |
| **6** | **Idea 6: Home Session del Par (Asiático vs Occidental)** | Fundamento sólido de liquidez; requiere clasificar los pares *a priori*. |
| **7** | **Idea 11: Coincidencia con Noticias Macro (CPI, FOMC, NFP)** | Lógica económica robusta, pero requiere compilar calendario sin lookahead. |
| **8** | **Idea 3: Reapertura CME (Domingo 20h a Lunes 00h UTC)** | Fuerte fundamento técnico, pero castigada por $n \approx 55$. |
| **9** | **Idea 2: Solapamiento Europa–EEUU (16:00 UTC)** | Celda pequeña ($n=170$ total), propensa a ruido. |
| **10** | **Idea 10: Gap de Fin de Semana CME vs Spot** | Excelente lógica teórica, pero $n < 50$ en springs. |
| **11** | **Idea 9: Efecto Inicio/Fin de Mes** | Muestra de borde reducida, efecto de baja intensidad. |
| **12** | **Idea 16: Cierre Diario UTC (00:00 UTC)** | Celda grande y estable, pero su delta respecto al baseline es modesto. |
| **13** | **Idea 14: Lunes "Low of the Week" (04:00 UTC)** | $n$ pequeño ($~55$). |
| **14** | **Idea 15: Valle de Liquidez (20:00 UTC)** | Diferencial marginal. |
| **15** | **Idea 5: Vencimiento de Opciones Deribit (Viernes 08:00 UTC)** | $n \approx 45$. Ruido casi seguro. |
| **16** | **Idea 8: Feriados Asiáticos** | Menos de 40 eventos en 5 años. Costo alto, significancia nula. |

---

## Criterio de Aprobación Concreto (Pre-Registrado) para las 3 Mejores

Para que cualquiera de las tres mejores ideas de mercado (**Idea 1: Funding**, **Idea 12: Clúster $\times$ Hora**, o **Idea 4: Fin de Semana**) pase de ser una hipótesis a un filtro o regla de alerta:

1. **Partición cronológica estricta:** In-Sample (IS: 2022-01-01 a 2024-12-31) y Out-of-Sample (OOS: 2025-01-01 a 2026-09-22).
2. **Consistencia de signo:** La mejora en el retorno medio por trade ($\Delta \mu = \mu_{\text{regla}} - \mu_{\text{baseline}}$) debe ser estrictamente **positiva tanto en IS como en OOS**. Si en uno da $+1.5\%$ y en otro $-0.8\%$ (como ocurrió con la hora UTC en spec 036), se descarta de inmediato como ruido.
3. **Bootstrap por DÍA con corrección de comparaciones múltiples:**
   - Se agrupan los trades por fecha normalizada (`day`).
   - Se ejecutan 5.000 iteraciones bootstrap remuestreando **días completos** con reemplazo.
   - Para 3 hipótesis simultáneas, corrección de Bonferroni / Šidák al 95%: nivel de confianza $\alpha = 0.05 / 3 \approx 0.0167$ $\rightarrow$ **Intervalo de Confianza al 98.33%**.
   - El IC98.33% de la muestra completa debe **excluir estrictamente el 0**.
4. **Veda de filtrado automático:** Aunque apruebe el laboratorio, **ninguna regla filtrará alertas en el bot** hasta contar con al menos 50 alertas reales maduras en producción (`specs/040`). Solo se registrará y mostrará en el mensaje.

---

# PARTE B — AUDITORÍA DEL RELOJ EN EL CÓDIGO

Revisión exhaustiva línea por línea en todo el directorio `app/`.

---

### Hallazgo 1: Configuración de Timezone Desconectada de Alertas y MessageBuilder
- **Severidad:** **Media**
- **Ubicación:** 
  - [app/behaviour/core.py:107, 178](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/behaviour/core.py#L107-L178)
  - [app/notifications/core.py:37, 41, 84-86](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/notifications/core.py#L37-L86)
  - [app/notifications/builder.py:19, 22, 184](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/notifications/builder.py#L19-L184)
- **Escenario de fallo:**
  1. En `app/behaviour/core.py:107`, el sistema lee `self.timezone = config.settings['timezone']` (ej. `America/Santiago`) y en la línea 178 ejecuta `self.notifier.set_timezone(self.timezone)`.
  2. En `app/notifications/core.py:84-86`:
     ```python
     def set_timezone(self, timezone):
         self.timezone = timezone
         self.chart_renderer.timezone_str = timezone
     ```
     `self.builder` (`MessageBuilder`) fue instanciado en la línea 37 con `timezone_str='UTC'`. `set_timezone` **nunca actualiza `self.builder.timezone_str`**. Por ende, cualquier mensaje generado por `MessageBuilder` con `creation_date` queda congelado en UTC.
  3. `WyckoffAlerter` ni siquiera recibe `self.timezone` en `app/behaviour/core.py:120-128`. Queda completamente huérfano de la zona horaria del operador.
- **Arreglo mínimo propuesto:**
  En `app/notifications/core.py:84`:
  ```python
  def set_timezone(self, timezone):
      self.timezone = timezone
      self.chart_renderer.timezone_str = timezone
      if hasattr(self, 'builder') and self.builder:
          self.builder.timezone_str = timezone
  ```
  Y pasar `timezone=self.timezone` al constructor de `WyckoffAlerter`.

---

### Hallazgo 2: Riesgo de Repintado y Omisión de Velas por Dependencia del Reloj Local en `drop_unclosed_candle`
- **Severidad:** **Alta**
- **Ubicación:** 
  - [app/data/manager.py:25-64, 266-268](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/data/manager.py#L25-L64)
- **Escenario de fallo:**
  `drop_unclosed_candle` utiliza el reloj del sistema operativo local (`now_utc = datetime.now(timezone.utc)`):
  ```python
  last_candle_start_ms = ohlcv[-1][0]
  last_candle_close_ms = last_candle_start_ms + period_seconds * 1000
  if last_candle_close_ms > now_ms:
      return ohlcv[:-1]
  ```
  - **Fallo A (Reloj local adelantado por deriva NTP en Windows):** Si el reloj local está 3 segundos adelantado respecto al exchange, en el segundo 03:59:58 UTC real (04:00:01 reloj local), `last_candle_close_ms > now_ms` es `False`. La vela de las 00:00 que aún está formándose en Binance **no se descarta**. El bot corre análisis técnico sobre una vela viva e incompleta (violando el Principio II: No Repaint).
  - **Fallo B (Reloj local atrasado o latencia de red):** Si el reloj local está 2 segundos atrasado y Binance no ha entregado aún la vela del nuevo período, la vela que acaba de cerrar a las 04:00:00 tiene `last_candle_close_ms (04:00:00) > now_ms (03:59:58)` $\rightarrow$ **se descarta la vela cerrada**. Luego, `DataManager` guarda el dataset en caché por 300 segundos (`TTL_OHLCV = 300` en línea 268). Durante 5 minutos completos el bot queda ciego al evento que acaba de ocurrir.
- **Arreglo mínimo propuesto:**
  Obtener la hora oficial del exchange usando `self.driver.exchanges[exchange].milliseconds()` (o almacenar el `Date` del header HTTP de Binance) y pasarla como `now_utc` a `drop_unclosed_candle`.

---

### Hallazgo 3: Ciclo Asíncrono con Deriva respecto a Velas Fijas (Update Interval Drift)
- **Severidad:** **Media**
- **Ubicación:** 
  - [app/app.py:180-194](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/app.py#L180-L194)
- **Escenario de fallo:**
  El ciclo ejecuta `self.behaviour.run(...)` (que toma 60–90 segundos entre llamadas a la API de Binance con rate limits) y luego ejecuta `time.sleep(300)`. El intervalo entre ejecuciones es de 360 a 390 segundos.
  El bot no tiene un cron sincronizado con el reloj de pared (:00, :05, :10). Si un ciclo corre a las 03:59:40 UTC, termina a las 04:01:00 UTC y duerme 300s, el próximo ciclo no despierta hasta las 04:06:00 UTC, entregando la alerta a las 04:07:30 UTC. Esto causa demoras variables en la notificación.
- **Arreglo mínimo propuesto:**
  Sincronizar el descanso con el reloj de pared:
  ```python
  elapsed_in_block = time.time() % update_interval
  sleep_time = max(5.0, update_interval - elapsed_in_block)
  time.sleep(sleep_time)
  ```

---

### Hallazgo 4: Ausencia Total de Timestamp en las Alertas Enviadas al Operador
- **Severidad:** **Media**
- **Ubicación:** 
  - [app/analysis/wyckoff_alerts.py:338-346, 437-447](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/analysis/wyckoff_alerts.py#L437-L447)
- **Escenario de fallo:**
  Cuando la alerta llega a tiempo, `_stale_notice(timestamp)` retorna `""`. El mensaje de Telegram no incluye en ningún punto a qué hora cerró la vela ni qué día.
  El operador en Chile recibe un mensaje sin hora. Si estuvo lejos del teléfono o la notificación de Telegram se demoró por la red, no tiene forma de saber en el texto si la alerta corresponde a la vela de las 20:00 UTC, 00:00 UTC o 04:00 UTC. Si la demora fue de 1 hora y 50 minutos, `_stale_notice` no se activa (su umbral es 2 horas), y el operador entra tarde a un trade sin saber que el precio ya corrió.
- **Arreglo mínimo propuesto:**
  Incorporar siempre el timestamp explícito en formato dual UTC y local Santiago:
  ```
  🕒 Cierre: 20:00 UTC (17:00 Santiago) | Vela 4h
  ```

---

### Hallazgo 5: Fronteras de Fin de Semana en `_is_weekend_close` (Viernes Noche vs Domingo Noche)
- **Severidad:** **Baja**
- **Ubicación:** 
  - [app/analysis/wyckoff_alerts.py:389-393](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/analysis/wyckoff_alerts.py#L389-L393)
- **Escenario de fallo:**
  `return (timestamp + pd.Timedelta(seconds=CANDLE_SECONDS)).dayofweek >= 5`.
  - La vela de viernes 20:00 a 24:00 UTC cierra sábado 00:00:00 UTC $\rightarrow$ `dayofweek == 5` $\rightarrow$ Marca `Cierre en fin de semana: True`.
  - La vela de domingo 20:00 a 24:00 UTC cierra lunes 00:00:00 UTC $\rightarrow$ `dayofweek == 0` $\rightarrow$ Marca `Cierre en fin de semana: False`.
  Esto reproduce el backtest de Freqtrade (donde el trade entra a la apertura de la vela siguiente), pero desde la perspectiva del operador es contraintuitivo: una vela que se formó un viernes laboral se clasifica como fin de semana, y una vela formada un domingo por la noche se clasifica como día hábil.
- **Arreglo mínimo propuesto:**
  Mantener la lógica para coherencia con el backtest de Freqtrade, pero clarificar en el texto explicativo: `"Cierre sábado 00:00 UTC (fin de semana)"`.

---

### Hallazgo 6: Fragilidad de `_stale_notice` ante Timestamps Naive y Desync de Docker en Windows
- **Severidad:** **Media**
- **Ubicación:** 
  - [app/analysis/wyckoff_alerts.py:376-386](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/analysis/wyckoff_alerts.py#L376-L386)
  - [tests/analysis/test_wyckoff_alerts.py:728-732](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/tests/analysis/test_wyckoff_alerts.py#L728-L732)
- **Escenario de fallo:**
  `elapsed = (self._now_utc() - (timestamp + pd.Timedelta(seconds=CANDLE_SECONDS))).total_seconds()`.
  1. Si `timestamp` fuera un objeto naive (sin timezone), la resta lanza `TypeError: can't subtract offset-naive and offset-aware datetimes` (esto está incluso documentado en el test unitario `test_naive_timestamp_raises_type_error`).
  2. En Docker Desktop para Windows (WSL2), cuando la PC entra en estado de suspensión o hibernación y se reanuda, el reloj de la máquina virtual WSL2 suele quedar congelado en el pasado hasta que Windows fuerza una sincronización NTP. Si el bot se ejecuta con el reloj de WSL2 atrasado, `self._now_utc()` produce un tiempo menor a `timestamp`, resultando en `elapsed < 0`, silenciando completamente el aviso de alerta retardada.
- **Arreglo mínimo propuesto:**
  Sanear el timestamp:
  ```python
  if getattr(timestamp, 'tzinfo', None) is None:
      timestamp = timestamp.tz_localize('UTC')
  ```
  Y verificar sincronización de reloj en contenedor.

---

### Hallazgo 7: Historial de Open Interest en `market_microstructure.py` Asume 24 Horas sin Validar Timestamps
- **Severidad:** **Baja**
- **Ubicación:** 
  - [app/analysis/market_microstructure.py:79-85](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/analysis/market_microstructure.py#L79-L85)
- **Escenario de fallo:**
  ```python
  history = ex.fetch_open_interest_history(symbol, '1h', limit=OI_HISTORY_HOURS + 1)
  values = [h.get('openInterestValue') for h in history if h.get('openInterestValue')]
  if values:
      data['open_interest_usd'] = round(float(values[-1]), 0)
      if len(values) >= 2 and values[0]:
          data['oi_change_24h_pct'] = round((values[-1] - values[0]) / values[0] * 100, 2)
  ```
  Si un par de futuros fue listado recientemente en Binance (ej. hace 6 horas), o si el endpoint devuelve menos de 25 barras por interrupción temporal, `values[0]` corresponde a hace 5 horas, pero el registro lo graba como `oi_change_24h_pct`.
- **Arreglo mínimo propuesto:**
  Validar el lapso temporal real:
  ```python
  if len(history) >= 2 and (history[-1]['timestamp'] - history[0]['timestamp']) >= 23 * 3600 * 1000:
      data['oi_change_24h_pct'] = round((values[-1] - values[0]) / values[0] * 100, 2)
  else:
      data['oi_change_24h_pct'] = None
  ```

---

### Lo que está BIEN implementado en el código (Sin Relleno)
- **Manejo de OHLCV:** [IndicatorUtils.convert_to_dataframe](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/analyzers/utils.py#L48-L56) construye el índice `datetime` explícitamente en UTC (`pandas.to_datetime(..., utc=True)`), sin usar transformaciones locales.
- **Firma de deduplicación:** [wyckoff_alerts.py:260](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/analysis/wyckoff_alerts.py#L260) usa `timestamp.isoformat()`, que al provenir del índice UTC genera strings canónicos con offset `+00:00` persistibles en SQLite y JSONL sin ambigüedad.
- **API Twitter/GetXAPI:** [twitter_sentiment.py:91-94, 138-150](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/analysis/twitter_sentiment.py#L91-L150) calcula `until_time` en segundos epoch UTC y parsea `%z`, manteniendo aware todas las fechas.
- **Colas y TTLs:** [manager.py](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/data/manager.py#L95) y [queue.py](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/notifications/queue.py#L110) usan `time.time()`, que es un timestamp Unix lineal e independiente de husos horarios.

---

## Propuesta de Texto Exacto para las Alertas de Telegram

Para resolver el Hallazgo 4 y adaptar el bot al operador en `America/Santiago` sin romper la referencia al gráfico de Binance:

```html
🟢 <b>ALCISTA — posible subida</b>
🕒 <b>Cierre vela:</b> 20:00 UTC (17:00 Santiago) | 4h | 24h: +1.2%
<b>BTC/USDT</b> | binance
Wyckoff Spring: rompio el soporte y volvio a entrar (trampa bajista)
Volumen en la ruptura: 3.4x el promedio
Barrida bajo el nivel: 1.8%
Pares con evento en esta misma vela: 6 (backtest con 5+ pares: media ~+2.5%)

📈 <b>Plan: long, mantener ~3 dias (72h), stop -10% en precio (mark)</b>
Tomando TODAS las señales a 1x (con comisiones y funding): acierto 56-58%, ganancia media +1.5% a +1.8% por trade.
⚠️ Si solo podes tener 3 posiciones abiertas a la vez rinde menos: ~+1% medio y 50-56% de acierto...

🕐 <b>Ejecucion</b> (medido en ~1.270 springs con velas de 1 minuto):
• Entrar en los primeros ~15 min da lo mismo que a la apertura; esperar 1-2 h cuesta ~0.3-0.4%.
• Orden limite o esperar confirmacion no mejora: te perdes los que despegan.
• No muevas el stop a break-even ni cortes por retrocesos chicos.

<i>Backtest Freqtrade 2022-2026. No es asesoria financiera.</i>
```

*(Si la alerta llega de madrugada en Santiago, ej. 05:07 local, el operador al despertar a las 08:30 lee inmediatamente `17:00 Santiago` o `05:00 Santiago` y reconoce al instante las 3.5 horas de demora transcurridas).*

---

# SÍNTESIS FINAL

### Los 3 Experimentos de Horario que yo Correría Primero
1. **Liquidación de Funding (00/08/16 UTC vs 04/12/20 UTC):** Probar si los springs en velas de funding sufren distorsión mecánica por carry trade. Muestra balanceada ($740$ vs $645$), hipótesis con dirección pre-fijada y costo analítico casi nulo.
2. **Interacción Hora UTC $\times$ Clúster de Mercado ($\ge 5$ Pares Simultáneos):** Medir si las capitulaciones masivas (el único edge fuerte de $+2.5\%$) se concentran en las aperturas de EEUU (16h UTC) o el cierre diario (00h UTC), descartando eventos aislados en horas ilíquidas.
3. **Fin de Semana "Puro" (Sábado 04:00 UTC a Domingo 16:00 UTC):** Depurar la muestra de 38 fines de semana eliminando las velas de frontera (viernes tarde y domingo noche con reapertura de CME) para verificar si el IC excluye el cero.

### Los 3 Bugs de Reloj Más Graves en el Código
1. **Riesgo de repintado y pérdida de velas en `drop_unclosed_candle` ([manager.py:61](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/data/manager.py#L61)):** Depender de `datetime.now(timezone.utc)` del host local en lugar del reloj del exchange expone al sistema a analizar velas sin cerrar por adelanto de reloj o a descartar velas recién cerradas por atraso (y cachearlas vacías por 5 minutos).
2. **Falta de sincronización al reloj de pared en el worker principal ([app.py:194](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/app.py#L194)):** Ejecutar `time.sleep(300)` después de un ciclo de duración variable provoca una deriva temporal acumulativa que retrasa las alertas hasta 7–8 minutos tras el cierre de la vela.
3. **Ausencia total de hora/fecha en los mensajes de alerta ([wyckoff_alerts.py:437](file:///C:/Users/Proyecto%20Z/Desktop/github/agy/crypto-signal/app/analysis/wyckoff_alerts.py#L437)):** El operador manual en Santiago no tiene información temporal en Telegram para saber si una alerta corresponde a la vela actual o a una vela cerrada hace horas mientras dormía.
