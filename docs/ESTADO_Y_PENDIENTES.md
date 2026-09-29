# Estado de crypto-signal y pendientes (registro al 2026-09-29, actualizado al final del día)

Trabajo en tres fases: (1) Freqtrade (proyecto aparte, `~/freq`: bots en dry-run y laboratorio de backtests),
(2) crypto-signal (esta base de código, hecha), (3) fase de análisis (pendiente, la define el operador).
crypto-signal es un bot **solo de alertas** por Telegram; el operador opera a mano. Freqtrade se usó aquí
únicamente como laboratorio de backtests y no se tocaron sus bots.

## Estado

- `main` con 360 tests pasando, desplegado en Docker (`docker compose up -d --build`). Specs 001-041. Vigila 30 pares (`top_n: 30` en `config.yml`, gitignored).
- Vigila 20 pares USDT de Binance por volumen (stablecoins y tokens de oro excluidos). Los 36 slices están en `specs/`.
- **Único edge validado:** Spring de Wyckoff (long) en 4h con volumen de ruptura >= 2.5x, manteniendo ~72 h con stop -10%
  (acierto 56-58%, +1.5% a +1.8% por trade tomando todas las señales; con tope de 3 posiciones ~+1% y 50-56%).
  Upthrust (short): sin edge fiable, solo informativo.
- El edge viene sobre todo de capitulaciones de todo el mercado (springs aislados casi sin ventaja; 5+ pares en la misma vela ~+2.5%).
- Ningún dato no validado filtra alertas: se muestra y se registra (`app/agent_state/rumor_radar.jsonl`): profundidad de la
  barrida, pares simultáneos, caída 24h, cierre en fin de semana, menciones en Twitter.
- Guía de ejecución medida con velas de 1 minuto (spec 036): el retraso de ~7 min no cuesta; esperar 1-2 h cuesta ~0.3-0.4%;
  orden límite, esperar confirmación, cortar por retrocesos chicos y mover el stop a break-even empeoran el resultado.

## Hecho desde el primer registro (specs 037-040)

- **037** Registro en vivo de funding, open interest, long/short y libro en cada alerta (`micro` en el jsonl, solo se registra).
  Experimento de funding: ninguna de 3 hipótesis aprueba (IS sin efecto; solo mejora en 2025-26 = ruido).
- **038** Experimentos de laboratorio pendientes: ninguno aprueba. Trailing, TP y 48 h empeoran; barrida >= 1% / 1.5% y caída 24h
  mejoran en ambos períodos pero sus IC incluyen 0.
- **039** Springs perdidos con el bot apagado: ahora se revisan las 3 velas anteriores (hasta 12 h) y se avisan como retardados
  (costo medido ~0.5 pp por 4 h). Mínimos iguales (EQL): no aprueba y va al revés.
- **040** `validate_forward.py` para validar con alertas reales (se niega a concluir con < 50 maduras). Fix: alerta no entregada por
  Telegram se reintenta (hasta 12 ciclos), reintento por fragmento sin duplicar, `RetryAfter` repetido, la API de agentes loguea errores SQLite.

- **041** Horarios/continentes (brainstorm con opencode y agy): ningún corte horario aprueba. Auditoría del reloj: aviso con hora UTC + Santiago,
  reloj del exchange para decidir velas cerradas, ciclo alineado al reloj de pared, logs con hora UTC, un solo worker con Wyckoff activo.
  El 31% de los avisos llega entre 00:00 y 07:00 hora de Santiago.

## Pendiente

1. Esperar >= 50 alertas reales maduras (>= 72 h) y correr `specs/040-validacion-hacia-adelante/validate_forward.py`
   (hoy hay 6, todas Upthrust). Decidir ahí si la barrida >= 1% u otro dato pasa de "mostrar" a "filtrar".
2. **Sesgo de supervivencia (spec 042, hueco principal):** repetir el backtest incluyendo perpetuos deslistados de Binance; hoy los 29 pares
   son sobrevivientes y "comprar la caída" puede verse mejor de lo real.
3. Pedir al operador su capital y tamaño de posición reales (nunca se asumen).
4. Ideas sin probar: mean-reversion informativa tras caída >= 15% en 24h (funciona señal a señal, no con pocas posiciones); "sesión propia del par"
   (clasificar pares por su horario dominante a priori); calendario macro; decidir si mostrar un resumen matutino en hora de Santiago.

## Reglas de trabajo que resultaron necesarias

- Mensajes de commit: solo `improvements` o `fix`. No commitear si la suite tiene fallos.
- Verificar lo que producen los agentes externos (opencode/agy) antes de aplicarlo.
- Juzgar filtros con bootstrap por día y el estándar "mejora en 2022-24 Y en 2025-26".
- TA-Lib: un solo NaN deja el SMA en NaN para siempre; no convertir volúmenes en cero a NaN antes de promediar.
