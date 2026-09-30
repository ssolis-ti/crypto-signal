# Cierre del proyecto crypto-signal (v2.0)

Resumen ejecutivo de qué se construyó, qué se probó, qué funcionó, qué no, y qué queda abierto. El detalle de cada prueba está en `specs/NNN-*/`.

## Qué es

Un bot **solo de alertas** para Binance USD-M, sobre velas de 4 h, con avisos a Telegram. El operador decide y opera a mano. Freqtrade (proyecto aparte) se usó solo como laboratorio de backtests; el bot no depende de él.

## Resultado principal

**Un único edge validado:** el **Spring de Wyckoff (long)** en monedas líquidas (≥ 20 M USD/24 h), en 4 h, con volumen de la vela de ruptura ≥ 2.5x, mantenido 72 h con stop −10 % y comisión 0.1 %. Funciona sobre todo en **días de capitulación amplia** (≥ 20 % de los pares vigilados con spring confirmado en la misma vela).

| Medida | Valor |
|---|---|
| Springs aislados / poco extendidos | ~+0.5 % a +1 %, gana 41–51 % |
| Días de pánico amplio (49 días, canasta de todos los springs, 72 h) | media +1.8 % a +2.2 %, mediana +0.6 %, 45 % de los días en pérdida, p10 −9.5 %, p90 +12 % |
| Con sesgo de supervivencia (incluye 177 perpetuos deslistados), fuera de muestra | de +1.64 % a +0.35 % |
| Composición | ~80–85 % rebote de las alts tras liquidaciones forzadas, ~15–20 % estructura |
| BTC y ETH en esos días | ~0 |
| Tamaño sugerido | ≤ ~30 % del capital repartido en la canasta (pérdida ~3 % en un mal día); ~10 % en casos poco extendidos |

Es un edge **modesto y de alta varianza**, no un sistema de ingresos estable.

## Qué se probó y NO funcionó

Con criterio fijado antes, in-sample 2022–24 / out-of-sample 2025–26, bootstrap por día y corrección por comparaciones múltiples:

- RSI, MACD, score 0–100, ma_crossover, sqzmom, otros timeframes (solo 4 h confirma), CMF/PVT/NVI, patrones de vela, taker flow.
- Twitter (conteos y contenido como filtro), funding, open interest, ratio long/short, libro de órdenes.
- Horarios, sesiones, continentes, fines de semana, cambio de mes.
- Estructura completa de Wyckoff (SC, ST, SOS, LPS, SOW, LPSY), entrada por retest, trailing, take profit, horizonte de 48 h, selección por par, índice continuo.
- **Todo el lado corto** (upthrust, clímax de compra, funding alto, amplitud de máximos): sin edge; los clústeres de upthrust amplios pierden.
- **Radar intradía de "rumores"** (spec 052): volumen z ≥ 3 + retorno propio z ≥ 2.5 con velas de 1 h, 48 pares 2022–26: rinde igual que entrar al azar (long y short).

## Qué quedó en producción

| Pieza | Estado |
|---|---|
| Aviso **OPORTUNIDAD DE COMPRA** (Spring, un mensaje por vela, lenguaje simple, 4 pasos con precios, tamaño en % del capital) | Validado |
| Aviso informativo bajista, "Movimiento raro" (radar + Twitter) | Informativos, sin ventaja comprobada |
| Radar RSI/MACD | Apagado en la configuración de cierre |
| Reloj del exchange, ciclo alineado al reloj de pared, springs perdidos (hasta 12 h), reintento de Telegram, deduplicación tras reinicio | Robustez |
| Registro de cada alerta con microestructura y auditoría de reloj (`rumor_radar.jsonl`) | Base para validar hacia adelante |
| API local de solo lectura (`127.0.0.1:8090`) | Opcional |

## Calidad

- 398 tests en verde al cierre. Dependencias fijadas (spec 008).
- Constitución de 7 principios (solo lectura, sin repintado, validar antes de confiar, secretos fuera del repo, UTC interno, tests obligatorios, dependencias fijadas).
- Rondas de auditoría con agentes externos (opencode/DeepSeek, agy/Gemini), siempre verificadas contra el código: varias afirmaciones de los agentes resultaron falsas y se descartaron. Última ronda QA: dos hallazgos reales (radar perdía avisos si Telegram fallaba; un error del radar podía costar un spring del mismo par), ambos corregidos.

## Límites conocidos

- Depende de que el PC esté encendido; no avisa que está apagado.
- Sin validación real hacia adelante todavía: hay muy pocas alertas reales maduras. Confirmar el efecto de los días de pánico amplio requiere ~25 episodios (~2 años); monitorear degradación por CUSUM, ~10 años.
- La calibración usa 49 pares del laboratorio; el bot vigila 50 por volumen, que cambian con el tiempo.
- El causante principal del efecto es la beta de las alts; un régimen distinto (sin liquidaciones forzadas, cambios de estructura del mercado) puede eliminarlo.
- Código heredado de indicadores individuales y renderizado de gráficos sin tests propios.

## Pendientes (opcionales)

1. Decidir tamaños en dinero: necesita el **capital real del operador** (nunca se asume).
2. Correr `validate_forward.py` cuando haya ≥ 50 alertas maduras.
3. Candidatos sin probar: desliste anunciado por Binance como catalizador (faltan fechas), Gemini como disyuntor de riesgo, perfil de volumen/reingreso al área de valor, velas por volumen, resumen matutino en hora de Santiago, taker buy ratio intradía (no está en el histórico).
4. Alerta de "bot apagado" desde un servicio externo, si se quiere vigilancia continua.

## Cómo se organiza el repositorio

| Ruta | Contenido |
|---|---|
| `app/` | Código del bot (`analysis/` Wyckoff y textos, `behaviour/` ciclo, `notifiers/` Telegram, `api/` API local) |
| `tests/` | pytest, espejo de `app/` |
| `specs/` | Spec Kit: una carpeta por feature/investigación (001–052) con spec, resultados y scripts |
| `docs/` | `DESPLIEGUE.md`, `OPERACION.md`, `GUIA_DE_AVISOS.md`, `config.md`, `ESTADO_Y_PENDIENTES.md`, este archivo |
| `config-clean.yml` | Plantilla de configuración (copiar a `config.yml`) |
| `.specify/memory/constitution.md` | Principios del proyecto |
