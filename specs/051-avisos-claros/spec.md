# Spec 051: avisos de Telegram en lenguaje sencillo, con pasos claros

Pedido del operador: "arregla los avisos del bot a Telegram, lenguaje sencillo e interpretable, consejos e indicaciones claras: por ahora no se entienden bien los mensajes".

## Problemas encontrados
1. **El aviso principal** (el único con ventaja comprobada) usaba jerga (Spring, Upthrust, "trampa bajista", "barrida", "backtest") mezclada con muchas advertencias y cifras de distintos formatos, y no decía paso a paso qué hacer ni con qué precios.
2. **En días de pánico llegaban muchos avisos largos casi idénticos** (uno por moneda), difíciles de leer y de accionar.
3. **Los avisos viejos de RSI/MACD** decían "COMPRA ⭐⭐⭐ señal muy fuerte (85/100)" y mostraban una tabla técnica ([INFO]/[CONTEXT]/[THRESHOLDS]), aunque el puntaje no predice nada (specs 007 y 011). Confundían y sugerían una fuerza inexistente.

## Cambios
- Nuevo módulo `app/analysis/alert_text.py` (funciones puras, con tests): construye los textos.
  - **OPORTUNIDAD DE COMPRA** (una moneda): qué pasó en palabras simples, qué tan fuerte es (según cuántas monedas hicieron lo mismo), **4 pasos numerados con precios concretos** (referencia, stop de −10% en precio, día y hora de salida a las 72 h en UTC y en hora de Santiago), cuánto poner (en % del capital, sin asumir capital), y "ten presente" con el riesgo real (4 a 5 de cada 10 pierden).
  - **Un solo mensaje por vela**: si varias monedas hacen lo mismo a la vez ("pánico generalizado" si son >= 20%), sale UN mensaje con la lista de monedas (precio de referencia → stop), los pasos y el tamaño total (<= ~30% del capital repartido). El registro y la deduplicación siguen siendo por moneda.
  - **Aviso informativo (sin acción)** para el lado bajista: dice claramente "no hagas nada" porque no tiene ventaja comprobada.
  - **Movimiento raro (solo para mirar)** para el radar de volumen + Twitter.
  - **Aviso tardío** con lenguaje claro y qué hacer si el precio ya se movió; **moneda poco líquida** con advertencia.
- **RSI/MACD**: el resumen ya no usa estrellas ni letras de calidad; lo presenta como "Radar RSI/MACD (solo informativo)", agrupado en alcistas/bajistas, con el RSI descrito en palabras ("muy bajo"/"muy alto"), y dice que estos indicadores no predijeron el precio y remite a la señal principal. La plantilla del mensaje de detalle se reemplazó por una versión corta y honesta (configs `config-clean.yml`, `config.yml`, `app/defaults.yml`, `app/config.yml.example`); las etiquetas de los indicadores se simplificaron.
- **Twitter**: encabezado "Qué se dice en Twitter (solo referencia, no está comprobado que sirva)".
- Guía para el operador: `docs/GUIA_DE_AVISOS.md` (qué es cada aviso, qué hacer, glosario).

## Cifras que muestran los mensajes (todas medidas en el proyecto)
Pánico generalizado (49 días, canasta con todos los springs, 72 h, stop −10%): mediana +0.6%, media +1.8%, 45% de los días en pérdida, rango −9.5% a +12% (spec 050). Poco extendido: ~+0.5% a +1% y gana 41-51% (spec 044). Tamaño: con stop de −10%, poner 10% del capital arriesga ~1%; ~30% repartido en la canasta arriesga ~3% en un día malo (spec 050, Kelly empírico y tope por pérdida). Con 3x de apalancamiento la caída máxima llegó a 46% (spec 042).

## Pruebas
395 tests (antes 372): textos (sin jerga, pasos, precios, horas, tamaños, tardío, liquidez, agrupado, truncado de listas), envío agrupado (un mensaje, un registro por moneda, reintento del grupo completo, no repite), resumen RSI/MACD, y las plantillas renderizan con Jinja en las tres configuraciones.
