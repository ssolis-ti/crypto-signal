# Spec: Clasificador de sentimiento/narrativa de Twitter (corrección de specs 022/028)

## Contexto — dónde specs 022 y 028 se equivocaron

Ambos intentos anteriores midieron **`tweet_count`** (cuántos tweets hay) como
proxy de "rumor" o "atención". Los dos fallaron por el mismo motivo:
`advanced_search_tweets` devuelve una página fija de ~18-19 tweets sin
importar la ventana o la moneda — no es un conteo real, es un tope de API.

El operador corrigió el enfoque de fondo: la idea nunca fue contar tweets,
sino **leer el contenido** — cruzar el pico de volumen (ya detectado por
Wyckoff) con lo que la gente está diciendo en ese momento: ¿hay un rumor,
una noticia, una capitulación, una euforia? Ese contenido es la señal, no el
número de mensajes.

## Piloto cualitativo ya ejecutado (6 eventos, lectura manual)

Antes de diseñar el clasificador formal, se leyó el contenido real (no el
conteo) de 6 eventos Wyckoff de altcoins ya confirmados en producción,
usando el mismo query angosto (ticker + ventana del evento) que specs/028:

| Evento | Dirección | Resultado 14d | Contenido observado |
|---|---|---|---|
| DOGE 2026-07-06 | hot (spring) | Perdedor (-6.23%) | Sentimiento mayormente alcista/esperanzado (compra de ballena, "to the moon") — **sin capitulación real** |
| ATOM 2026-07-08 | hot (spring) | Perdedor (-5.10%) | Mixto/apático — noticia negativa de fondo (Cosmostation da de baja validadores) |
| LINK 2026-07-31 | hot (spring) | **Ganador (+9.98%)** | Retail derrotado/apático ("está en la basura", "sin acción hasta 2032") + divergencia sentiment explícita: "CROWD=Bearish, MP(algo)=Bullish" + compra contraria de ballena ($65k) + catalizador regulatorio real (voto CLARITY Act) |
| BNB 2026-08-08 | cold (upthrust) | Perdedor (-15.80%, siguió subiendo) | Euforia sostenida y viral ("BNB season", memecoins explotando, +290 likes en llamada alcista) — **sin agotamiento** |
| BCH 2026-09-11 | hot (spring) | **Ganador (+48.58%)** | Hilo de capitulación viral masivo (300K views: "vendido de $3786 a $229, no compres") + confirmación independiente de un bot de analítica social ("Galaxy Score 75, actividad social en alza") justo en la ventana |
| NEAR 2026-09-11 | cold (upthrust) | Dato dudoso (-100.8%, posible artefacto) | Narrativa muy alcista y coherente (buybacks +97% semana, $1B en volumen de Intents, respaldo de influencer de 448K followers) — descartado del análisis por el retorno anómalo |

**Patrón observado (n=5 válidos, puramente descriptivo, NO estadísticamente
probado)**: los dos eventos `hot` (spring) que ganaron mostraban sentimiento
de **agotamiento/capitulación genuino** (LINK, BCH); el que perdió mostraba
sentimiento todavía esperanzado, sin capitulación real (DOGE). El evento
`cold` (upthrust) que perdió mostraba **euforia sostenida sin señales de
agotamiento** (BNB) — coherente con la teoría Wyckoff (springs genuinos
ocurren en capitulación real; upthrusts fallan cuando el momentum alcista es
genuino, no agotado).

Esto es consistente con la intuición original del operador, y **muy
distinto** de lo que specs/022/028 intentaron medir (conteo bruto).

## Objetivo de este slice

Diseñar (no necesariamente automatizar por completo) un procedimiento
repetible para clasificar el contenido de Twitter alrededor de un evento
Wyckoff en categorías accionables, y decidir cómo escalarlo.

## Esquema de clasificación propuesto

Por evento, sobre la muestra de tweets de la ventana (ticker + horas
alrededor del evento):

1. **`sentiment_extreme`**: `capitulation` / `euphoria` / `mixed` / `none` —
   ¿el contenido dominante muestra agotamiento emocional extremo (rendirse,
   "está muerto", ventas de pánico) o euforia extrema (FOMO viral, "a la
   luna"), o ninguno de los dos (chatter normal)?
2. **`social_spike_confirmed`** (bool): ¿algún tweet de una herramienta de
   analítica (Galaxy Score, FOMO alerts, trending, sentiment bots) confirma
   de forma independiente que hay un pico de atención social en la ventana?
3. **`catalyst_present`** (bool): ¿hay una noticia/catalizador concreto
   (partnership, buyback, listing, voto regulatorio, hackeo, movimiento de
   ballena) que explique el volumen, más allá del sentimiento puro?
4. **`wyckoff_aligned`** (derivado): para eventos `hot`, `sentiment_extreme
   == capitulation`; para eventos `cold`, `sentiment_extreme == euphoria`
   pero SIN señales de agotamiento (la euforia sostenida invalida el
   upthrust, no lo confirma — asimetría importante detectada en el piloto).

## Decisión de arquitectura pendiente — cómo escalar

El piloto de 6 eventos se hizo con lectura manual (yo leyendo cada tanda de
tweets). Escalar a los 321 eventos históricos de producción, o a alertas en
vivo, tiene dos caminos con costos muy distintos:

- **Opción A — Clasificación manual/interactiva por lotes**: seguir como en
  este piloto, en sesiones de trabajo, sobre muestras acotadas (20-40
  eventos por vez). Sin cambios de arquitectura, sin dependencias nuevas,
  pero no es accionable en vivo (no puede clasificar una alerta en tiempo
  real sin un operador leyendo).
- **Opción B — Integrar una llamada a un LLM en el pipeline**: agregar una
  dependencia nueva (cliente de API de LLM) y una API key nueva al proyecto,
  para que `WyckoffAlerter` (specs/023) pueda, en el momento de la alerta,
  consultar Twitter y pedirle a un LLM que aplique el esquema de arriba
  automáticamente. Esto es un cambio de arquitectura real: nueva superficie
  de secretos (Principio IV de la constitución), nuevo costo variable por
  alerta, nueva dependencia externa con su propio riesgo de disponibilidad.

Este slice deja documentado el esquema y el hallazgo cualitativo, pero **no
implementa la Opción B sin decisión explícita del operador**, dado que
introduce manejo de secretos y costo variable — cambios que esta constitución
trata con más cuidado que un simple script de validación.

## Criterios de éxito

- SC-001: Esquema de clasificación documentado y aplicado consistentemente
  en el piloto de 6 eventos.
- SC-002: Hallazgo cualitativo honesto (n pequeño, no es prueba estadística)
  documentado con ejemplos concretos.
- SC-003: Decisión de arquitectura (Opción A vs B) explícitamente devuelta
  al operador, no asumida.
