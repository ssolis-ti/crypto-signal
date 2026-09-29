# Spec 038: experimentos de laboratorio pendientes (spring 72h, stop -10%)

Criterios fijados ANTES de correr. Base de comparacion: `WyckoffLab_SpringH72_SL10` (modo senal: todos
los eventos, 1x, comisiones y funding reales, IS 2022-24 / OOS 2025-26, ya corrida: 861 / 525 trades).
Las estrategias (`wyckoff_lab_exp.py`, en ~/freq/user_data/strategies) reusan la logica de eventos
validada; la unica diferencia con la base es lo que se indica.

| id | variante | tipo |
|---|---|---|
| E1 | barrida >= 1.0% bajo el soporte | filtro |
| E2 | barrida >= 1.5% | filtro |
| E3 | caida 24h <= -8% antes de la confirmacion | filtro |
| E4 | trailing: se activa a +3.5%, sigue a 2.0% (stop -10% se mantiene) | salida |
| E5 | horizonte 48h + ROI 6% inmediato / 4% tras 24h / 0% tras 48h | salida |
| E6 | horizonte 48h simple (sin TP) | salida |

Medicion (por trade, neta): media, acierto, peor trade. Diferencia con bootstrap POR DIA (los eventos
comparten vela): filtros = media(filtrados) - media(excluidos); salidas = media(variante) - media(base)
sobre los mismos eventos (pareado por par+fecha de entrada).

Aprueba SOLO si cumple todo: (1) diferencia > 0 en IS y en OOS; (2) IC bootstrap por dia de la muestra
unida excluye 0, con nivel corregido por 6 comparaciones (IC 99.2%); (3) para salidas, el peor trade y la
caida no empeoran. Si no: no se cambia el plan del mensaje. Aunque apruebe, se marca "hipotesis del
backtest" y se confirma con alertas reales (>= 50) antes de tocar el bot.

Fuera de alcance: filtro BTC>EMA200 (ya medido sin efecto, spec 035); el borrador de agy lo aplicaba en
silencio como "siempre verdadero" (columna informativa mal nombrada), se descarta.

## Resultado (resultado_exp038.txt)

El control (E0) reproduce la base: 861 IS / 525 OOS trades, +1.69% de media. **Ninguna variante aprueba.**

| Variante | 2022-24 | 2025-26 | IC 99.2% por dia (unido) | Lectura |
|---|---|---|---|---|
| E1 barrida >= 1.0% | +1.53 pp | +2.50 pp | [-0.29, +3.92] | mejora en ambos periodos; el IC roza 0 |
| E2 barrida >= 1.5% | +1.49 pp | +1.61 pp | [-0.33, +3.45] | igual, algo mas debil |
| E3 caida 24h <= -8% | +1.66 pp | +1.36 pp | [-2.63, +5.50] | mejora en ambos, muy pocos eventos (139 / 118), IC ancho |
| E4 trailing | -1.55 pp | -1.42 pp | [-2.84, -0.27] | **empeora, significativo** (acierto 71% pero corta las ganancias) |
| E5 48h + ROI | -0.85 pp | -0.52 pp | [-1.92, +0.49] | empeora |
| E6 48h simple | -0.75 pp | -0.15 pp | [-1.46, +0.31] | empeora o empata: 72h sigue siendo mejor |

Conclusiones: (1) las salidas "protectoras" (trailing, TP, horizonte corto) recortan las ganancias y no
ayudan, coherente con spec 036; el plan de 72h + stop -10% sin tocar se mantiene. (2) Los tres filtros
son consistentes en signo en ambos periodos pero no superan la correccion por 6 comparaciones; siguen
siendo hipotesis. La profundidad de la barrida (E1) es la mas prometedora y ya se muestra y registra en
el bot: se decide con >= 50 alertas reales. Nota: en E4 hay mas trades (936) porque cerrar antes libera
el par para una entrada nueva; la comparacion se hizo pareada por par+fecha (860 comunes).
