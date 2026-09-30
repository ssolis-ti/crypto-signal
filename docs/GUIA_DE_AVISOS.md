# Guía rápida: qué te avisa el bot y qué hacer

El bot solo **avisa**; no opera. Tú decides. Hay un solo aviso con ventaja comprobada: **OPORTUNIDAD DE COMPRA**. Todo lo demás es información.

## Los avisos, de más a menos importante

### 🟢 OPORTUNIDAD DE COMPRA: MONEDA (o "pánico generalizado" / "varias monedas a la vez")
**Qué es:** una moneda líquida cayó por debajo de su mínimo de los últimos 3 días con mucho volumen y enseguida volvió a subir. Suele indicar que los vendedores se agotaron y puede haber un rebote de unos días.
**Qué tan fuerte es** lo dice el propio aviso, según cuántas monedas lo hicieron a la vez:
- **Pánico generalizado** (20% o más de las monedas vigiladas): es el caso con más ventaja histórica, pero no es seguro. En los 49 días así del historial, un día típico dio +0.6%, 4 a 5 de cada 10 días terminaron en pérdida y el rango normal fue de −9.5% a +12%.
- **Caso poco extendido** (menos del 20%): la ventaja es pequeña (~+0.5% a +1% de media, gana 4 a 5 de cada 10 veces). Si entras, con poco dinero.

**Qué hacer (paso a paso, viene escrito en el aviso):**
1. Compra (long) **ahora, a precio de mercado**. Esperar no mejora el resultado; cada 4 horas de retraso cuesta ~0.5%.
2. Pon el **stop loss en −10%** (el aviso trae el precio exacto). Obligatorio; no lo muevas ni lo quites.
3. Si no salta el stop, **cierra a las 72 horas** (el aviso trae el día y la hora en UTC y en hora de Santiago). No cierres antes por miedo a una bajada chica: cerrar antes empeoró los resultados.
4. No compres más si baja (no promedies a la baja). Sin apalancamiento alto: usa 1x.

**Cuánto poner** (el bot no conoce tu capital, por eso lo da como porcentaje):
- Caso poco extendido: hasta ~10% de tu capital (si toca el stop pierdes ~1% de tu capital).
- Pánico generalizado: reparte por igual entre 3 o más monedas de la lista y, en total, no más de ~30% de tu capital (en un mal día pierdes cerca de 3% de tu capital; con 20%, ~2%).

**Si el aviso llega tarde** (bloque "⏱️ Aviso tardío"): el bot estuvo apagado y la vela cerró hace horas. Si el precio ya subió bastante desde el precio de referencia, es mejor no entrar.
**Si la moneda dice "poco líquida"** (⚠️): mueve menos de 20 millones de USD al día; en el historial rindieron peor. Usa muy poco dinero o sáltala.

### 🔴 Aviso informativo (sin acción)
Una moneda subió sobre su máximo reciente con mucho volumen y volvió a caer. **No hay que hacer nada**: en las pruebas estos avisos no dieron ventaja para abrir ventas (cortos). Solo si tienes una compra abierta de esa moneda, vigila tu stop.

### 🛰️ Movimiento raro (solo para mirar)
Mucho volumen y más conversación en Twitter, pero sin el patrón de rebote. **No hay ventaja comprobada**: no entres solo por esto.

### 📋 Radar RSI/MACD (solo informativo)
Lista de monedas "muy vendidas" o "muy compradas" según RSI/MACD. En las pruebas **no predijeron el precio**: no entres solo por esto. La señal principal es la OPORTUNIDAD DE COMPRA.

## Palabras que aparecen
- **Stop loss:** orden que cierra tu operación sola si el precio cae 10% desde tu entrada. Limita cuánto puedes perder.
- **Precio de referencia:** el precio al cierre de la vela; sirve para calcular tu stop. Tu precio de entrada real será parecido.
- **Canasta:** comprar varias monedas de la lista a la vez, en partes iguales. En días de pánico el resultado viene del conjunto, no de una moneda.
- **Vela de 4 h:** el bot mira el mercado en bloques de 4 horas; el aviso llega ~7 minutos después de que cierra una vela.
- **Apalancamiento 1x:** operar solo con tu dinero, sin prestado.

Todo es probabilidad, no garantía. No es asesoría financiera.
