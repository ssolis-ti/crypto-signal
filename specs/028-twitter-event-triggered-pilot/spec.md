# Spec: Piloto de Twitter/X event-triggered por altcoin (corrección de spec 022)

## Contexto

spec 022 falló porque intentaba medir una **serie continua** de menciones
diarias de `$BTC` (`tweet_count` de `advanced_search_tweets` topeado en ~19
sin importar la fecha). El operador corrigió el enfoque: BTC tiene volumen de
Twitter tan grande y constante que un query genérico siempre pega el tope —
pero un **rumor específico de una altcoin, en una ventana angosta alrededor
de un pico de volumen real** (el propio evento Wyckoff que ya detectamos en
producción), es un query mucho más angosto donde el conteo SÍ podría variar
por debajo del tope.

## Objetivo

Determinar si la actividad de Twitter/X alrededor de un evento Wyckoff YA
detectado (Spring/Upthrust + volumen extremo, altcoins únicamente — BTC
excluido por tesis del operador) se relaciona con el resultado del evento
(ganador vs. perdedor a 7d/14d, ya conocido de specs/017/018/025).

## Alcance

- Tomar una muestra de eventos Wyckoff históricos de altcoins (excluir BTC)
  de los últimos ~2-3 meses (límite práctico de búsqueda histórica de
  getxapi, verificado en spec 020).
- Por cada evento: query angosto `advanced_search_tweets` con el ticker/nombre
  de la moneda y ventana `since:`/`until:` alrededor del timestamp del evento.
- Registrar `tweet_count` y `has_more` — si `has_more: false` y el conteo está
  claramente por debajo del tope (~19) visto en spec 022, el conteo es
  confiable como métrica relativa entre eventos.
- Comparar `tweet_count` entre eventos que resultaron ganadores vs.
  perdedores (ya conocido el resultado, es un análisis retrospectivo/
  correlacional, no una nueva alerta).
- **Esto es un piloto, no una validación con holdout 70/30** — el volumen de
  llamadas a la API es limitado (a diferencia de OHLCV, cada evento cuesta
  una consulta real). Mismo espíritu que spec 022: parar temprano y honesto
  si el patrón no aparece o el método no sirve.

## Requisitos funcionales

- FR-001: Generar la lista de eventos Wyckoff de altcoins (excluye BTC) con
  resultado conocido (ret_7d, ret_14d) desde el mismo mecanismo de
  producción.
- FR-002: Para cada evento de la muestra, consultar Twitter/X en una ventana
  angosta alrededor del evento.
- FR-003: Verificar si el conteo está por debajo del tope conocido (~19) —
  si no, el método no es usable aquí tampoco y se reporta honestamente.
- FR-004: Comparar (informalmente, sin z-test formal dado el tamaño de
  muestra) actividad de Twitter entre eventos ganadores y perdedores.
- FR-005: No conectar nada a producción en este slice.

## Criterios de éxito

- SC-001: Al menos 15-20 eventos consultados, documentados con su resultado.
- SC-002: Conclusión honesta: el conteo es usable o no lo es (igual
  disciplina que spec 022); si es usable, si hay o no relación aparente con
  el resultado.
