# Spec 040: validación hacia adelante con alertas reales

`validate_forward.py` lee `app/agent_state/rumor_radar.jsonl`, baja las velas 4h de Binance USD-M (público,
solo lectura) y calcula el resultado real de cada alerta con el plan del estudio: entrada a la apertura de
la vela siguiente a la confirmación, stop −10 % del cierre de la vela de señal, salida a 72 h (y retorno a
24 h), 0.1 % de comisión. Si la mecha cruza el stop, el retorno queda en el precio del stop y el hueco se
anota sin filtrar. El episodio amplio promedia solo springs líquidos; `watched_pairs` ausente no se
sustituye por 30. Spring = long, Upthrust = short (informativo). Compara con la referencia del backtest y
corta por lo que el bot registra: pares simultáneos, barrida, fin de semana, caída 24h, funding,
desequilibrio del libro, open interest, ratio de menciones (spec 037).

Regla (Principio III): con menos de 50 alertas maduras (>= 72 h) el script imprime "MUESTRA INSUFICIENTE"
y no hay que sacar conclusiones de los cortes. Solo describe; nunca modifica el bot.

Verificado con alertas sintéticas contra el cálculo manual de las velas reales (BTC long -1.93% a 24h y
-1.55% a 72h; ETH short +1.04% y -1.93%). Estado al 2026-09-29: 6 alertas reales (todas Upthrust), ninguna
madura todavía.

Uso:
```
docker run --rm -v "$PWD:/src" -w /src crypto-signal-crypto-signal python specs/040-validacion-hacia-adelante/validate_forward.py app/agent_state/rumor_radar.jsonl
```
