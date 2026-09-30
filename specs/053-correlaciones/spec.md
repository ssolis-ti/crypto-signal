# Spec 053: correlaciones entre pares como variable de estado del edge

Pregunta del operador: ¿se investigó el tema de correlaciones? ¿hay indicios? Se consultó a opencode y agy (`BRAINSTORM_*.md`) y se midió (`corr_regime.py`, criterio fijado antes).

## Qué ya se había cubierto (no como correlación entre pares)
Correlación ALT/BTC del score (007/011: sin valor predictivo), fuerza relativa vs BTC (049: ~0), BTC/ETH en días amplios (044: ~0%), lead-lag con BTC en 15 min (036: ruido), elasticidad intradía (050: invirtió signo OOS), retorno residual vs BTC en 1 h (052: igual que azar). Como **variable de estado** (régimen de correlación, dispersión, contagio, macro) no se había medido.

## Medición (1.022 velas con springs, 648 IS / 374 OOS; canasta por vela, 72 h, stop −10%)
Estado medido al cierre de la vela de confirmación con datos anteriores; terciles fijados en IS.
- **Correlación media entre pares (7 días):** IS alto−bajo −0.12 pp (IC −1.8 a +1.6); OOS −4.8 pp (IC −14.9 a +1.0). Sin efecto y el signo no se sostiene.
- **Dispersión entre pares (24 h):** IS +1.08 pp (IC −0.5 a +2.6); OOS −8.4 pp (IC −19.3 a −0.1). **Signo invertido entre períodos**: no aprueba.
- **Retorno del mercado 24 h:** +0.16 pp IS, +1.97 pp OOS, ambos con IC que incluye 0.
- La correlación media es algo mayor en las velas de pánico amplio (0.70–0.74 vs 0.65) pero es **coincidente** (es el mismo fenómeno: beta común), no un predictor añadido.
- Prueba de "contagio" (¿rho alto convierte un spring aislado en vela amplia?): mal definida, la amplitud se mide en la misma vela y por construcción es 0% en aislados. **No concluyente**; el clasificador que propone opencode (H2, predecir el día amplio 1-2 velas antes) sigue sin probarse.

## Veredicto
**No hay indicios de una ventaja incremental por correlaciones.** Mecanismo: el edge es ~80–85% rebote beta de las alts, y una correlación alta es ese mismo fenómeno (riesgo de "aprobar por identidad"). Potencia: ~49 días amplios (MDE ≈ 2.9 pp).
Ideas sin probar y baratas: R² de cada par contra la canasta como filtro de "caída idiosincrática vs beta pura" (opencode); clasificador de día amplio (H2); sincronía intra-vela de mínimos con 15 min (agy). Macro externo (SPX/DXY/VIX): descartado por mecanismo débil y potencia nula.
Recomendación de ambos agentes: no filtrar; como máximo registrar `rho_hat` y la dispersión en el jsonl para revisarlas con alertas reales.
