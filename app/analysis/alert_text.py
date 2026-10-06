"""
Textos de las alertas de Telegram (lenguaje sencillo, pasos claros, cifras honestas).

Son funciones puras: reciben datos ya calculados y devuelven HTML para Telegram. La logica de deteccion
vive en wyckoff_alerts.py; aqui solo se decide COMO se lo explica el bot al operador.

Cifras que aparecen en los mensajes (todas medidas en el proyecto, ver specs/043, 044, 049, 050):
- Dia de capitulacion amplia (>= 20% de los pares con spring en la misma vela), 49 dias, canasta con todas las
  senales, 72 h, stop -10%: mediana +0.6%, media +1.8%, 45% de los dias en perdida, rango tipico -9.5% a +12%.
- Spring poco extendido (< 20% de los pares): ~+0.5% a +1% de media y gana 41-51% de las veces.
- Stop -10%: perder 1% del capital en una operacion = poner 10% del capital; en un dia malo de canasta (decil
  inferior, -9.5%) perder ~3% del capital = poner ~30% del capital repartido entre las monedas.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd
import pytz

WEEKDAYS_ES = ('lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom')
CANDLE_HOURS = 4
HOLD_HOURS = 72
STOP_PCT = 10
WIDE_FRACTION = 0.20
LOW_LIQUIDITY_USD = 20_000_000
MAX_LIST = 15
DISCLAIMER = "No es asesoría financiera. Los resultados pasados no garantizan resultados futuros."


@dataclass
class AlertItem:
    pair: str
    direction: str                  # 'hot' (spring, compra) o 'cold' (upthrust, informativo)
    price: Optional[float]          # cierre de la vela de confirmacion = precio de referencia de entrada
    volume_x: Optional[float]       # volumen de la ruptura / promedio
    candle_open: pd.Timestamp       # apertura (UTC) de la vela de confirmacion
    concurrent: Optional[int] = None
    watched: Optional[int] = None
    dvol24h: Optional[float] = None
    change_24h: Optional[float] = None
    twitter_section: str = ''
    extra: dict = field(default_factory=dict)


def coin(pair: str) -> str:
    return pair.split('/')[0]


def fmt_price(value: Optional[float]) -> str:
    """Precio legible tanto para BTC (67,234) como para monedas de fracciones de centavo."""
    if value is None or value != value:
        return "?"
    v = float(value)
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 100:
        return f"{v:,.1f}"
    if v >= 1:
        return f"{v:,.2f}"
    if v >= 0.01:
        return f"{v:.4f}"
    if v <= 0:
        return "?"
    # monedas de fracciones de centavo: 4 cifras significativas (0.00000871), sin ceros de sobra
    decimals = -int(math.floor(math.log10(v))) + 3
    return f"{v:.{decimals}f}".rstrip('0')


def stop_price(price: Optional[float]) -> Optional[float]:
    return None if price is None else price * (1 - STOP_PCT / 100)


def when(dt_utc: pd.Timestamp, tz_name: str) -> str:
    """'vie 20:00 UTC (17:00 Santiago)'; agrega el dia local solo si cambia (p. ej. 'sáb 00:00 UTC (vie 20:00 Santiago)')."""
    t = pd.Timestamp(dt_utc)
    if t.tzinfo is None:
        t = t.tz_localize('UTC')
    text = f"{WEEKDAYS_ES[t.dayofweek]} {t:%H:%M} UTC"
    if tz_name and tz_name != 'UTC':
        local = t.tz_convert(pytz.timezone(tz_name))
        city = tz_name.split('/')[-1].replace('_', ' ')
        day = f"{WEEKDAYS_ES[local.dayofweek]} " if local.dayofweek != t.dayofweek else ""
        text += f" ({day}{local:%H:%M} {city})"
    return text


def close_time(item: AlertItem) -> pd.Timestamp:
    return pd.Timestamp(item.candle_open) + pd.Timedelta(hours=CANDLE_HOURS)


def exit_time(item: AlertItem) -> pd.Timestamp:
    return close_time(item) + pd.Timedelta(hours=HOLD_HOURS)


def late_notice(elapsed_hours: Optional[float]) -> str:
    """Bloque de aviso tardio (la vela cerro hace mas de 2 h, p. ej. el bot estuvo apagado)."""
    if elapsed_hours is None or elapsed_hours <= 2:
        return ""
    return (f"⏱️ <b>Aviso tardío:</b> la vela cerró hace {elapsed_hours:.1f} h (el bot estuvo sin revisar). "
            f"Cada 4 horas de retraso el resultado empeora ~0.5%. Si el precio ya subió bastante desde el "
            f"precio de referencia, es mejor no entrar.\n\n")


def liquidity_note(items: List[AlertItem]) -> str:
    low = [i for i in items if i.dvol24h is not None and i.dvol24h < LOW_LIQUIDITY_USD]
    if not low:
        return ""
    if len(items) == 1:
        v = low[0].dvol24h / 1e6
        return (f"⚠️ <b>Moneda poco líquida:</b> mueve solo {v:.1f} millones de USD al día. En el historial estas monedas "
                f"rindieron peor (~+0.5% y tocan el stop 1 de cada 4 veces). Usa muy poco dinero o sáltala.\n\n")
    names = ", ".join(coin(i.pair) for i in low[:6])
    return (f"⚠️ <b>Ojo con las poco líquidas</b> ({names}): mueven menos de 20 millones de USD al día y en el historial "
            f"rindieron peor. Prefiere las líquidas.\n\n")


def _wide(item_or_frac) -> bool:
    return item_or_frac >= WIDE_FRACTION


def _fraction(concurrent: Optional[int], watched: Optional[int]) -> Optional[float]:
    if not concurrent or not watched:
        return None
    return concurrent / watched


def strength_block(concurrent: Optional[int], watched: Optional[int]) -> str:
    """Que tan fuerte es la senal segun cuantas monedas hicieron lo mismo a la vez."""
    frac = _fraction(concurrent, watched)
    if frac is None:
        return ""
    if _wide(frac):
        return (f"<b>¿Qué tan fuerte es?</b>\n"
                f"🔥 Pánico generalizado: {concurrent} de {watched} monedas ({frac * 100:.0f}%) hicieron lo mismo en esta vela. "
                f"Es el caso con más ventaja histórica, pero <b>no es seguro</b>. En los 49 días así del historial "
                f"(comprando varias monedas a la vez y saliendo a las 72 h): un día típico dio <b>+0.6%</b>, "
                f"<b>4 a 5 de cada 10 días terminaron en pérdida</b>, y el rango normal fue de <b>−9.5% a +12%</b> "
                f"(algunos días muy buenos suben el promedio a +1.8%).\n\n")
    return (f"<b>¿Qué tan fuerte es?</b>\n"
            f"⚪ Caso poco extendido: solo {concurrent} de {watched} monedas ({frac * 100:.0f}%) hicieron lo mismo. "
            f"Aquí la ventaja histórica es <b>pequeña</b>: rindió ~+0.5% a +1% de media y ganó apenas 4 a 5 de cada 10 veces. "
            f"Si entras, que sea con poco dinero.\n\n")


def sizing_line(concurrent: Optional[int], watched: Optional[int], several: bool) -> str:
    frac = _fraction(concurrent, watched)
    if frac is not None and _wide(frac):
        return ("<b>¿Cuánto poner?</b>\n"
                "Reparte por igual entre 3 o más monedas de la lista y, en total, <b>no más de ~30% de tu capital</b> "
                "(así, en un mal día, pierdes cerca de 3% de tu capital; con 20% pierdes ~2%). Sin apalancamiento alto: "
                "usa 1x (con 3x la caída máxima del historial llegó a 46%).\n\n")
    return ("<b>¿Cuánto poner?</b>\n"
            "Poco: <b>hasta ~10% de tu capital</b> en total (si toca el stop de −10%, pierdes ~1% de tu capital). "
            "Sin apalancamiento alto: usa 1x.\n\n")


def _ticket(item: AlertItem, tz_name: str, several: bool) -> str:
    """Las tres cifras de la orden, arriba del relato, para leerlas en la primera pantalla."""
    exit_at = when(exit_time(item), tz_name)
    clock = (f"<b>Salida:</b> {exit_at}. Son 72 h después del cierre de la vela, no de este mensaje. "
             f"No cierres antes por miedo a una bajada chica.\n\n")
    if several:
        return (f"<b>Entrada:</b> ahora, a precio de mercado, varias monedas de la lista, en partes iguales. "
                f"El precio de referencia de cada fila es el cierre de la vela de 4 h, no tu precio de llenado.\n"
                f"<b>Stop:</b> stop loss de −{STOP_PCT}% sobre ese cierre (el precio está en cada fila). "
                f"No lo muevas ni lo quites.\n" + clock)
    price = fmt_price(item.price)
    stop = fmt_price(stop_price(item.price))
    return (f"<b>Entrada:</b> ahora, a precio de mercado. precio de referencia: <b>{price}</b> "
            f"(cierre de la vela de 4 h, no tu precio de llenado).\n"
            f"<b>Stop:</b> stop loss en <b>{stop}</b> (−{STOP_PCT}%). Es el −{STOP_PCT}% de ese cierre. "
            f"No lo muevas ni lo quites.\n" + clock)


def build_single_buy(item: AlertItem, tz_name: str, elapsed_hours: Optional[float]) -> str:
    coin_name = coin(item.pair)
    price = fmt_price(item.price)
    stop = fmt_price(stop_price(item.price))
    vol = f"{item.volume_x:.1f} veces lo normal" if item.volume_x else "mucho volumen"
    steps = (f"<b>¿Qué hacer? Paso a paso</b>\n"
             f"1️⃣ Compra (long) {coin_name} <b>ahora, a precio de mercado</b> (precio de referencia: <b>{price}</b>). "
             f"Esperar más no mejora el resultado.\n"
             f"2️⃣ Pon un <b>stop loss en {stop}</b> (−{STOP_PCT}%). Es obligatorio; no lo muevas ni lo quites.\n"
             f"3️⃣ Si no salta el stop, <b>cierra el {when(exit_time(item), tz_name)}</b> "
             f"(72 h después del cierre de la vela, no de este mensaje). "
             f"No cierres antes por miedo a una bajada chica: cerrar antes empeoró los resultados.\n"
             f"4️⃣ No compres más si baja (no promedies a la baja).\n\n")
    parts = [
        f"🟢 <b>OPORTUNIDAD DE COMPRA: {item.pair}</b>\n",
        _ticket(item, tz_name, several=False),
        f"🕐 La vela de 4 h cerró el {when(close_time(item), tz_name)}\n\n",
        late_notice(elapsed_hours),
        liquidity_note([item]),
        (f"<b>¿Qué pasó?</b>\n"
         f"{coin_name} cayó por debajo de su mínimo de los últimos 3 días con mucho volumen ({vol}) y enseguida "
         f"volvió a subir. Suele significar que los vendedores se agotaron y puede venir un rebote de unos días.\n\n"),
        strength_block(item.concurrent, item.watched),
        steps,
        sizing_line(item.concurrent, item.watched, several=False),
        ("<b>Ten presente</b>\n"
         "• No es seguro: puede perder, y perder es normal (4 a 5 de cada 10 veces).\n"
         "• Con monedas que luego se deslistaron, la ventaja bajó bastante; funciona mejor en monedas grandes.\n"
         f"• {DISCLAIMER}"),
    ]
    text = "".join(parts)
    if item.twitter_section:
        text += f"\n\n{item.twitter_section}"
    return text


def build_group_buy(items: List[AlertItem], tz_name: str, elapsed_hours: Optional[float]) -> str:
    n = len(items)
    concurrent = items[0].concurrent or n
    watched = items[0].watched
    frac = _fraction(concurrent, watched)
    wide = frac is not None and _wide(frac)
    ref = items[0]
    lines = []
    for it in sorted(items, key=lambda i: -(i.dvol24h or 0))[:MAX_LIST]:
        warn = " ⚠️" if (it.dvol24h is not None and it.dvol24h < LOW_LIQUIDITY_USD) else ""
        lines.append(f"• <b>{it.pair}</b>: ref {fmt_price(it.price)} → stop {fmt_price(stop_price(it.price))}{warn}")
    more = f"\n… y {n - MAX_LIST} más" if n > MAX_LIST else ""
    title = ("🟢 <b>OPORTUNIDAD DE COMPRA: pánico generalizado</b>" if wide
             else "🟢 <b>OPORTUNIDAD DE COMPRA: varias monedas a la vez</b>")
    what = (f"{concurrent} de {watched} monedas ({frac * 100:.0f}%) cayeron por debajo de su mínimo de los últimos 3 días con mucho "
            f"volumen y enseguida volvieron a subir, todas en la misma vela de 4 h. Suele significar que los vendedores se agotaron "
            f"y puede venir un rebote de unos días.") if frac is not None else (
        f"{n} monedas cayeron por debajo de su mínimo reciente con mucho volumen y volvieron a subir en la misma vela.")
    steps = (f"<b>¿Qué hacer? Paso a paso</b>\n"
             f"1️⃣ Compra (long) <b>varias monedas de la lista</b> (idealmente 3 o más, en partes iguales), <b>ahora, a precio de mercado</b>. "
             f"Mejor la canasta que una sola moneda: el resultado viene del conjunto.\n"
             f"2️⃣ En cada una pon un <b>stop loss de −{STOP_PCT}%</b> (el precio está en la lista). Obligatorio; no lo muevas.\n"
             f"3️⃣ Si no salta el stop, <b>cierra todo el {when(exit_time(ref), tz_name)}</b> "
             f"(72 h después del cierre de la vela, no de este mensaje). "
             f"No cierres antes por miedo a una bajada chica.\n"
             f"4️⃣ No compres más si baja (no promedies a la baja).\n\n")
    parts = [
        f"{title}\n",
        _ticket(ref, tz_name, several=True),
        f"🕐 La vela de 4 h cerró el {when(close_time(ref), tz_name)}\n\n",
        late_notice(elapsed_hours),
        f"<b>¿Qué pasó?</b>\n{what}\n\n",
        strength_block(concurrent, watched),
        f"<b>Monedas con señal</b> (precio de referencia → stop)\n" + "\n".join(lines) + more + "\n\n",
        liquidity_note(items) if any(i.dvol24h is not None and i.dvol24h < LOW_LIQUIDITY_USD for i in items) else "",
        steps,
        sizing_line(concurrent, watched, several=True),
        ("<b>Ten presente</b>\n"
         "• No es seguro: casi la mitad de los días así terminó en pérdida.\n"
         "• Con monedas que luego se deslistaron, la ventaja bajó bastante; funciona mejor en monedas grandes.\n"
         f"• {DISCLAIMER}"),
    ]
    return "".join(parts)


def build_info_bearish(items: List[AlertItem], tz_name: str, elapsed_hours: Optional[float]) -> str:
    ref = items[0]
    if len(items) == 1:
        head = f"🔴 <b>Aviso informativo (sin acción): {ref.pair}</b>"
        what = (f"{coin(ref.pair)} subió por encima de su máximo de los últimos 3 días con mucho volumen y enseguida volvió a caer.")
    else:
        names = ", ".join(coin(i.pair) for i in items[:10])
        more = f" y {len(items) - 10} más" if len(items) > 10 else ""
        head = f"🔴 <b>Aviso informativo (sin acción): {len(items)} monedas</b>"
        what = (f"Estas monedas subieron por encima de su máximo de los últimos 3 días con mucho volumen y enseguida volvieron a caer: "
                f"{names}{more}.")
    price = fmt_price(ref.price)
    vol = f"{ref.volume_x:.1f}×" if ref.volume_x else "alto"
    return (f"{head}\n"
            f"<b>Entrada:</b> ninguna. <b>Stop:</b> ninguno. <b>Salida:</b> ninguna.\n"
            f"<b>Qué hacer: Nada.</b> No abras una venta. No cierres una compra por este aviso.\n"
            f"{what} Podría venir una bajada, y aun así no se opera: en nuestras pruebas estos avisos "
            f"<b>no dieron ventaja para abrir ventas</b>. Úsalo solo como información.\n"
            f"🕐 La vela de 4 h cerró el {when(close_time(ref), tz_name)}. "
            f"Cierre {price}: solo para ubicar la vela, no es una orden. Volumen de la ruptura: {vol}.\n"
            f"{late_notice(elapsed_hours)}"
            f"<i>{DISCLAIMER}</i>")


def build_radar(pair: str, rel_vol: float, candle_change: float, candle_open: pd.Timestamp, tz_name: str,
                elapsed_hours: Optional[float], twitter_section: str = "") -> str:
    color = "subió" if candle_change >= 0 else "bajó"
    close = pd.Timestamp(candle_open) + pd.Timedelta(hours=CANDLE_HOURS)
    text = (f"🛰️ <b>Movimiento raro: {pair}</b> (solo para mirar)\n"
            f"<b>Entrada:</b> ninguna. <b>Stop:</b> ninguno. <b>Salida:</b> ninguna.\n"
            f"<b>Qué hacer:</b> nada. <b>No hay ventaja comprobada</b>. No entres solo por este aviso.\n"
            f"🕐 La vela de 4 h cerró el {when(close, tz_name)}\n"
            f"{late_notice(elapsed_hours)}"
            f"<b>¿Qué pasó?</b>\n"
            f"{coin(pair)} {color} {abs(candle_change):.1f}% en esta vela con muchísimo volumen ({rel_vol:.1f} veces lo normal), "
            f"pero <b>sin el patrón de rebote</b> de las oportunidades de compra. Este aviso no trae precio de orden.\n")
    if twitter_section:
        text += f"\n{twitter_section}\n"
    text += f"\n<i>{DISCLAIMER}</i>"
    return text
