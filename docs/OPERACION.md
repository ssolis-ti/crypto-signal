# Operación diaria

Manual corto para quien usa el bot. Para qué significa cada aviso y qué hacer con él, ver [`GUIA_DE_AVISOS.md`](GUIA_DE_AVISOS.md). Para instalar o mover el bot, [`DESPLIEGUE.md`](DESPLIEGUE.md).

## Cómo funciona el ciclo

- El bot analiza los **50 pares USDT de Binance USD-M con más volumen de 24 h** (stablecoins y tokens de oro excluidos; la lista se recalcula sola).
- Corre **cada 5 minutos**, alineado al reloj de pared (unos 20 s después de cada :00, :05, :10…). Un ciclo dura ~1 minuto con 50 pares.
- La señal que vale se decide con **velas de 4 h cerradas** (cierran a las 00, 04, 08, 12, 16 y 20 UTC; en Santiago, con horario de verano, 21, 01, 05, 09, 13 y 17). El aviso principal llega ~1 minuto después del cierre. Los otros 47 ciclos de cada bloque ven la misma vela y no repiten el aviso.
- Solo usa datos públicos: no tiene claves de exchange, no opera.

## Qué te puede llegar

| Aviso | Acción |
|---|---|
| 🟢 **OPORTUNIDAD DE COMPRA** (una moneda, "varias monedas a la vez" o "pánico generalizado") | Es el único con ventaja medida. Trae los 4 pasos con precios (entrada, stop −10 %, salida a 72 h) y el tamaño sugerido en % del capital. |
| 🔴 **Aviso informativo (sin acción)** | No hacer nada. No hay ventaja para vender en corto. |
| 🛰️ **Movimiento raro** | Solo mirar el gráfico. No validado. |
| 📋 **Radar RSI/MACD** | Apagado por defecto en la configuración de cierre (no predijeron el precio). |

## Configuración que se toca

Todo en `config.yml` (raíz del proyecto), luego `docker compose restart crypto-signal`:

| Qué | Dónde |
|---|---|
| Cantidad de pares | `settings.dynamic_pairs.top_n` (50) |
| Zona horaria de los avisos | `settings.timezone` |
| Avisos Wyckoff | `settings.wyckoff_alerts.enabled` |
| Twitter en el aviso / radar de rumores | `wyckoff_alerts.twitter_sentiment.enabled`, `wyckoff_alerts.rumor_radar.enabled` (necesitan claves en `.env`) |
| Registro de funding/OI/libro por alerta | `wyckoff_alerts.microstructure.enabled` (solo registra) |
| Avisos RSI/MACD | `indicators.rsi[0].alert_enabled`, `indicators.macd_cross[0].alert_enabled` |

Referencia completa: [`config.md`](config.md).

## Revisiones útiles

```bash
docker logs --since 30m crypto-signal | grep -i "error\|traceback"     # errores
docker logs --since 10m crypto-signal | grep -i "sleeping"             # el ciclo late
docker logs crypto-signal | grep -i "Alert sent\|RADAR\|WYCKOFF"       # avisos enviados
curl http://127.0.0.1:8090/status                                      # estado por HTTP
```

Registro de eventos: `app/agent_state/rumor_radar.jsonl` (una línea JSON por evento; incluye `recorded_at`, `exchange_time` y `clock_skew_s`). Telegram solo recibe la compra spring. El HTML enviado queda en `app/agent_state/telegram_sent.jsonl`. El radar y el upthrust se registran y no entran al chat.

## Validación hacia adelante (cuando haya datos)

Con ≥ 50 alertas maduras (≥ 72 h) reales:
```bash
python specs/040-validacion-hacia-adelante/validate_forward.py
```
(Necesita pandas: se corre en un entorno con pandas o en la imagen de laboratorio). Se niega a concluir con menos de 50. La confirmación del efecto de los días de pánico amplio (≥ 20 % de los pares) necesita ~25 episodios, cerca de 2 años; el monitoreo de degradación (CUSUM) se estima en ~10 años. Detalle en `specs/040` y `specs/050`.

## Riesgos que hay que tener presentes

- **El bot depende de que el PC esté encendido.** No avisa que está apagado.
- **El edge es modesto y con mucha varianza**: en los días de pánico amplio la mediana fue +0.6 % en 72 h y 45 % de esos días terminaron en pérdida (rango típico −9.5 % a +12 %). Usa el stop −10 % siempre y respeta el tamaño sugerido.
- ~80–85 % del efecto es rebote de las alts tras liquidaciones forzadas; solo ~15–20 % es estructura del patrón.
- El sesgo de supervivencia baja el resultado fuera de muestra a ~+0.35 % al incluir monedas deslistadas: el edge vive en las monedas grandes.
- Nada de esto es asesoría financiera.

## Reglas de trabajo para quien modifique el código

- Todo cambio: spec en `specs/NNN-slug/`, tests, y `git commit` solo con la suite en verde.
- Las conclusiones se validan con el estándar del proyecto: in-sample 2022–24 / out-of-sample 2025–26, bootstrap por día, criterio fijado antes, corrección por comparaciones múltiples.
- Verificar lo que produzcan agentes externos antes de aplicarlo.
