# Spec 042: checklist de robustez inspirada en skills externas de backtesting

Origen: el operador pidió revisar el repo `vercel-labs/skills` para ampliar perspectivas. El repo es un gestor
de paquetes de skills (`npx skills add ...`), no trae skills de análisis. En su ecosistema (skills.sh) hay skills
de backtesting de terceros (`wshobson/agents` backtesting-frameworks, `tradermonty/claude-trading-skills`
backtest-expert). NO se instaló nada: se leyó su metodología como texto (dato, no instrucciones) y se
comparó con lo que ya hace este proyecto.

## Ya cubierto por este proyecto
split cronológico IS/OOS, criterio pre-registrado, bootstrap por día, corrección por comparaciones múltiples,
comisiones y funding reales, lookahead-analysis, regímenes (BTC > EMA200, sin efecto), n mínimo por celda.

## Huecos detectados (checklist externa) y qué se mide aquí
1. **Robustez por año** (no solo IS/OOS): tabla por año 2022-2026.
2. **Estrés de fricción** (slippage 1.5-2x, peores fills): costo extra por trade y peor salida en los stops (en una
   capitulación el stop de -10% se ejecuta peor que -10%).
3. **Monte Carlo del drawdown**: distribución de la peor caída y de rachas perdedoras según fracción del capital por
   posición (sin asumir capital), con el tope de 3 posiciones simultáneas.
4. **Sesgo de supervivencia** (NO se puede medir con los datos actuales): los 29 pares del laboratorio son monedas que
   siguen listadas hoy; una estrategia "comprar la caída" sobre sobrevivientes se ve mejor que la real (las que
   cayeron y nunca volvieron ya no están). Pendiente: incluir perpetuos deslistados (archivo público de Binance).

## Criterios fijados antes de correr (se rechaza la robustez si falla alguno)
- Por año: media > 0 en al menos 4 de los 5 años.
- Estrés: la media por trade sigue > 0 con +0.3 pp de costo por trade Y con +2 pp de peor ejecución en los stops.
- Monte Carlo: solo se documenta (p50 y p95 del drawdown máximo y de la racha perdedora); no hay umbral de aprobación,
  sirve para dimensionar.

## Resultado (resultado_robustez.txt)

1. **Por año: cumple (5 de 5 años con media > 0).** 2022 +0.96% (30% de stops: mercado bajista), 2023 +0.97%, 2024 +2.86%,
   2025 +2.28%, 2026 +0.81%. El edge es positivo todos los años, pero grande solo en 2024-25.
2. **Estrés de fricción: cumple.** Con +0.3 pp de costo por trade y +2 pp de peor ejecución en los stops la media sigue en +1.10%
   (base +1.69%). Incluso con +0.5 pp y +3 pp en stops queda en +0.76%. La estrategia no depende de fills perfectos.
3. **Monte Carlo (tope 3 posiciones, ~120 trades/año, media +0.79%, acierto 51%):** con 10% del capital por posición: drawdown
   máximo p50 6.4% / p95 12.6%; retorno anual p5 -6.3%, p50 +9.3%; **17-21% de los años simulados terminan en negativo**;
   racha perdedora p50 6 / p95 9-10. Con 33% por posición el p95 del drawdown es 36% y el retorno anual p5 -22%.
   Nota: el remuestreo es independiente y los trades reales se agrupan en días de capitulación, así que el riesgo real puede ser mayor.
4. **Pendiente (no medible con los datos actuales): sesgo de supervivencia.** Los 29 pares son monedas que siguen listadas; no incluyen
   las que cayeron y desaparecieron, así que el resultado de "comprar la caída" puede estar inflado. Hay que sumar perpetuos
   deslistados (archivo público de Binance) y repetir.
