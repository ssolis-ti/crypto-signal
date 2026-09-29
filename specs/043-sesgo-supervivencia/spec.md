# Spec 043: sesgo de supervivencia (perpetuos deslistados)

Hueco detectado en spec 042 (checklist de skills externas): los 29-30 pares del laboratorio son monedas que siguen
listadas hoy, así que "comprar la caída" puede verse mejor de lo real. Se descargaron del archivo público de Binance
(`data.binance.vision`, velas 4h mensuales + diarias para no perder los últimos días antes del deslistado) los perpetuos
USDT-M que ya no cotizan: 340 símbolos inactivos, 163 excluidos por ser acciones/ETF/materias primas tokenizadas,
**177 perpetuos cripto** con datos suficientes (2022-01 a 2026-09; monedas como LUNA, FTT, SRM, ANC, KLAY, REEF, BSW...;
algunos son renombres de monedas vivas, p. ej. RNDR→RENDER, FTM→S, MATIC→POL, por lo que el conjunto no es 100% "fracasos").

Método: mismo spring que el laboratorio (lookback 20, confirmación 3, volumen de ruptura >= 2.5x), entrada a la apertura
siguiente, 72h, stop -10% sobre mínimos, 0.1% de comisión ida y vuelta, sin funding (simulador simple). **Calibración: sobre los
sobrevivientes da +1.58% / 56% de acierto contra +1.69% / 56% del laboratorio con funding** (equivalente). Si el deslistado
ocurre en medio de la operación se cierra a su último precio.

## Resultado (resultado_supervivencia.txt)

| Grupo | n | media | acierto | stop | 2022-24 | 2025-26 |
|---|---|---|---|---|---|---|
| Sobrevivientes (30) | 1610 | +1.58% | 56% | 13.8% | +1.54% | +1.64% |
| Deslistados (177) | 2894 | +0.82% | 48% | 28.3% | +1.78% | **-0.23%** (acierto 39%, stop 33.5%) |
| Ambos | 4504 | +1.09% | 51% | 23.1% | +1.69% | **+0.35%** |

- **El sesgo existe y se concentra en 2025-26**: en 2022-24 los deslistados rinden igual que los sobrevivientes (+1.78% vs +1.54%);
  en 2025-26 pasan a ~0 (acierto 39%, casi 1 de cada 3 operaciones toca el stop). Con el universo completo el resultado fuera de
  muestra baja de +1.64% a +0.35%.
- Diferencia deslistados - sobrevivientes: -0.76 pp, IC95 por día [-1.65, +0.23] (incluye 0; en 2025-26 con >= 3M USD/día:
  -1.47 pp, IC [-3.62, +0.94]). El efecto es grande en magnitud pero no alcanza significancia.
- **Por liquidez** (volumen en USD de las 24h previas): < 3M: -1.21% (n=412 deslistados); 3M-20M: +0.50% con 26% de stops (n=1290);
  20M-100M: +1.22% (n=875); >= 100M: +3.71% pero con acierto 44% y 37.5% de stops (n=317, pocas monedas que se desploman
  mucho y otras que rebotan fuerte: cola gorda en ambos lados). Los 30 sobrevivientes son casi todos >= 20M (1547 de 1610).
- Peores casos: siempre son el stop de -10%; solo 1 operación de 2894 se cerró por deslistado en medio de la posición.

## Conclusión y decisión
1. El edge validado **se debilita fuera de las grandes monedas y en 2025-26**: hoy la expectativa razonable para "cualquier
   perpetuo con >= 3M de volumen" es ~+0.7% por trade, no +1.6%. El backtest anterior sobreestima porque solo incluye
   sobrevivientes líquidos.
2. El bot ya limita su universo a los 30 pares de mayor volumen (30 pares con mínimo 3M USD/24h), que se parece más al
   grupo de sobrevivientes. Aun así, el mensaje ahora registra y muestra el volumen en USD de las 24h y avisa cuando es < 20M.
3. Sigue pendiente tomar decisiones de tamaño de posición con esta cifra más conservadora y validar con alertas reales.
