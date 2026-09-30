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
| [038](specs/038-experimentos-lab-pendientes/) | Experimentos de laboratorio pendientes, criterio fijado antes y corrección por 6 comparaciones: **ninguno aprueba**. Trailing, TP y horizonte de 48h empeoran (72h + stop -10% se mantiene); los filtros de barrida ≥1%/1.5% y caída 24h ≤ -8% mejoran en ambos períodos pero sus IC incluyen 0 |
| [039](specs/039-springs-perdidos-y-eql/) | **Springs perdidos con el bot apagado**: el bot ahora revisa también las 3 velas anteriores (hasta 12 h) y avisa los que no salieron, marcados como retardados con el costo medido (~0.5 pp por cada 4 h). Más: mínimos iguales (EQL) como filtro, **no aprueba y va al revés** (springs sobre pisos muy tocados rinden menos) |
| [040](specs/040-validacion-hacia-adelante/) | Script para validar con alertas reales (resultado a 24h/72h y cortes por pares simultáneos, barrida, funding, libro, open interest, menciones); se niega a concluir con < 50 alertas maduras. Además (fix): si Telegram falla la alerta se reintenta en vez de darse por enviada, reintento por fragmento sin duplicar, `RetryAfter` repetido, y la API de agentes ya loguea sus errores de SQLite |
| [041](specs/041-horarios-y-continentes/) | Brainstorm de opencode y agy sobre horarios y continentes + auditoría del reloj. **Ningún corte horario aprueba** (funding, apertura Europa/EEUU, clúster×sesión, fin de semana puro, inicio/fin de mes: 3 invierten el signo IS↔OOS). Auditoría del reloj (fix): el aviso muestra el cierre en UTC y hora de Santiago; el reloj del exchange decide qué vela cerró; el ciclo se alinea al reloj de pared; los logs llevan hora UTC; **con 30 pares corrían 2 workers y partían el conteo de pares simultáneos** |
| [042](specs/042-robustez-checklist-externa/) | Checklist de robustez inspirada en skills externas de backtesting (revisadas del ecosistema de `vercel-labs/skills`, sin instalar nada): **cumple** año por año (5/5 positivos), estrés de fricción (+1.10% con +0.3 pp de costo y +2 pp de peor stop) y Monte Carlo del drawdown (17-21% de años negativos incluso con poco capital por posición). **Hueco abierto: sesgo de supervivencia** (solo hay monedas que siguen listadas) |
| [043](specs/043-sesgo-supervivencia/) | **Sesgo de supervivencia medido** con 177 perpetuos cripto deslistados (archivo público de Binance): el simulador simple reproduce el laboratorio (+1.58% vs +1.69%); los deslistados rinden igual en 2022-24 (+1.78%) pero **~0 en 2025-26** (-0.23%, acierto 39%); con el universo completo el resultado fuera de muestra baja de +1.64% a +0.35%. El edge vive en las monedas grandes; el bot avisa ahora cuando el volumen es < 20M USD/24h |
| [044](specs/044-amplitud-capitulacion/) | Sesión de apoyo mutuo con opencode y agy para salir del bloqueo (ronda 1 + 2 en `brainstorm/`). **Amplitud de mínimos con volumen: no aprueba (~0%)**: lo que sostiene el edge es que además rebotan. **Amplitud de springs confirmados: relación graduada** (>= 20% de los pares: +3.8% en 2022-24, +1.5% en 2025-26; poco extendido: ~+0.5% a +1%), no significativa fuera de muestra. El aviso ahora expresa la amplitud como fracción de los pares vigilados con esas cifras |
| [045](specs/045-oi-long-short-historico/) | **OI y ratio long/short históricos** (data.binance.vision, cobertura 100% de 3,476 springs; refuta que solo fueran validables hacia adelante): **no aprueban**. Limpieza de OI: +2.21 pp en 2022-24 pero -1.31 pp en 2025-26; long/short: +0.4 pp no significativo. Observación exploratoria: OI subiendo fuerte durante el spring rinde peor en ambos períodos (-1.6 pp, IC incluye 0) |
| [044b](specs/044-amplitud-capitulacion/) | Instrumento en días de capitulación amplia (47 episodios): **BTC y ETH solos rinden ~0% (+0.24% / +0.33%); la canasta de springs de las alts +2.23%** (IC95 [+0.11, +4.28], +2.41% en 2022-24 y +1.97% en 2025-26). El edge es rebote de las alts, no del mercado |
| [046](specs/046-entrada-secundaria/) | **Entrada secundaria (retest de Fase C) y salida por retest: no aprueban.** El 21% de los springs vuelve a su mínimo en 4-32 h con vela verde de volumen seco; esos son los perdedores (-3.68% vs +3.01% del resto), pero el retest llega cuando el daño ya está hecho (salir ahí: +0.01 pp). Se mantiene la entrada inmediata con stop -10% |
| [047](specs/047-wyckoff-estructura-completa/) | **Estructura completa de Wyckoff** (clímax de venta, test secundario, signo de fortaleza, backup/LPS, signo de debilidad, LPSY y spring tras caída previa), 226 símbolos con deslistados, criterio fijado antes: **ninguna aprueba** (SOS/LPS pierden en ambos períodos; SC invierte el signo; los cortos no tienen edge). Solo el Spring en días de capitulación amplia tiene ventaja medible |
| [048](specs/048-lado-corto-espejo/) | **El lado corto en espejo** (subida >= +15% en 24 h, clímax de compra, funding agregado alto, amplitud de máximos, clúster de upthrusts), 226 símbolos, criterio fijado antes: **ninguno aprueba**. Asimetría: los upthrusts casi nunca ocurren en grupo y, cuando sí (>= 20% de los pares), el short pierde -2.4% / -2.1%; las capitulaciones rebotan en V, los techos no |
| [049](specs/049-debate-wyckoff/) | **Debate sobre Wyckoff (libros, técnicas, sucesores, matemática y estadística; opencode desde la tradición china —庄家, 缠论, 筹码分布— y agy desde la formalización)**. Test discriminante: en días de capitulación amplia hasta las alts golpeadas sin spring rinden +0.8% (springs +1.9%): ~80-85% de la ventaja es rebote de beta, ~15-20% estructura. Predictores de estructura (esfuerzo-resultado, rango previo, fuerza relativa, momentum): **ninguno aprueba**; la fuerza relativa va al revés (las más golpeadas rebotan más) |
| [050](specs/050-marco-matematico/) | **Marco y matemática para mejorar el mejor edge** (debate opencode + agy, dos rondas, literatura arXiv verificada; una cita falsa detectada). Mediciones que corrigieron supuestos: sd entre días **7.4 pp** (no 4), ICC 0.62, **mediana del día +0.57% y 45% de días en rojo**, MDE real ~2.9 pp; un CUSUM tardaría ~100 episodios. Marco final: gate binario ≥20% + canasta equiponderada + 72 h/stop -10% + tope por pérdida (≤0.3x del capital para perder ~3% en un día malo) + gobierno pasivo. Muertos por potencia: índice continuo, selección por par, HMM, horizonte OU, ponderar por daño (β invierte signo). El aviso ahora da la distribución por día |
| [051](specs/051-avisos-claros/) | **Avisos de Telegram en lenguaje sencillo**: el aviso de compra ahora explica qué pasó, qué tan fuerte es y da 4 pasos con precios concretos (referencia, stop, día y hora de salida en UTC y Santiago), cuánto poner en % del capital y el riesgo real; las señales de una misma vela salen en UN mensaje ("pánico generalizado" con lista de monedas); el lado bajista dice "no hagas nada"; los avisos viejos de RSI/MACD dejan las estrellas y avisan que no predijeron el precio. Guía: `docs/GUIA_DE_AVISOS.md` |
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
