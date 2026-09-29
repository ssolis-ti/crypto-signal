# Spec 032: Freqtrade como laboratorio del edge Wyckoff

## Por qué

La validación original (specs/017-018) usó 10 meses de datos spot y solo midió la
dirección del precio a horizontes fijos: sin comisiones, funding, stops, liquidación
ni tamaño de posición. El laboratorio Freqtrade del operador (`~/freq`, servicio `lab`)
tiene futuros de Binance desde 2021 y simula el trade completo. Además, los 10 meses
originales caen dentro del OOS del lab, así que **2022-2024 es fuera de muestra real
para todo el hallazgo**.

## Cómo

- `wyckoff_lab.py`: réplica exacta de `WyckoffPrimitives.detect_springs/upthrusts` +
  filtro de volumen de ruptura ≥ 2.5x (lookback 20, confirmación 3). Entrada a la
  apertura de la vela siguiente a la confirmación (cuando llega la alerta).
- 30 pares de futuros (los 29 de `config_backtest.json` + BTC), 4h con detalle 1h.
- Corte del lab: IS 2022-01-01 → 2025-01-01, OOS 2025-01-01 → 2026-09-22.
- Modo señal: stake 100, sin límite de posiciones (se toma cada evento).
- Modo real: 100 USDT, 3 posiciones de 30 USDT (config del operador).
- `lookahead-analysis` sobre `WyckoffLab_SpringH72`: **sin sesgo** (40 señales, 0 contaminadas).

## Resultados (comisiones y funding incluidos)

### Ronda 1: horizonte, ambas direcciones, 1x sin stop

| Horizonte | Win% IS / OOS | Media por trade IS / OOS |
|---|---|---|
| 1h | 44,2 / 46,5 | −0,10 / −0,06 |
| 2h | 45,6 / 49,0 | −0,05 / +0,10 |
| 24h | 57,2 / 54,0 | +0,21 / +0,71 |
| 72h | 56,4 / 59,4 | +0,51 / +1,24 |
| 7d | 54,8 / 53,2 | +0,48 / +0,66 |
| 14d | 51,0 / 50,5 | −0,90 / +0,71 |

Por dirección a 72h: spring +1,38% / +1,82%; upthrust −0,19% / +0,63%.
Upthrust gana seguido (57-61%) pero pierde en promedio en 2022-24 (squeezes):
depende del régimen, no es edge.

### Ronda 2: solo springs, 72h

| Variante | Trades IS / OOS | Win% IS / OOS | Media IS / OOS |
|---|---|---|---|
| 1x sin stop (señal) | 827 / 509 | 56,2 / 58,0 | +1,52 / +1,76 |
| 1x stop −10% (señal) | 861 / 525 | 55,1 / 57,0 | +1,69 / +1,69 |
| 1x stop −10%, 100 USDT | 353 / 210 | 49,6 / 56,2 | 100 → 192 / 100 → 163, DD 27% / 19% |
| 3x stop −10% precio, 100 USDT | 354 / 210 | 49,7 / 56,2 | 100 → 382 / 100 → 296, DD 46% / 32% |

A 3x, cada año de 2022, 2023 y 2024 terminó positivo.

## Conclusiones aplicadas a crypto-signal

1. **"⚡ Rápida 1-2h, 72-78%" era falso**: 44-49% y negativo con comisiones sobre
   ~3.400 trades. Eliminado del mensaje.
2. **"Sostenida 14d, 64%" no es robusto**: 14d pierde en 2022-24. Reemplazado por
   el plan validado: **long, mantener ~72h, stop −10%**.
3. **Upthrust**: se sigue avisando, pero marcado "sin edge confiable, no operar short
   solo por esta señal".

## Limitaciones

- El DD a 3x (46%) es alto para 100 USDT; 1x o 2x es más prudente.
- 30 pares fijos del lab ≠ 20 pares dinámicos de crypto-signal (mismo mecanismo).
- Stake fijo, sin interés compuesto.
