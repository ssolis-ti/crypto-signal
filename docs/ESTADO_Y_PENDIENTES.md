# Estado de crypto-signal y pendientes (registro al 2026-09-29)

Trabajo en tres fases: (1) Freqtrade (proyecto aparte, `~/freq`: bots en dry-run y laboratorio de backtests),
(2) crypto-signal (esta base de código, hecha), (3) fase de análisis (pendiente, la define el operador).
crypto-signal es un bot **solo de alertas** por Telegram; el operador opera a mano. Freqtrade se usó aquí
únicamente como laboratorio de backtests y no se tocaron sus bots.

## Estado

- Commit `b7394da` en `main`, 316 tests pasando, desplegado en Docker (`docker compose up -d --build`).
- Vigila 20 pares USDT de Binance por volumen (stablecoins y tokens de oro excluidos). Los 36 slices están en `specs/`.
- **Único edge validado:** Spring de Wyckoff (long) en 4h con volumen de ruptura >= 2.5x, manteniendo ~72 h con stop -10%
  (acierto 56-58%, +1.5% a +1.8% por trade tomando todas las señales; con tope de 3 posiciones ~+1% y 50-56%).
  Upthrust (short): sin edge fiable, solo informativo.
- El edge viene sobre todo de capitulaciones de todo el mercado (springs aislados casi sin ventaja; 5+ pares en la misma vela ~+2.5%).
- Ningún dato no validado filtra alertas: se muestra y se registra (`app/agent_state/rumor_radar.jsonl`): profundidad de la
  barrida, pares simultáneos, caída 24h, cierre en fin de semana, menciones en Twitter.
- Guía de ejecución medida con velas de 1 minuto (spec 036): el retraso de ~7 min no cuesta; esperar 1-2 h cuesta ~0.3-0.4%;
  orden límite, esperar confirmación, cortar por retrocesos chicos y mover el stop a break-even empeoran el resultado.

## Pendiente

1. Validar hacia adelante con >= 50 alertas reales los campos registrados y el radar de menciones.
2. Robustez: detectar springs confirmados con la PC apagada (hoy solo se lee la última vela); reintentar si Telegram falla
   varias veces seguidas o llega un segundo `RetryAfter`; la base de la API de agentes ignora errores de escritura en silencio.
3. Experimentos de laboratorio sin correr (`specs/035-auditoria-resultados/scripts_estrategia/experimentos_lab.py`):
   barrida profunda (con criterio fijado antes), take-profit a 48 h, trailing, y combinación spring + caída fuerte de 24 h.
4. Pedir al operador su capital y tamaño de posición reales (nunca se asumen).

## Reglas de trabajo que resultaron necesarias

- Mensajes de commit: solo `improvements` o `fix`. No commitear si la suite tiene fallos.
- Verificar lo que producen los agentes externos (opencode/agy) antes de aplicarlo.
- Juzgar filtros con bootstrap por día y el estándar "mejora en 2022-24 Y en 2025-26".
- TA-Lib: un solo NaN deja el SMA en NaN para siempre; no convertir volúmenes en cero a NaN antes de promediar.
