# 🚀 Crypto-Signal

Bot de análisis técnico para criptomonedas, con notificaciones a Telegram. Solo lectura: usa datos
públicos de mercado vía CCXT, no tiene claves de exchange y no puede operar ni mover fondos.

> **Estado**: en producción (ver [Estado actual](#-estado-actual-y-límites-conocidos)). Desarrollado
> desde 2026-09-28 con [GitHub Spec Kit](https://github.com/github/spec-kit) sobre una
> [constitución](.specify/memory/constitution.md) de 7 principios — ver [Desarrollo](#-desarrollo-spec-kit--slices).

---

## ✨ Características

- 📊 **+15 indicadores técnicos**: RSI, MACD, Bollinger, Ichimoku, Stoch RSI, ADX, y más
- 📈 **Gráficos automáticos**: velas, RSI, MACD e Ichimoku
- 📱 **Notificaciones inteligentes a Telegram**: resumen consolidado por ciclo + detalle/chart para
  las señales de mayor calidad
- 🧠 **Scoring contextual**: cada señal se clasifica (A+/A/B/C) según tendencia de BTC, fuerza
  relativa ALT/BTC, sentiment de mercado y estructura de precio
- 🤖 **API de integración para agentes** (nuevo): estado del bot, contexto de mercado y señales
  consultables por HTTP, pensada para que un agente/IA la use como fuente de verdad
- 🔄 **Multi-exchange** vía CCXT (hoy configurado para Binance)
- ⚙️ **Altamente configurable**: templates de Telegram, umbrales por indicador, pares dinámicos por
  volumen

---

## 🏗️ Arquitectura

```
app/
├── app.py              # Entry point: arranca workers de análisis + API de agentes
├── conf.py             # Carga config.yml + defaults.yml + secretos desde .env
├── behaviour/          # Orquesta un ciclo: datos → indicadores → contexto → notificar
├── data/                # DataManager (OHLCV+cache), PairResolver (qué pares analizar)
├── exchanges/           # CCXTDriver (solo lectura: fetch_ohlcv, fetch_tickers)
├── analyzers/           # Indicadores/informantes/crossovers (TA-Lib)
├── analysis/            # MarketContext (BTC trend/sentiment) + SignalEnhancer (scoring 0-100)
├── notifications/       # Notifier, cola de prioridad, smart notifications, builder de mensajes
├── notifiers/           # Clientes: Telegram, Webhook, Stdout
├── rendering/           # Generación de gráficos (matplotlib)
├── api/                 # API REST de agentes (SQLite + FastAPI) — specs/009-agent-api/
└── utils/               # CalibrationLogger (diagnóstico, opcional)

specs/                   # Spec Kit: una carpeta NNN-slug/ por feature (spec, plan, tests, decisiones)
.specify/memory/constitution.md   # Principios que gobiernan todo el desarrollo
tests/                    # pytest, espejo de la estructura de app/
```

Ver [`ARCHITECTURE.md`](ARCHITECTURE.md) para el mapa de dependencias real del código (generado con
[Graphify](https://github.com/Graphify-Labs/graphify)): módulos más conectados, comunidades, y qué
tan acoplado está cada uno.

---

## 🐳 Despliegue con Docker (recomendado)

```bash
# 1. Clonar y entrar al repo
git clone https://github.com/ssolis-ti/crypto-signal.git
cd crypto-signal
git checkout main

# 2. Configurar Telegram (token + chat_id van en .env, NUNCA en config.yml)
cp .env.example .env
#   Editar .env con tu TELEGRAM_TOKEN y TELEGRAM_CHAT_ID
#   (o usar el script Configurar_Telegram_CryptoSignal.bat si estás en Windows)

# 3. Copiar y ajustar la configuración
cp config-clean.yml config.yml
#   Editar config.yml: pares, indicadores, umbrales (ver docs/config.md)

# 4. Construir y arrancar
docker compose up -d --build
```

> ⚠️ `config.yml` va en la **raíz del proyecto** (junto a `docker-compose.yml`), montado en modo
> solo-lectura dentro del contenedor. Las credenciales de Telegram viven solo en `.env`
> (`app/conf.py::_apply_env_secrets` las inyecta en tiempo de ejecución, con prioridad sobre
> cualquier valor en `config.yml`) — ambos archivos están en `.gitignore`.

### Verificar que está funcionando

```bash
docker logs -f crypto-signal          # ver el ciclo de análisis en vivo
curl http://127.0.0.1:8090/health     # API de agentes viva
curl http://127.0.0.1:8090/status     # workers, pares, último ciclo
```

---

## 🤖 API de integración para agentes

Desde `specs/009-agent-api/`, el bot expone en `http://127.0.0.1:8090` (solo accesible desde el host
donde corre Docker, sin autenticación) todo lo que ya calcula cada ciclo pero antes solo existía como
log de texto:

| Endpoint | Qué devuelve |
|---|---|
| `GET /health` | Liveness check |
| `GET /status` | Pares cubiertos, ciclos completados, último error por worker |
| `GET /market-context?exchange=&history=N` | BTC trend, sentiment, gainers/losers — histórico |
| `GET /signals/recent?pair=&quality=&signal_type=` | Señales con su score/quality completo, más recientes primero |
| `GET /indicators?pair=&exchange=` | Último valor de cada indicador/informante, por par |
| `GET /config` | Configuración activa (indicadores, settings) — nunca incluye tokens/credenciales |
| `GET /docs` | Documentación interactiva (OpenAPI/Swagger), autodescriptiva |

El historial de señales y contexto de mercado persiste en SQLite (`app/agent_state/`, sobrevive
reinicios); los snapshots de indicadores reflejan solo el estado más reciente (no historial completo).

---

## ⚙️ Configuración

Ver [`docs/config.md`](docs/config.md) para el detalle completo de `config.yml`. Puntos clave:

- **Pares**: manual (`settings.market_pairs`) o dinámico por volumen
  (`settings.dynamic_pairs`, top-N en Binance).
- **Indicadores**: cada uno con `hot`/`cold`, `candle_period`, `period_count` propios.
- **Scoring** (`settings.correlation.scoring`): pesos de BTC trend, estructura (EMA99), RSI y
  sentiment — ver [limitaciones conocidas](#-estado-actual-y-límites-conocidos), el score **no
  está validado como filtro** hoy.
- **Notificadores**: Telegram (recomendado), Webhook, Stdout.

### Personalizar el mensaje de Telegram

```yaml
notifiers:
  telegram:
    optional:
      template: |
        {% if status == 'hot' %}🟢 COMPRAR{% else %}🔴 VENDER{% endif %}
        📊 {{market}} | {{indicator|upper}} | Quality: {{quality}} ({{score|round}})
        💵 {{prices}}
```

---

## 🧭 Desarrollo: Spec Kit + Slices

Todo cambio de código en este repo sigue [GitHub Spec Kit](https://github.com/github/spec-kit):
cada feature vive en `specs/NNN-slug/` con su `spec.md` (requisitos), `plan.md` (Constitution Check),
`research.md` (decisiones), `tasks.md` (implementación + Convergencia), y — si toca lógica —
tests en `tests/`. La [constitución](.specify/memory/constitution.md) fija 7 principios no
negociables (solo lectura, sin repintado, validar heurísticos, UTC interno, tests obligatorios,
dependencias pinneadas).

| Slice | Qué resolvió |
|---|---|
| [001](specs/001-no-repaint-signals/) | Repintado: el bot leía la vela en formación como señal |
| [002](specs/002-utc-internal-time/) | Hora naive/local → UTC en índice de indicadores y anti-spam |
| [003](specs/003-utc-start-date/) | Mismo bug en el `since` enviado al exchange |
| [004](specs/004-core-pipeline-test-coverage/) | Cobertura de tests: crossover, pares, cola, smart notifications |
| [005](specs/005-notifier-core-coverage/) | Cobertura de `Notifier` + bug real de webhook corregido |
| [006](specs/006-deferred-cleanup-findings/) | Logs de debug residuales + último bug UTC (charts/calibración) |
| [007](specs/007-signal-enhancer-validation/) | Backtest histórico real del score 0-100 — **sin valor predictivo medible** |
| [008](specs/008-pin-dependencies/) | Dependencias fijadas a versión exacta (antes todas `>=`) |
| [009](specs/009-agent-api/) | API REST de solo lectura para integración con agentes/IA |
| [010](specs/010-btc-change-1h-fix/) | `btc_change_1h` usaba el delta absoluto de CCXT, no un %; ahora se calcula desde OHLCV real |
| [011](specs/011-macd-cross-validation/) | Validación histórica del score aplicada a `macd_cross` (1,776 señales) — confirma y refuerza el hallazgo de 007 |
| [012](specs/012-wyckoff-fractal-research/) | Investigación (sin código): método Wyckoff + temporalidades fractales como hipótesis alternativa |
| [013](specs/013-wyckoff-effort-result/) | `WyckoffPrimitives`: ratio esfuerzo/resultado, flags de clímax/movimiento delgado — primitivas puras, sin conectar a alertas todavía |
| [014](specs/014-wyckoff-range-spring-upthrust/) | Detección de rango de trading, Spring y Upthrust — reglas de precio explícitas, aún sin conectar a alertas |
| [015](specs/015-wyckoff-historical-validation/) | Validación histórica de Spring/Upthrust (2,839 eventos): win-rate significativo (53-55%) en los 4 horizontes — primer efecto real de las 3 validaciones — pero **no replica** la magnitud de +20-30%/1-2 semanas recordada |
| [016](specs/016-wyckoff-multiframe-integration/) | Condicional: integración multi-timeframe — pendiente decisión del operador (resultado de 015 es real pero modesto) |
| [017](specs/017-wyckoff-edge-refinement/) | Búsqueda de edge con split in-sample/out-of-sample: **volumen extremo en la ruptura (≥2.5x) confirma** — 62.4% win-rate fuera de muestra (n=101, 14d) — pendiente decisión de conectarlo a Telegram |
| [018](specs/018-wyckoff-timing-and-drawdown/) | Timing y drawdown con velas de 1h: win-rate más alto (72-78%) en las primeras 1-2h con magnitud chica; sostener hasta 14d da más magnitud (+2.84% mediana) pero 26.5% de eventos ven drawdown ≥10% — pendiente decisión de cómo encuadrar la alerta |
| [019](specs/019-wyckoff-confluence-and-ta-confirmation/) | Confluencia 1D/4h + RSI/ADX como refinamiento: **ninguno de los tres sumó nada** (los tres empeoraron fuera de muestra) — el volumen extremo en la ruptura sigue siendo el único edge validado |
| [020](specs/020-orderflow-and-social-data-research/) | Investigación (verificada en vivo): Binance ya expone taker buy/sell volume gratis; getxapi sí tiene búsqueda histórica real en Twitter/X |
| [021](specs/021-wyckoff-taker-flow/) | Taker buy/sell flow como refinamiento: hipótesis de absorción pasa la barra mecánica pero con signo invertido in-sample/out-of-sample — **inconcluso**, no se suma como edge validado |
| [022](specs/022-twitter-attention-pilot/) | Piloto de atención en Twitter/X: `tweet_count` de getxapi resultó capeado (~19 siempre) — método descartado, frenado a tiempo tras 10/41 consultas |
| [023](specs/023-wyckoff-live-alerts/) | **En producción**: alerta Wyckoff Spring/Upthrust (volumen extremo ≥2.5x) a Telegram, con encuadre dual (rápida/sostenida) y números reales — independiente de `SignalEnhancer` |
| [024](specs/024-ta-crossover-validation/) | Validación de `ma_crossover` (golden/death cross) y `sqzmom` (squeeze momentum), solos y con filtro de volumen extremo: **ninguno confirmó** out-of-sample — se mantiene el volumen extremo en rupturas Wyckoff como único edge validado del proyecto |
| [025](specs/025-wyckoff-multi-timeframe-validation/) | Validación del mismo mecanismo (Spring/Upthrust + volumen extremo) en 1h/2h/8h/1d: **solo 4h confirma** — timeframes rápidos pierden poder predictivo, 1d tiene muestra insuficiente (10 meses) |
| [026](specs/026-broader-signal-catalog/) | Investigación (no implementación): catálogo de 150+ funciones TA-Lib sin probar, patrones de vela y filtros de volumen como candidatos; order book verificado factible en vivo pero **sin historial** en Binance — no validable con el mismo rigor sin recolección propia |
| [027](specs/027-wyckoff-volume-context-filters/) | CMF/PVT/NVI como filtro de contexto adicional sobre el edge ya validado: **ninguno mejora el baseline** — NVI pasó la vara mecánica pero falló el estándar real (empeora in-sample, "mejora" solo out-of-sample = ruido, mismo patrón que spec 021) |
| [028](specs/028-twitter-event-triggered-pilot/) | Corrección de spec 022 (Twitter por altcoin, no BTC genérico): **mismo tope de ~19 tweets persiste** sin importar cap de la moneda ni ancho de ventana — confirma que `advanced_search_tweets` no sirve para medir volumen de conversación, con cualquier acotamiento |
| [029](specs/029-wyckoff-candle-pattern-filter/) | Patrones de vela TA-Lib (60+ CDL*, y un subset "core" curado) como filtro adicional: **ninguno confirma** — un candidato pasó la vara mecánica a 14d pero el chequeo de consistencia in/out-of-sample (agregado tras la lección de spec 027) lo descartó como falso positivo automáticamente |
| [030](specs/030-twitter-sentiment-classifier/) | Corrección de specs 022/028 (leer **contenido**, no contar tweets): piloto cualitativo de 6 eventos muestra capitulación genuina en springs ganadores vs. euforia sostenida en upthrusts perdedores — patrón coherente con Wyckoff, **no validado estadísticamente** (n=5), esquema de clasificación diseñado, decisión de escalado (manual vs. LLM en vivo) pendiente del operador |
| [031](specs/031-wyckoff-twitter-sentiment/) | **En producción (opcional)**: `WyckoffAlerter` enriquece el mensaje con contenido de Twitter/X (GetXAPI) clasificado por Gemini, etiquetado como informativo/no validado — nunca decide si la alerta se envía; degrada segura sin credenciales; deshabilitado por defecto |
| [032](specs/032-freqtrade-lab-wyckoff/) | **Freqtrade como laboratorio** (futuros 2022-2026, comisiones y funding, sin lookahead): el encuadre "rápido 1-2h" era falso (44-49%), 14d no es robusto; lo que funciona es **spring long ~72h con stop −10%** (56-58%, +1,5-1,8%/trade, positivo en IS y OOS). Upthrust sin edge confiable. Mensaje de la alerta actualizado |
| [036](specs/036-minutos-criticos/) | **Minutos críticos tras la alerta** (brainstorm de opencode y agy + medición con 2.716 eventos en velas de 1 min): el retraso de ~7 min no cuesta, esperar 1-2 h sí; orden límite, esperar confirmación, invalidación temprana y **break-even** empeoran el resultado (con BE el acierto cae de ~58% a ~13%); taker flow, BTC 15 min y hora UTC son ruido. La alerta de spring ahora incluye guía de ejecución |
| [037](specs/037-microestructura-funding/) | Registro en vivo de funding, open interest, ratio long/short y libro de órdenes en cada alerta (solo se registra) + experimento de funding en el laboratorio con criterio fijado antes: **ninguna de 3 hipótesis aprueba** (IS sin efecto; solo mejora en 2025-26 = ruido) |
| [035](specs/035-auditoria-resultados/) | **Auditoría de resultados y de estrategia** (opencode/DeepSeek + agy/Gemini, verificadas por mí): el mensaje de alerta mezclaba tres formatos (corregido); el edge viene de capitulaciones de todo el mercado (springs aislados sin ventaja, 5+ pares a la vez +2.5%); filtros propuestos (barrida, caída 24h, régimen BTC) no superan un bootstrap por día -> se muestran y registran, no filtran |
| [033](specs/033-rumor-radar/) | **En producción, NO validado**: radar volumen + rumor — vela 4h con volumen ≥2.5x sin evento Wyckoff + velocidad de menciones en Twitter ≥2x vs hace 7 días → aviso. Cada caso se registra en `agent_state/rumor_radar.jsonl` para validarlo después |

---

## 📊 Estado actual y límites conocidos

- ✅ Pipeline de datos sin repintado, UTC consistente en todo punto crítico, 155 tests pasando.
- ✅ Corriendo en producción, ciclo real Binance → Telegram confirmado end-to-end.
- ✅ **Alerta Wyckoff en vivo** (slice 023): Spring/Upthrust con volumen extremo (≥2.5x) — el único
  edge de todo el proyecto que sobrevivió validación con holdout — envía un mensaje con encuadre dual
  (⚡ rápida 1-2h / 📈 sostenida 14d) y los números reales de la validación, completamente
  independiente del score de `SignalEnhancer`. Gateado por `settings.wyckoff_alerts.enabled` (default
  `false`, activado en el `config.yml` del operador).
- ⚠️ **El score de `SignalEnhancer` fue validado históricamente contra los dos indicadores
  habilitados en producción (RSI: 642 señales — slice 007; macd_cross: 1.776 señales — slice 011) y
  no mostró valor predictivo** — en macd_cross a 72h la correlación es incluso significativamente
  **negativa** (p=0.0055). Se decidió mantener el filtro de detalle/chart (`detail_min_quality: 'A'`)
  sin cambios hasta rediseñar y re-validar el heurístico — ver
  [`validation-report.md` (RSI)](specs/007-signal-enhancer-validation/validation-report.md) y
  [`validation-report.md` (macd_cross)](specs/011-macd-cross-validation/validation-report.md).
- ⚠️ Gran parte del código heredado (indicadores individuales, `build_indicator_messages`,
  `rendering/plotters.py`) no tiene tests propios todavía — solo lo tocado por los slices arriba.

---

## 🤝 Créditos

- Proyecto original: [CryptoSignal](https://github.com/CryptoSignal/Crypto-Signal)
- Fork mejorado: [w1ld3r/crypto-signal](https://github.com/w1ld3r/crypto-signal)
- Esta versión: [ssolis-ti/crypto-signal](https://github.com/ssolis-ti/crypto-signal)

## 📄 Licencia

MIT License — ver [LICENSE](LICENSE).
