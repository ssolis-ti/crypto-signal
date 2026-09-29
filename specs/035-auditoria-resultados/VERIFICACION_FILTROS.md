# Verificación independiente de los filtros propuestos (AUDIT_MEJORAS.md)

La auditoría de estrategia (agy/Gemini) propuso filtros surgidos de cortar los trades del spring
por ~40 características. Se reprodujeron sus números exactos con datos del laboratorio
(`scripts/verify_filters.py`, imagen Freqtrade) y se midió cada diferencia con **bootstrap por día**
(los eventos se agrupan en velas compartidas por muchos pares: no son independientes).

| Filtro | Dif. medias 2022-24 [IC95 por día] | Dif. medias 2025-26 [IC95 por día] | Veredicto |
|---|---|---|---|
| Barrida >= 1% bajo el soporte | +2.0 pp [-0.04, +3.9] | +2.4 pp [-0.07, +4.7] | Consistente en ambos períodos y con teoría clara; en el borde de lo significativo |
| Barrida >= 1.5% | +1.75 [-0.10, +3.5] | +1.69 [-0.67, +4.1] | Igual, algo más débil |
| Caída 24h <= -8% | +2.2 [-1.6, +5.6] | +1.5 [-3.3, +6.3] | Débil; con <= -5% el signo se invierte en 2022-24 |
| BTC > EMA200 diaria | +0.3 [-3.2, +4.0] | +0.4 [-3.9, +4.9] | Sin efecto real por trade |

Springs por cantidad de pares con evento en la misma vela (verificado): aislado -0.22% / +0.88%;
5+ pares +2.71% / +2.29% (IS/OOS).

## Decisión

Ningún filtro se aplica como compuerta (Principio III: comparaciones múltiples, ICs que incluyen 0).
Se **muestran** en el mensaje (profundidad de la barrida y pares simultáneos, con la etiqueta
"hipótesis del backtest, sin confirmar en vivo") y se **registran** en `rumor_radar.jsonl`
(`sweep_depth_pct`, `concurrent_pairs`, `change_24h_pct`) para validarlos hacia adelante con
alertas reales. Regla para el futuro: pasar de "mostrar" a "filtrar" solo si se confirma con
>= 50 alertas reales o en un experimento de laboratorio pre-registrado.
