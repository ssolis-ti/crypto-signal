# Spec 045: open interest y ratio long/short históricos como contexto del spring

Origen: sesión de apoyo mutuo (spec 044). opencode verificó que `data.binance.vision` tiene métricas diarias por símbolo con
open interest y ratio long/short de cuentas cada 5 min desde ~2021, incluso de deslistados. Eso refuta que "OI y long/short solo se
pueden validar hacia adelante": hoy el bot los registra en cada alerta (`micro`, spec 037) y ahora se pueden probar hacia atrás.

## Protocolo (fijado ANTES de mirar los datos)
- Eventos: los springs confirmados del universo completo (49 pares del laboratorio + deslistados) con >= 20M USD/24h
  (`events_universo.csv`, 3,476 springs, spec 044), entrada a la apertura siguiente, 72 h, stop -10%, 0.1% comisión (simulador de spec 043).
- Variables, medidas con la última fila de métricas <= hora de entrada (sin mirar el futuro):
  - V1: cambio del open interest en USD en las 24 h previas a la entrada (%).
  - V2: `count_long_short_ratio` (proporción de cuentas long/short) a la hora de entrada.
- Cortes por terciles calculados SOLO con 2022-24 y congelados para 2025-26.
- Hipótesis (2), dirección fijada:
  - H1: springs con el cambio de OI en el tercil INFERIOR (limpieza de apalancamiento) rinden más que el resto (dif > 0).
  - H2: springs con el ratio long/short en el tercil INFERIOR (minoristas cortos, combustible de squeeze) rinden más que el resto (dif > 0).
- Placebo (no cuenta para aprobar): tercil SUPERIOR de cambio de OI; no debería rendir más que el resto.
- Familia de k=2: IC bootstrap por DÍA al 97.5% (percentiles 1.25 / 98.75).
- Aprueba SOLO si, en la dirección fijada: signo correcto en 2022-24 y en 2025-26; IC unido excluye 0; |dif unida| >= 0.5 pp;
  >= 30 días distintos por celda y período. Cobertura: se reporta el % de springs con métricas disponibles.
- Si aprueba: no filtra el bot; se muestra/registra como hipótesis hasta >= 50 alertas reales (el bot ya registra `micro`).

## Resultado (resultado_oi_ls.txt)
Cobertura: **100% de los 3,476 springs tienen open interest a 24 h y 99% ratio long/short** (las métricas históricas existen para todo el
universo, incluidos deslistados). Terciles congelados con 2022-24: OI 24h [-9.28%, -0.92%]; long/short [2.19, 3.08].

**Ninguna hipótesis aprueba.**
- H1 OI 24h en el tercil inferior (limpieza de apalancamiento): 2022-24 **+2.21 pp** (media +3.25%, acierto 63%, 140 días) pero 2025-26
  **-1.31 pp** (signo invertido); unido +1.29 pp, IC97.5% por día [-1.39, +3.94].
- H2 long/short en el tercil inferior (cortos): +0.45 pp en 2022-24 y +0.86 pp en 2025-26 (mismo signo, efecto chico); unido +0.40 pp, IC [-1.42, +2.39].
- Placebo (no cuenta para aprobar) OI 24h en el tercil SUPERIOR: -1.29 pp (2022-24) y -2.09 pp (2025-26); unido -1.57 pp, IC [-3.75, +0.55].
  Es consistente en los dos períodos y va en el sentido que se esperaría si "OI subiendo fuerte durante el spring = peor" (los
  que abren posiciones al caer siguen cayendo). **Observación exploratoria, no pre-registrada: no se actúa**; el bot ya registra
  `micro.oi_change_24h_pct` y se revisa con >= 50 alertas reales.

Conclusión: el mismo patrón que funding y horarios: un efecto grande en 2022-24 que no sobrevive fuera de muestra. El OI/long-short queda
como dato informativo registrado; ahora también se sabe que se pueden backtestear (archivos diarios de data.binance.vision).
