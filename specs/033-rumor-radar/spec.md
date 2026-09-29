# Spec 033: Radar volumen + rumor (en vivo, sin validar)

## Decisión del operador

Implementar y usar ya, sin backtest previo. Todo el radar queda marcado "NO validado" en
el propio mensaje y cada caso se registra para validarlo después con datos reales hacia
adelante (Principio III: se usa, pero no se confía en él como edge).

## Qué hace

1. **Velocidad de menciones** (`TwitterSentimentAnalyzer.mention_velocity`): GetXAPI
   devuelve una página fija de ~20 tweets, así que en vez de contar se mide cuánto tiempo
   abarcan → menciones/hora. Se compara con la misma medición de hace 7 días usando
   `until_time:<epoch>` (corte exacto verificado en vivo). También reporta la mayor
   cantidad de vistas (tweet viral ≥ 50.000).
2. **En la alerta Wyckoff**: la sección de Twitter ahora muestra la velocidad además del
   sentimiento. Si Gemini falla, se muestra igual la velocidad.
3. **Radar**: si una vela de 4h cierra con volumen ≥ 2.5x SIN evento Wyckoff y las
   menciones se aceleran ≥ `min_mention_ratio` (2.0), manda "🛰️ RADAR VOLUMEN + RUMOR"
   con la vela, la velocidad y la clasificación del contenido.
4. **Registro**: cada caso del radar (se haya avisado o no) y cada alerta Wyckoff van a
   `app/agent_state/rumor_radar.jsonl` (volumen persistente del contenedor).

## Costo

Solo se consulta en velas con volumen ≥ 2.5x: 2 consultas GetXAPI (US$0.002) y, si hay
aviso, 1 llamada a Gemini. Dedup por vela: el ciclo de 5 min no repite consultas.

## Configuración

`settings.wyckoff_alerts.rumor_radar.enabled` (default false, requiere
`twitter_sentiment.enabled` y `GETXAPI_API_KEY`) y `min_mention_ratio`.

## Riesgo conocido

Spam de cashtags (airdrops, memecoins) infla la velocidad en tickers grandes: en la
prueba en vivo SOL dio 2.2x por spam de airdrops. La clasificación de Gemini lo expone
en el resumen, pero no lo filtra. Revisar con el registro tras unas semanas.

## Validación pendiente

Con ~1-2 meses de `rumor_radar.jsonl`, cruzar cada caso con el retorno posterior del par
(24h/72h) en el laboratorio Freqtrade, y decidir si el radar se queda, se ajusta el
umbral o se apaga.
