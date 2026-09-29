# Spec 037: microestructura en vivo + funding como filtro del Spring

## Parte A: registro en vivo (implementado)

`app/analysis/market_microstructure.py`. Al salir cada alerta de Binance se guarda en
`agent_state/rumor_radar.jsonl`, campo `micro`: funding, open interest (USD y cambio 24h),
ratio long/short (cuentas, 1h), spread y desequilibrio del libro (todo el libro pedido y +-1%).
Solo se registra: no filtra ni cambia el mensaje (Principio III). Libro y open interest no tienen
historia larga en Binance, asi que solo se pueden validar hacia adelante (>= 50 alertas reales).
Config: `wyckoff_alerts.microstructure.enabled`.

## Parte B: experimento de funding en el laboratorio (criterio fijado ANTES de correr)

Pregunta: ¿el funding en el momento del spring separa springs buenos de malos?
Mecanismo esperado: funding bajo/negativo = cortos apretados/pagando -> el rebote de un spring
tiene mas combustible (short squeeze) que con longs baratos y euforicos.

Datos: trades de `WyckoffLab_SpringH72_SL10` en modo senal (todos los eventos, 1x), IS 2022-24
(861) y OOS 2025-26 (525); funding real de Binance (cada 8h) del laboratorio. El funding usado
es el ultimo publicado a la hora de entrada o antes (sin mirar el futuro).

Hipotesis (3, direccion fijada de antemano: funding BAJO es mejor):
- H1: funding < 0 vs >= 0.
- H2: funding en el cuartil inferior de los ultimos 90 dias del propio par vs resto.
- H3: funding acumulado de las ultimas 24h (3 pagos) < 0 vs >= 0.

Criterio de aprobacion (todo junto): la diferencia de medias (filtrado - resto) es > 0 en IS y en
OOS, y el IC bootstrap por DIA (los eventos comparten vela) de la muestra unida excluye 0 con
nivel corregido por 3 comparaciones (IC 98.3%). Si no se cumple todo: NO se aplica; se registra
como dato. Si aprueba, tampoco pasa directo a filtro: se marca "hipotesis del backtest" y se
confirma con alertas reales.

## Resultado (resultado_funding.txt)

**Ninguna de las 3 hipotesis aprueba.** Datos: 859 springs IS + 525 OOS.
- H1 (funding < 0): IS +0.00 pp (identico: +1.71 vs +1.71), OOS +1.24 pp, unido +0.45 pp, IC98.3% [-1.39, +2.30].
- H2 (cuartil bajo 90d): IS +0.05, OOS +2.19, unido +0.89, IC [-1.25, +3.23].
- H3 (acumulado 24h < 0): IS -0.32, OOS +0.54, unido +0.01, IC [-1.89, +1.98].

Lectura: en 2022-24 el funding no separa nada; el "efecto" solo aparece en 2025-26 (mismo patron que
NVI en spec 027: mejora solo out-of-sample = ruido). Todos los IC incluyen 0. Se descarta como filtro;
el funding igual queda registrado en vivo (`micro.funding_rate_pct`) por si el patron de 2025-26 se repite.
