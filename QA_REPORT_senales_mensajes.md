# QA Report — Lógica de señales y mensajes

Rama: `qa-opencode` (commits `e99cb94`, `e51f3ba`, `68f537e`).
Suite base antes de tocar nada: **195 passed** (toda verde). Suite final: **250 passed**.
Método: tests adversariales (sin red ni reloj real; `requests`/`ccxt`/tiempo mockeados),
estilo de `tests/analysis/test_wyckoff_alerts.py`.

---

## 1) Bugs REALES encontrados

### Bug 1 — Mensajes de Telegram > 4096: contenido descartado (ALERTA PERDIDA)

- **Archivo**: `app/notifiers/utils.py`, `NotifierUtils.chunk_message` (bloque original, líneas 25-39).
- **Entrada que lo dispara**: cualquier mensaje con `len(message) > max_message_size` (4096).
  - Línea única de 10000 caracteres sin `\n`: el `for` entra una sola vez, hace
    `chunked_message.append('')` y termina → devuelve `['']`. **Se pierde el mensaje completo**
    (y enviar `''` además dispara `BadRequest: message text is empty`).
  - Mensaje multilínea > 4096: el `chunk` acumulado al salir del `for` **nunca se hace flush**,
    así que se pierde la cola del mensaje (verificado: entrada 4889 chars → salida 4095 chars).
  - Línea larga mezclada con otras líneas: esa línea también se descarta.
- **Qué pasaba**: se descartaba el mensaje entero o su cola sin ningún error visible
  (`send_direct_text` solo loguea). La alerta Wyckoff/radar podía no llegar o llegar incompleta.
- **Qué debería pasar**: entregar todo el texto, en chunks no vacíos y de tamaño ≤ límite,
  sin partir etiquetas HTML en el caso normal (corte por líneas).
- **Fix**: flush del último chunk + hard-split de una línea individual mayor al límite
  (manteniendo los cortes por línea para el resto). Cambio mínimo en `app/notifiers/utils.py`.
- **Tests que lo cubren**: `tests/notifiers/test_telegram_client.py::TestChunkMessage`
  (7 tests: message corto, exactamente en el límite, multilínea sin pérdida, línea larga,
  sin chunks vacíos, líneas no cortadas, y una integración real por `notify()` que reensambla
  todos los chunks y compara contra el original).
- **Nota**: el código original permitía chunks de hasta `max-1`; el fix permite hasta `max`
  (Telegram acepta 4096 inclusive).

### Bug 2 — `format_section` revienta con tipos inesperados y tumba la alerta Wyckoff

- **Archivo**: `app/analysis/twitter_sentiment.py`, `format_section` (líneas originales 199-210).
- **Entrada que lo dispara** (salida no confiable de Gemini/terceros):
  - `sentiment_extreme` con un valor no-string, p. ej. `["capitulation"]`:
    `SENTIMENT_LABELS.get(list, ...)` → `TypeError: unhashable type: 'list'`.
  - `ratio` presente pero `current`/`baseline` `None` o no numéricos:
    `f"{current:.1f}"` → `TypeError: unsupported format string passed to NoneType`.
  - `max_views` no numérico (`"muchas"`): comparación `str >= int` → `TypeError`.
- **Qué pasaba**: `TwitterSentimentAnalyzer.analyze()` devuelve ese resultado; `_send_alert`
  construye la sección de Twitter **antes** de enviar y la excepción sube hasta el `try/except`
  de `WyckoffAlerter.check_and_alert`. Resultado: **la alerta Wyckoff validada no se envía**,
  aunque la sección de Twitter es informativa y por diseño (Principio III) nunca debe decidir
  si la alerta se manda.
- **Qué debería pasar**: degradar segura — mostrar solo lo numérico/conocido y nunca perder
  la alerta.
- **Fix**: guardas de tipo (`isinstance`) para `ratio`/`current`/`baseline`, `max_views` y
  `sentiment_extreme`. Cambio mínimo en `app/analysis/twitter_sentiment.py`.
- **Tests que lo cubren**: `tests/analysis/test_twitter_sentiment.py::TestFormatSectionAdversarial`
  (6 tests) y `TestAnalyzeMalformedResponses::test_gemini_wrong_typed_fields_do_not_break_formatting`.

**Verificación de regresión**: se revertiron temporalmente solo los dos archivos de `app/`
(`git stash`) y los 9 tests objetivo fallaron; con el fix, pasan.

---

## 2) Riesgos detectados y NO arreglados

1. **Alerta perdida si Telegram falla de forma persistente (no se reintenta en el ciclo siguiente).**
   `Notifier.send_direct_text` (`app/notifications/core.py:252-256`) traga la excepción por cliente,
   y `WyckoffAlerter._send_alert` (`app/analysis/wyckoff_alerts.py:288-301`) llama a `_remember`
   incondicionalmente. Si los 3 reintentos de tenacity fallan, la alerta se pierde y queda marcada
   como enviada. No lo arreglé porque exige cambiar el contrato de `send_direct_text` (devolver
   éxito/fallo) y la semántica de dedup, excede el cambio mínimo y puede introducir duplicados ante
   éxito parcial. Trade-off actual: preferir no duplicar sobre no perder.
2. **Ventana de duplicado entre envío y registro.** Si el proceso muere tras enviar y antes de
   escribir/recordar la firma, al reiniciar puede reenviar la misma vela. Requiere idempotencia
   (registrar antes de enviar o reconciliar), no un cambio mínimo.
3. **Alerta real perdida si la confirmación ocurrió con la PC apagada** (comportamiento
   documentado, no bug nuevo). `check_and_alert` solo mira `df.iloc[-1]` y
   `WyckoffPrimitives._detect_range_event` marca el evento en la **primera** vela de confirmación.
   Test: `TestDetectionDegenerateInputs::test_multi_candle_break_only_alerts_on_first_confirmation`.
   No lo cambie porque el edge se validó con esa definición (tocar la ventana = cambiar estrategia).
4. **`_stale_notice` con timestamp naive lanza `TypeError`** (recorrido de alerta perdida). La ruta
   de producción siempre entrega índice UTC-aware (`convert_to_dataframe(..., utc=True)`); no lo
   endurecí. Test de caracterización: `TestStaleNoticeBoundaries::test_naive_timestamp_raises_type_error`.
5. **Radar con `ratio is None`** (baseline insuficiente) se registra y deduplica sin alertar ni
   reintentar; un `dict` con `ratio=None` no se trata como fallo reintentable, a diferencia de
   `mention_velocity() is None`. Documentado sin cambios por ambigüedad de diseño.
   Test: `TestRadarEdges::test_ratio_none_records_and_dedups_without_alert`.
6. **Dos `RetryAfter` seguidos.** `_async_notify` hace un solo `sleep`+reintento; un segundo
   `RetryAfter` propaga y `send_direct_text` lo traga → alerta perdida. No tocado (semántica de
   reintentos de Telegram, borde con infraestructura).
7. **`SmartNotificationManager.build_summary_message`** (`app/notifications/smart.py:261-269`) solo
   clasifica `A+/A/B/C`; una calidad distinta caería fuera de `display_signals` sin contarse como
   truncada, aunque `total_count` la incluye (posible info engañosa). Hoy `SignalEnhancer` solo
   produce `A+/A/B/C`, por lo que no es alcanzable en producción; no lo modifiqué.

---

## 3) Áreas revisadas sin bugs nuevos (honesto)

- **Dedup por reinicio**: la carga de `agent_state/rumor_radar.jsonl` ya tolera archivo vacío,
  líneas corruptas, truncadas y con campos faltantes; y distingue firmas de radar y Wyckoff. Se
  agregaron tests de red de seguridad.
- **Velocidad de menciones**: `_mentions_per_hour` ya salta `createdAt` mal formados/ausentes y
  devuelve `None` con span 0. `_search`/`analyze` degradan a `None` ante respuestas que no son
  dict o sin `tweets`. Tests de red de seguridad.
- **Múltiples clientes Telegram**: `send_direct_text` ya aísla por cliente (uno que falla no
  impide el envío a los demás) y los fallos quedan contenidos. Tests de red de seguridad.
- **smart/builder con datos faltantes**: los defaults (`UNKNOWN`, `C`, `50.0`, `values` no-dict)
  funcionan; `build_indicator_messages` omite resultados de 0 filas y tolera pares sin `/`.
  Tests de red de seguridad.
- **Borde `>= 2.5x`**, `spring` vs `upthrust` en la misma vela (gana Spring), volumen 0/NaN,
  rango plano y `_change_24h` con pocas velas: comportamiento correcto/esperado; los tests
  documentan la precedencia y los degenerados.

---

## 4) Tests agregados y resultado final

**Tests agregados: 55** (de 195 a 250).

| Archivo | Tests nuevos |
|---|---|
| `tests/notifiers/test_telegram_client.py` (`TestChunkMessage`) | 7 |
| `tests/notifications/test_core.py` (`TestSendDirectText`) | 3 |
| `tests/analysis/test_twitter_sentiment.py` (3 clases) | 14 |
| `tests/analysis/test_wyckoff_alerts.py` (6 clases) | 24 |
| `tests/notifications/test_smart.py` (`TestMissingDataDefaults`) | 4 |
| `tests/notifications/test_builder.py` (`TestBuildIndicatorMessagesMissingData`) | 3 |

**Resultado final de la suite** (comando indicado, ruta del clon):
`250 passed, 5 warnings` — sin fallos ni tests omitidos. Los 5 warnings son preexistentes
(deprecaciones de `starlette`/`python-telegram-bot`).

Sin cambios de features, refactors, estrategia, umbrales (`2.5x`, `4h`, `LOOKBACK`), ni dependencias.
No se agregaron logs de debug permanentes.
