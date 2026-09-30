# Spec 044: amplitud de capitulación del mercado (señal de régimen)

Origen: sesión de apoyo mutuo con opencode y agy (ronda 1, `specs/044-amplitud-capitulacion/brainstorm/`). Ambos pusieron
primero esta idea: el edge del spring es sobre todo capitulación de TODO el mercado (5+ pares en la misma vela ~+2.5%), así
que en vez de esperar que cada par dibuje un spring, medir la amplitud directamente sobre todos los pares.

## Definición (fijada ANTES de correr; umbrales no se ajustan mirando resultados)

- Universo point-in-time (evita el sesgo de supervivencia, spec 043): los 49 pares del laboratorio MÁS los 177 perpetuos
  deslistados descargados, y en cada vela solo entran los pares con >= 20M USD de volumen en las 24h previas (6 velas de 4h)
  y >= 25 velas de historia.
- Por par y vela de 4h cerrada t: "en capitulación" = low_t <= mínimo de los 20 lows previos Y volumen_t >= 2.0 x SMA20(volumen).
- Amplitud_t = pares en capitulación / pares elegibles. **Señal: Amplitud_t >= 25%** (y al menos 5 pares elegibles).
- Entrada a la apertura de t+1; mantener 72 h (18 velas); stop -10% sobre mínimos; 0.1% de comisión ida y vuelta.
- Retorno del evento = media (par a par, ya neto) de la canasta de los pares en capitulación en t. Comparaciones descriptivas:
  canasta de todos los pares elegibles, y solo BTC.
- Unidad de análisis: un episodio = grupo de velas señal consecutivas o dentro de 72 h (se cuenta la primera vela); se reportan
  también los días distintos. Bootstrap por DÍA.
- Control: la media incondicional de la misma canasta en cualquier vela (deriva del mercado), para medir exceso.
- Sensibilidad (solo descriptiva, para ver meseta y no pico): umbrales 15%, 20%, 30%, 35%.

## Criterio de aprobación (todo junto)
1. Media del evento >= +1.5% en 2022-24 Y en 2025-26.
2. Exceso sobre la media incondicional > 0 con IC95 bootstrap por día (unido) que excluye 0.
3. >= 35 días distintos con señal en total y >= 15 por período.
4. Acierto de la canasta del evento >= 55% en ambos períodos.
Si aprueba: NO filtra nada; pasa a alerta informativa de régimen y se valida hacia adelante (>= 50 alertas / episodios).
Si no aprueba: se descarta como señal independiente (queda el spring par a par).

## Resultado 1: amplitud de MÍNIMOS con volumen (la definición de arriba) — NO aprueba (`resultado_amplitud.txt`)
Universo point-in-time (49 pares + 177 deslistados, >= 20M USD/24h; mediana de 54 pares elegibles por vela). Con umbral 25% hubo 142
episodios en 142 días distintos: media +0.02% (2022-24 +0.41%, 2025-26 **-0.62%**), acierto 47%, exceso sobre la deriva incondicional
+0.40 pp con IC95 por día [-0.72, +1.59]. La sensibilidad (15% a 35%) da lo mismo: ~0 en todos los umbrales. **Lección: que muchos pares hagan
nuevos mínimos con volumen NO es la señal; lo que sostiene el edge es que además REBOTEN (la confirmación del spring).** Comprar
"cuchillos cayendo" sin confirmación no rinde.

## Resultado 2: amplitud de SPRINGS CONFIRMADOS (seguimiento exploratorio; `resultado_cluster_fraccion.txt`, `resultado_cluster_universo.txt`)
Variable: fracción de los pares elegibles con spring en la misma vela (mismo simulador de spec 043).
- Con los 49 pares del laboratorio (>= 20M USD/24h) por conteo absoluto: 1, 2-4 y 5-9 springs a la vez rinden ~0% (+0.07%, +0.08%,
  -0.21%); **10+ rinde +3.44% (63% de acierto, 48 días; 2022-24 +3.84%, 2025-26 +2.87%)**. 5+ vs <5: +2.23 pp, IC95 [+0.35, +4.13].
- Con el universo completo (incluye deslistados): 10+ rinde +2.71% (61%, 64 días; +3.15% / +1.69%); 5+ vs <5: +1.90 pp, IC [-0.51, +4.17].
- En fracción de pares: dosis-respuesta en 2022-24 (>=5%: +2.5%, >=20%: +3.8%, >=30%: +5.1%, >=40%: +6.1%, acierto 60% → 76%); en 2025-26 se
  atenúa (+0.9%, +1.5%, +1.95%, +1.1%). Tramos sin solapar: < 20% de los pares → 2022-24 +0.53% (51%), 2025-26 +1.01% (41%); >= 20% → 2022-24 **+3.80% (65%)**,
  2025-26 +1.48% (54%). Diferencia amplia - no amplia: 2022-24 +3.27 pp IC [+0.08, +6.31]; 2025-26 +0.47 pp IC [-4.40, +5.58] (no significativa).
- A nivel episodio (una observación por vela de señal) el efecto es débil: 2022-24 +1.40%, 2025-26 -0.39%: el retorno está dominado por
  pocos días con muchísimos springs, imposibles de tomar todos a mano.
- Protocolo (umbral elegido con 2022-24, probado en 2025-26): eligió el umbral más bajo (5%), con 2025-26 +0.91% y diferencia
  unida +1.46 pp IC [-1.09, +3.70]: no concluyente.

## Decisión
1. La amplitud de mínimos no es señal. La amplitud de springs confirmados sí muestra una relación graduada, pero fuera de muestra es
   modesta y no significativa: **el aviso deja de prometer "5+ pares: +2.5%"** y ahora dice: fracción de los pares vigilados con spring,
   "capitulación amplia" (>= 20%) con +3.8%/65% en 2022-24 y +1.5%/54% en 2025-26, y "poco extendido" (< 20%) con ~+0.5% a +1%, acierto 41-51%.
   El bot registra también `watched_pairs` para validarlo hacia adelante.
2. El plan del mensaje incluye la advertencia de supervivencia (spec 043).
3. Pendiente de la sesión de apoyo mutuo (ver 045): OI y ratio long/short históricos; entrada secundaria; funding agregado; Gemini como disyuntor de riesgo.

## Resultado 3: ¿qué instrumento en los días de capitulación amplia? (`instrumento.py`, exploratorio)
Idea de opencode (E2) y agy: en esos días operar BTC/ETH o una canasta en vez de cada par. 47 episodios no solapados de capitulación
amplia (>= 20% de los pares con spring; 27 en 2022-24 y 20 en 2025-26), mismas reglas (72 h, stop -10%, 0.1% comisión):

| Instrumento | 2022-24 | 2025-26 | unido |
|---|---|---|---|
| **Canasta de los springs de esa vela** | **+2.41%** (59%) | **+1.97%** (55%) | **+2.23%** (57%), IC95 por día [+0.11, +4.28] |
| BTC solo | +0.02% | +0.53% | +0.24% (62%, 15% stops); exceso vs cualquier vela +0.20 pp [-1.44, +1.78] |
| ETH solo | -0.05% | +0.83% | +0.33% (53%, 19% stops); exceso +0.39 pp [-1.70, +2.59] |
| BTC+ETH | -0.01% | +0.68% | +0.28% |

**BTC y ETH no aportan nada en esos días (media ~0, igual que una vela cualquiera): el edge es de REBOTE DE LAS ALTS, no de "el mercado
rebota".** Descarta "operar BTC/canasta grande cuando el mercado capitula". La canasta de springs de las alts sí rinde +2.23% con signo igual
en ambos períodos (27 y 20 episodios: cada período por separado tiene un IC que incluye 0 por el n chico; unido excluye 0).
Regla práctica: en un día de capitulación amplia conviene tomar VARIOS springs (no elegir uno ni irse a BTC): el resultado es de la canasta.

## Cierre de la sesión de apoyo mutuo (ronda 2 en `brainstorm/`)
- agy y opencode coincidieron en las críticas útiles: contar días/bloques independientes (no eventos), universo point-in-time con deslistados,
  umbrales congelados con 2022-24, y medir contribución INCREMENTAL sobre la amplitud. Ambos concluyen que el cuello de botella son los pocos días
  independientes de capitulación (decenas), no las señales.
- Probado en esta sesión (todo con criterio fijado antes o declarado exploratorio): amplitud de mínimos (no), amplitud de springs (graduada, modesta),
  OI/long-short históricos (no, spec 045), instrumento BTC/ETH (no), funding agregado y horarios (no, specs 037/041), sesgo de supervivencia (spec 043).
- Sin probar aún (candidatos ordenados): (1) entrada secundaria / retest tipo Fase C con stop ceñido; (2) desliste anunciado por Binance como catalizador
  (los 177 deslistados permiten backtestear, falta la fecha de anuncio); (3) Gemini como "disyuntor" ante hack/insolvencia/desliste inminente del token;
  (4) funding agregado como confirmación incremental de la amplitud; (5) resumen matutino en hora de Santiago.
