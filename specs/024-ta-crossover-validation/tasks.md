# Tasks: Validación de cruces TA no probados

## Phase 1: Implementation

- [X] T001 `validate_ta_crossovers.py`: reimplementar `ma_crossover` (EMA10/EMA50)
      y `sqzmom` (squeeze release + momentum) de forma vectorizada sobre toda la
      serie histórica, sin modificar `app/` (FR-001, FR-006).
- [X] T002 Calcular retorno direccional esperado en 24h/72h/7d/14d sin look-ahead
      (FR-002).
- [X] T003 Split cronológico 70/30 in-sample/out-of-sample por candidato (FR-003).
- [X] T004 Evaluar 4 candidatos (ma_crossover solo/+volumen, sqzmom solo/+volumen)
      con z-test de win rate, reportar veredicto por horizonte (FR-004, FR-005).

## Phase 2: Execution

- [X] T005 Ejecutar contra basket real (10 meses, 4h, mismos 15 pares que
      specs/017-021) dentro de `crypto-signal:dev`.
- [X] T006 Documentar resultados y veredicto en la sección Convergence.

## Phase 3: Convergence

Ejecutado 2026-09-29 contra basket real (14/15 pares con historia completa —
MATIC/USDT devolvió 0 velas en Binance, probablemente por el rename a
POL/USDT; se excluyó automáticamente sin afectar al resto). 10 meses, 4h,
1800 velas por par.

**Resultado: ningún candidato confirmó.** Los 4 fallaron la vara out-of-sample
(win_rate>=60%, p<0.05, n>=30) en los 4 horizontes:

1. **ma_crossover solo** (688 eventos): sin edge — el único horizonte
   significativo out-of-sample (14d, p=0.0438) fue *negativo* (43.0% win rate),
   igual patrón que macd_cross en spec 011.
2. **ma_crossover + volumen extremo**: muestra insuficiente out-of-sample
   (n=17 en todos los horizontes) — el cruce EMA10/EMA50 es demasiado frecuente
   como señal base, y exigir volumen extremo además la vuelve demasiado rara
   para un split 70/30 sobre 10 meses.
3. **sqzmom solo** (775 eventos): sin edge — significativo out-of-sample en 7d
   y 14d, pero *negativo* (39.9% y 38.2% win rate respectivamente). El
   indicador tiende a señalar en el sentido equivocado, no solo sin ventaja.
4. **sqzmom + volumen extremo**: números inestables entre tramos (in-sample 7d
   65.4% *sig* vs out-of-sample 7d 42.1%; in-sample 14d 59.3% vs out-of-sample
   14d 47.4% con retorno medio negativo) — firma clásica de sobreajuste, misma
   que el taker-flow de spec 021.

**Conclusión**: ninguno de los dos indicadores sin probar (`ma_crossover`,
`sqzmom`) aporta un edge direccional real como señal aislada o combinada con
volumen extremo. Se confirma el patrón de todo el arco 007-024: el único
mecanismo que sobrevivió holdout fue el volumen extremo en rupturas de rango
Wyckoff (spring/upthrust), no cruces de medias ni indicadores de volatilidad
por sí solos. No se conecta nada a producción (FR-006 cumplido).

**Outcome**: `converged` — hallazgo negativo documentado, ningún código de
producción modificado. De la lista de candidatos sin probar en el listado
previo (adx, stochrsi_cross, klinger_oscillator, bbp, aroon_oscillator,
candle_recognition, ichimoku, iiv, momentum, obv, mfi), ninguno tiene ya una
tesis a priori mejor que ma_crossover/sqzmom — dado que los dos candidatos más
prometedores fallaron limpiamente, no se recomienda continuar probando el
resto sin una hipótesis nueva y específica.
