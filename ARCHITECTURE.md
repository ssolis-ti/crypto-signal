# Mapa de Arquitectura

Generado con [Graphify](https://github.com/Graphify-Labs/graphify) (análisis AST local, sin LLM
para código) el 2026-09-28, en el commit `629b4071` (post-slice 009). El grafo completo
(`graph.json`, `graph.html` interactivo) se regenera localmente y vive en `graphify-out/` —
**gitignorado a propósito** por ser voluminoso y 100% regenerable; este documento es el resumen
curado que sí se versiona, para que la estructura del proyecto quede documentada sin depender de
volver a correr la herramienta.

Para regenerar el grafo completo:

```bash
graphify . --output graphify-out --code-only
graphify cluster-only graphify-out
```

## Resumen

- **955 nodos · 1576 edges · 63 comunidades** (46 con ≥3 nodos)
- 93% de las relaciones extraídas directamente del AST, 7% inferidas por patrón de uso
- 0 ciclos de importación detectados

## Módulos más conectados ("god nodes")

Estos son los puntos de mayor acoplamiento del proyecto — un cambio en cualquiera de ellos tiene
blast radius amplio, y son los primeros candidatos a tests exhaustivos (varios ya los tienen, ver
tabla de slices en el README):

| # | Nodo | Edges | Por qué es central |
|---|---|---|---|
| 1 | `IndicatorUtils` | 35 | Base de todos los indicadores/informantes (`convert_to_dataframe`) |
| 2 | `_make_notifier()` (test helper) | 21 | Fixture compartido por toda la suite de `tests/notifications/test_core.py` |
| 3 | `NotificationQueue` | 19 | Cola de prioridad (hoy no usada en el flujo vivo — reemplazada por `SmartNotificationManager`, ver abajo) |
| 4 | `RecordingClient` (test double) | 19 | Stub compartido para simular clientes Telegram/Webhook en tests |
| 5 | `SmartNotificationManager` | 19 | El gestor de notificaciones que sí está activo en producción |
| 6 | `SignalEnhancer` | 18 | Scoring 0-100 y clasificación A+/A/B/C — ver estado de validación en `specs/007-signal-enhancer-validation/` |
| 7 | `AgentStateStore` | 18 | Nuevo (slice 009): persistencia para la API de agentes |
| 8 | `Notifier` | 17 | Orquestador central de envío (Telegram/Webhook/Stdout) |
| 9 | `MarketContext` | 15 | BTC trend, sentiment, fuerza relativa ALT/BTC |

## Comunidades principales

Agrupamientos detectados por conectividad real del código (no por carpeta):

- **`plotters.py` / `StrategyExecutor`**: renderizado de gráficos y ejecución de indicadores —
  cohesión baja (0.06), múltiples responsabilidades sueltas; candidatos a refactor si se retoca esta
  zona.
- **`DataManager` / `CCXTDriver` / `PairResolver`**: la capa de datos, ya con buena cobertura de
  tests (slices 001, 003, 004).
- **`NotificationQueue` vs `SmartNotificationManager`**: son dos implementaciones de cola de
  notificaciones — `NotificationQueue` (slice 004) quedó testeada pero **no está wireada en el flujo
  real** (`notifications/core.py::notify_all` usa `SmartNotificationManager` directamente). Código
  vivo, no muerto, pero vale la pena saber cuál es la que realmente importa en producción.
- **`SignalEnhancer` / `MarketContext` / `AgentStateStore`**: el núcleo de "inteligencia" del bot —
  contexto de mercado, scoring, y ahora la capa de observabilidad para agentes.
- **`Configuration`**: carga y sanitiza `config.yml`/`.env`; punto único de verdad para qué está
  habilitado.

## Conexiones no obvias que el grafo reveló

- `validate_signal_enhancer.py` (script de investigación en `specs/007-.../`) importa directamente
  `SignalEnhancer` y `AltStrengthData` de `app/analysis/` — confirma que el backtest usó el código
  real de producción, no una reimplementación (tal como exige el Principio III de la constitución).
- `tests/api/test_server.py` y `tests/api/test_store.py` son ahora nodos bien conectados a
  `AgentStateStore` — cobertura simétrica del nuevo módulo.

## Preguntas que el grafo deja abiertas

- ¿Vale la pena eliminar `NotificationQueue` ya que `SmartNotificationManager` la reemplazó en el
  flujo real? (Hoy se mantiene porque tiene tests propios y podría reactivarse; no es código muerto
  en sentido estricto, pero tampoco se ejecuta en producción.)
- `plotters.py` y `StrategyExecutor` tienen la cohesión más baja del proyecto (0.06) — si se vuelve a
  tocar el renderizado de gráficos o el dispatcher de estrategias, es un buen candidato a dividir en
  módulos más chicos primero.
- Un solo nodo aislado: `common.sh` (script de Spec Kit, `.specify/scripts/`) — esperado, es
  tooling, no código de la aplicación.
