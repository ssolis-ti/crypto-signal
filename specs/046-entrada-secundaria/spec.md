# Spec 046: entrada secundaria (retest de Fase C) con stop ceñido

Origen: sesión de apoyo mutuo (spec 044). agy propuso esperar el "test de falta de oferta" después del spring: el precio vuelve a
tocar el mínimo con volumen seco y se entra ahí con un stop más corto (menos riesgo por operación). Es la única idea pendiente
evaluable con datos propios (el desliste anunciado necesita fechas de anuncio que no tenemos).

## Protocolo (fijado ANTES de correr; umbrales de agy, sin ajustar)
- Eventos: springs confirmados del universo completo (49 pares del laboratorio + deslistados, >= 20M USD/24h), simulador de spec 043.
- Retest: entre 1 y 8 velas de 4h DESPUÉS de la vela de confirmación busca la primera vela r con: low_r <= mínimo de la vela de ruptura x 1.015,
  volumen_r <= 0.85 x SMA20(volumen) y cierre > apertura. Entrada secundaria = apertura de r+1; stop -5%; 72 h desde esa entrada; 0.1% de comisión.
- Comparación PAREADA sobre los mismos springs que tuvieron retest: entrada original (apertura de t+1, stop -10%, 72 h) vs entrada secundaria.
  También cuántos springs tienen retest (los que no lo tienen se pierden: costo de oportunidad).
- Aprueba SOLO si: (1) media de la entrada secundaria >= +1.5% en 2022-24 y en 2025-26; (2) diferencia pareada (secundaria - original) > 0 en ambos
  períodos con IC95 por día unido que excluye 0; (3) tasa de stop <= 28%; (4) >= 30 días distintos por período.
- Si no aprueba: la entrada original (inmediata, stop -10%) se mantiene; se anota como descartada.

## Resultado del protocolo original (resultado_retest.txt) — NO aprueba
727 de 3,476 springs (21%) tienen retest a las 1-8 velas (espera media 4.9 velas). La entrada secundaria con stop -5% rinde -0.06% (43% de acierto, **45% de stops**)
frente a -3.68% de la entrada original de esos mismos springs: mejora +3.62 pp pareada (IC95 [+2.78, +4.38], en ambos períodos), pero queda en ~0 y con muchos stops
(falla los criterios 1 y 3). **Hallazgo:** los springs SIN retest promedian **+3.01% (61% de acierto)** (n=2,749) y los que sí lo tienen **-3.68%** (n=727): el retest
con vela verde de volumen seco NO es una oportunidad, es la marca de un spring que está fallando.

## Seguimiento pre-registrado (hipótesis nueva, declarada ANTES de calcularla): salir en el retest
El retest ocurre después de la entrada (usa solo información hasta la vela r, sin mirar el futuro), así que no sirve como filtro de entrada pero sí como regla de SALIDA
o de invalidación: "si tras el spring aparece un retest (mismo criterio), cerrar en el cierre de la vela r".
- Comparación: retorno neto de la operación con la regla (cierra al cierre de r, con el stop -10% vigente hasta r) vs mantener 72 h, sobre TODOS los springs
  (los que no tienen retest no cambian).
- Aprueba SOLO si: mejora la media general >= +0.5 pp en 2022-24 y en 2025-26, IC95 por día unido excluye 0, y no reduce el acierto general.
- Si no aprueba: el retest queda como dato informativo (registrado), sin regla de salida.

## Resultado del seguimiento (resultado_retest_exit.txt) — NO aprueba
Salir en el cierre de la vela de retest mejora la media general **+0.01 pp** (IC95 por día [-0.13, +0.15]; 2022-24 +0.04, 2025-26 -0.05) y baja el acierto (54% → 52%).
En los 727 springs con retest: mantener 72 h da -3.68% y salir en el retest -3.62%. **Cuando aparece el retest esas operaciones ya perdieron casi todo
lo que iban a perder**: el retest es una consecuencia de un spring fallido, no una alerta temprana. Coincide con spec 036 (la invalidación temprana no ayuda).

## Conclusión
La entrada original (inmediata, stop -10%, 72 h) se mantiene. Tanto la entrada secundaria como la salida por retest quedan descartadas. Dato que sí queda:
los springs que vuelven a su mínimo en las siguientes 4-32 h con una vela verde de volumen seco (21%) son los perdedores del conjunto, pero no hay forma
de aprovecharlo a tiempo. Se cierra la lista de candidatos de la sesión de apoyo mutuo (spec 044) que se podían probar con datos propios.
