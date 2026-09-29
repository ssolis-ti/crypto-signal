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
