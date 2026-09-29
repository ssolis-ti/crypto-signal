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
