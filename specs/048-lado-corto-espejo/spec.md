# Spec 048: el lado corto en espejo (todo lo probado en long, ahora en short)

Observación del operador: "lo pruebas todo en long, falta short también". Cierto: el Upthrust (short) se validó en las specs 017/018/023/032 (sin edge fiable) y
SOW/LPSY en la 047 (sin edge), pero casi todo lo posterior (amplitud, clúster, OI, funding, retest, horarios) se midió sobre springs. Falta el espejo simétrico.

## Universo y simulación (igual que 043/044/047; criterios fijados ANTES de correr)
Velas 4h; 49 pares del laboratorio + 177 deslistados (point-in-time); solo pares con >= 20M USD/24h en la vela de señal. Short: entrada a la apertura siguiente,
mantener 72 h, stop +10% sobre máximos, 0.1% de comisión ida y vuelta. IS 2022-24 / OOS 2025-26. Control: media incondicional del short en cualquier vela elegible.

| id | espejo de | señal (short) |
|---|---|---|
| S1 | clúster de springs | Upthrust confirmado (máximo por encima del máx20 con rel_vol >= 2.5 y cierre de vuelta debajo del nivel en <= 3 velas) en una vela donde >= 20% de los pares elegibles tienen upthrust; se compara contra las velas con < 20% (dosis-respuesta como en spec 044) |
| S2 | reversión tras -15% en 24 h | subida >= +15% en las últimas 6 velas (24 h) al cierre de la vela; un evento por símbolo cada 72 h |
| S3 | clímax de venta (SC) | clímax de compra (BC): high >= máx20, rel_vol >= 3.0, rango >= 1.5 x ATR14, cierre en la mitad inferior de la vela |
| S4 | funding agregado negativo | mediana del funding (último publicado) de los pares del laboratorio en el decil SUPERIOR de 2022-24 (umbral congelado con IS); canasta corta de todos los pares elegibles, un episodio por bloque de 72 h |
| S5 | amplitud de mínimos | amplitud de MÁXIMOS: fracción de pares elegibles con high >= máx20 y rel_vol >= 2.0 en la misma vela >= 25%; canasta corta de esos pares, un episodio por bloque de 72 h |

Familia de k=5 comparaciones: IC bootstrap por DÍA al 99% (percentiles 0.5 / 99.5).

## Criterio de aprobación
- S2-S5 (señales): media neta del short >= +1.0% en 2022-24 Y en 2025-26; exceso sobre la media incondicional del short > 0 con IC unido que excluye 0; >= 30 días distintos por período (S4 y S5, que son episodios de canasta: >= 20 por período).
- S1 (filtro de clúster): diferencia (>= 20% de los pares - < 20%) > 0 en ambos períodos, IC unido excluye 0, >= 0.5 pp; además la media del short en los clústeres amplios debe ser >= +1.0% en ambos períodos.
Si aprueba: no cambia el bot; alerta informativa y validación hacia adelante. Si no: descartado.

## Resultado (resultado_short_mirror.txt): ninguna aprueba
Media incondicional del short (cualquier vela elegible): +0.07%. Universo de 226 símbolos, >= 20M USD/24h.

| Señal (short) | n | días | 2022-24 | 2025-26 | exceso (IC99% por día) |
|---|---|---|---|---|---|
| S2 subida >= +15% en 24 h | 3,289 | 1,080 | -0.45% (47%) | +1.14% (48%) | +0.06 [-0.82, +0.86] |
| S3 clímax de compra (BC) | 2,833 | 1,150 | -0.30% (48%) | +0.74% (48%) | -0.01 [-0.69, +0.55] |
| S4 funding agregado en el decil alto | 77 | 77 | -1.16% (35%) | -0.45% (43%) | -0.82 [-2.43, +0.70] |
| S5 amplitud de máximos >= 25% | 82 | 82 | -1.35% (36%) | -0.39% (43%) | -0.92 [-2.48, +0.51] |
| S1 clúster de upthrusts (>= 20% de los pares) | 349 | 17 | **-2.43%** (40%) | **-2.10%** (43%) | amplio - no amplio: -2.56 pp [-5.95, +0.79] |

- **No hay un espejo corto del spring.** Reversión tras subidas fuertes, clímax de compra, funding alto y amplitud de máximos rinden ~0% o pierden; los cortos en
  mercados que ya subieron mucho pierden más que la media incondicional.
- **Asimetría de fondo:** los upthrusts confirmados son mucho menos frecuentes en grupo (mediana 4% de los pares, p90 11%; solo 10 días con >= 20% en 2022-24 y 7 en 2025-26)
  que los springs, y cuando ocurren en clúster amplio el short PIERDE (-2.4% / -2.1%): tras un blow-off amplio el precio tiende a seguir subiendo, mientras que tras una
  capitulación amplia rebota. Las capitulaciones se resuelven en V; los techos no. Ojo: solo 17 días con clúster amplio, es una observación, no una regla.
- El funding agregado tiene su umbral del decil superior en 0.0100% por pago, que es el funding base de Binance (muchos empates): la prueba no discrimina bien, aunque tampoco
  se acerca a aprobar.
- Conclusión: en cripto 4h con estas definiciones el lado corto no tiene edge propio; el único aprobado sigue siendo el spring (long) en capitulación amplia.
