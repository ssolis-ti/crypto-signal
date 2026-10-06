"""
Validacion hacia adelante de las alertas REALES (specs/040-validacion-hacia-adelante/).

Lee agent_state/rumor_radar.jsonl, baja las velas 4h de Binance USD-M (publico, solo lectura) y calcula
el resultado con el plan del estudio: entrada a la apertura de la vela siguiente, stop -10% del CIERRE
de la vela de senal, salida a las 72h. Si la mecha cruza el stop, el retorno queda en el precio del
stop (no en el minimo) y el hueco se anota aparte: no filtra ni cambia el aviso.

El episodio amplio promedia solo springs elegibles (liquidos). watched_pairs ausente no se sustituye
por 30. No concluye con menos de MIN_ALERTS alertas maduras. Solo describe; no modifica el bot.

Uso (desde la raiz del repo):
  docker run --rm -v "$PWD:/work" -w /work crypto-signal-crypto-signal python specs/040-validacion-hacia-adelante/validate_forward.py app/agent_state/rumor_radar.jsonl
"""
import json
import sys
from datetime import timedelta

import ccxt
import numpy as np
import pandas as pd

MIN_ALERTS = 50
STOP_PCT = -10.0
FEE_ROUNDTRIP_PCT = 0.1
LOW_LIQUIDITY_USD = 20_000_000
WIDE_FRACTION = 0.20
CANDLE = pd.Timedelta(hours=4)
# Nombres spot que Binance USD-M lista distinto. No cambia la senal; solo permite bajar la vela.
USD_M_ALIASES = {
    'PEPE/USDT': '1000PEPE/USDT:USDT',
    'MSTRB/USDT': 'MSTR/USDT:USDT',
    'CRCLB/USDT': 'CRCL/USDT:USDT',
    'SPCXB/USDT': 'SPCX/USDT:USDT',
}


def load_alerts(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get('type') == 'wyckoff' and e.get('candle'):
                rows.append(e)
    return rows


def futures_symbol(pair):
    """Spot BTC/USDT y perpetuo BTC/USDT:USDT apuntan al mismo contrato USD-M."""
    if not isinstance(pair, str) or '/' not in pair:
        return pair
    mapped = USD_M_ALIASES.get(pair)
    if mapped:
        return mapped
    if ':' in pair:
        return pair
    quote = pair.split('/')[1]
    return f'{pair}:{quote}'


def watched_count(alert):
    """0 es un universo vacio, no el defecto 30. Ausente queda en None."""
    value = alert.get('watched_pairs')
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_eligible(alert):
    """Spring liquido. Sin marca ni volumen, no entra en la media del episodio."""
    if 'eligible' in alert and alert.get('eligible') is not None:
        return bool(alert.get('eligible'))
    dvol = alert.get('dvol24h_usd')
    if dvol is None:
        return False
    try:
        return float(dvol) >= LOW_LIQUIDITY_USD
    except (TypeError, ValueError):
        return False


def as_utc(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize('UTC')
    return ts.tz_convert('UTC')


def path_result(part, entry, signal_close, sign):
    """
    Retorno % neto de comisiones y hueco del stop en puntos de precio relativo al cierre.

    El stop esta en el cierre de la senal, no en la apertura de entrada. Si se toca, el retorno
    es el del precio de stop contra la entrada. El hueco (cuanto la mecha paso de largo) se
    devuelve para anotarlo y no entra en el retorno.
    """
    if not np.isfinite(entry) or entry <= 0 or not np.isfinite(signal_close) or signal_close <= 0:
        return None, None
    stop_price = signal_close * (1 + sign * STOP_PCT / 100.0)
    if sign == 1:
        extreme = float(part.l.min())
        stopped = extreme <= stop_price
        gap = (stop_price - extreme) / signal_close * 100.0 if stopped else None
    else:
        extreme = float(part.h.max())
        stopped = extreme >= stop_price
        gap = (extreme - stop_price) / signal_close * 100.0 if stopped else None
    if stopped:
        ret = sign * (stop_price / entry - 1.0) * 100.0 - FEE_ROUNDTRIP_PCT
    else:
        ret = sign * (float(part.c.iloc[-1]) / entry - 1.0) * 100.0 - FEE_ROUNDTRIP_PCT
    return ret, gap


def outcome(ex, alert, now):
    """Retornos % a 24h y 72h, o None si todavia no madura la ventana de 24h."""
    symbol = futures_symbol(alert['pair'])
    conf = as_utc(alert['candle'])
    entry_ts = conf + CANDLE
    if now < entry_ts + timedelta(hours=24):
        return None
    since = int(conf.timestamp() * 1000)
    candles = ex.fetch_ohlcv(symbol, '4h', since=since, limit=22)
    df = pd.DataFrame(candles, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    if df.empty:
        return None
    df['t'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    signal = df[(df.t - conf).abs() <= pd.Timedelta(minutes=1)]
    forward = df[df.t >= entry_ts - pd.Timedelta(minutes=1)].reset_index(drop=True)
    if signal.empty or forward.empty:
        return None
    signal_close = float(signal.c.iloc[-1])
    entry = float(forward.o.iloc[0])
    sign = 1 if alert['direction'] == 'hot' else -1
    res = {}
    for label, n in (('r24', 6), ('r72', 18)):
        if len(forward) < n or now < entry_ts + timedelta(hours=4 * n):
            res[label] = None
            res[label.replace('r', 'gap')] = None
            continue
        ret, gap = path_result(forward.iloc[:n], entry, signal_close, sign)
        res[label] = ret
        res[label.replace('r', 'gap')] = gap
    return res


def summarize(name, d, col):
    d = d.dropna(subset=[col])
    if d.empty:
        return f"  {name:34s} n=0"
    return f"  {name:34s} n={len(d):3d} media={d[col].mean():+6.2f}% acierto={(d[col] > 0).mean() * 100:4.0f}%"


def episode_table(df):
    """Canasta del dia amplio: solo springs liquidos, con el universo que el bot registro."""
    hot = df[(df.direction == 'hot') & df.r72.notna() & df.concurrent.notna() & df.eligible.fillna(False)].copy()
    hot = hot[hot.watched.notna() & (hot.watched > 0)]
    if hot.empty:
        return hot
    hot['wide'] = (hot.concurrent / hot.watched) >= WIDE_FRACTION
    wide = hot[hot.wide]
    if wide.empty:
        return wide
    return wide.groupby('candle').r72.agg(['mean', 'count']).rename(columns={'mean': 'canasta', 'count': 'springs'})


def main(path):
    ex = ccxt.binanceusdm({'enableRateLimit': True})
    now = pd.Timestamp.now(tz='UTC')
    alerts = load_alerts(path)
    rows = []
    for a in alerts:
        try:
            o = outcome(ex, a, now)
        except Exception as e:
            print(f"  (no se pudo evaluar {a.get('pair')} {a.get('candle')}: {e})")
            continue
        micro = a.get('micro') or {}
        rows.append(dict(
            pair=a['pair'], candle=a['candle'], direction=a['direction'],
            r24=(o or {}).get('r24'), r72=(o or {}).get('r72'),
            gap24=(o or {}).get('gap24'), gap72=(o or {}).get('gap72'),
            concurrent=a.get('concurrent_pairs'), watched=watched_count(a),
            eligible=is_eligible(a),
            sweep=a.get('sweep_depth_pct'),
            weekend=a.get('weekend_close'), chg24=a.get('change_24h_pct'),
            funding=micro.get('funding_rate_pct'), imbalance=micro.get('book_imbalance'),
            oi_chg=micro.get('oi_change_24h_pct'), ls=micro.get('long_short_ratio'),
            mention_ratio=a.get('ratio')))
    df = pd.DataFrame(rows)
    print(f"Alertas wyckoff registradas: {len(alerts)} | evaluadas: {len(df)}")
    print("Mercado: Binance USD-M. Stop: -10% del cierre de la vela de senal. Entrada: apertura siguiente.")
    if df.empty:
        return
    for direction, label in (('hot', 'SPRING (long) — el que tiene edge'), ('cold', 'UPTHRUST (short) — solo informativo')):
        d = df[df.direction == direction]
        mature = d.dropna(subset=['r72'])
        print(f"\n== {label}: {len(d)} alertas, {len(mature)} maduras (>= 72h)")
        print(summarize('todas (24h)', d, 'r24'))
        print(summarize('todas (72h)', d, 'r72'))
        if direction == 'hot':
            print("  Referencia del backtest: 72h con stop -10% => acierto 56-58%, media +1.5% a +1.8%")
            stopped = mature[mature.gap72.notna()]
            through = stopped[stopped.gap72 > 0]
            if stopped.empty:
                print("  Hueco del stop: ningun stop tocado en las maduras.")
            elif through.empty:
                print(f"  Hueco del stop (no filtra): {len(stopped)} llenaron en el precio del stop, sin mecha de mas.")
            else:
                print(f"  Hueco del stop (no filtra): {len(through)} de {len(stopped)} stops pasaron el precio; "
                      f"mediana={through.gap72.median():.2f} pp peor={through.gap72.max():.2f} pp")
        if len(mature) < MIN_ALERTS:
            print(f"  -> {len(mature)} < {MIN_ALERTS}: MUESTRA INSUFICIENTE; no sacar conclusiones de los cortes de abajo.")
        cuts = {
            'pares simultaneos >= 5': d.concurrent >= 5, 'pares simultaneos < 5': d.concurrent < 5,
            'barrida >= 1%': d.sweep >= 1.0, 'barrida < 1%': d.sweep < 1.0,
            'cierre en fin de semana': d.weekend == True, 'cierre entre semana': d.weekend == False,
            'caida 24h <= -8%': d.chg24 <= -8, 'funding < 0': d.funding < 0, 'funding >= 0': d.funding >= 0,
            'libro: mas compra que venta': d.imbalance > 0, 'libro: mas venta que compra': d.imbalance < 0,
            'open interest sube (24h)': d.oi_chg > 0, 'open interest baja (24h)': d.oi_chg < 0,
            'menciones x2 o mas': d.mention_ratio >= 2,
        }
        for name, mask in cuts.items():
            sub = d[mask.fillna(False)]
            if len(sub):
                print(summarize(name, sub, 'r72'))
    episodes_report(df)


def episodes_report(df):
    """Nivel EPISODIO (spec 050): la unidad es el dia amplio, y solo con springs liquidos."""
    ep = episode_table(df)
    print(f"== EPISODIOS DE CAPITULACION AMPLIA (>= 20% de los pares liquidos): {len(ep)} episodios maduros")
    print("  Solo entran springs con eligible o volumen 24h >= 20M. watched_pairs ausente no cuenta como 30.")
    print("  Referencia historica por dia (49 dias, spec 050): media +1.76%, mediana +0.57%, 45% de los dias en rojo, p10 -9.45%, p90 +12.0%")
    if len(ep):
        print(f"  Observado: media {ep.canasta.mean():+.2f}% | mediana {ep.canasta.median():+.2f}% | dias en rojo {(ep.canasta < 0).mean()*100:.0f}% | springs por episodio: mediana {int(ep.springs.median())}")
    print("  Con sd diaria ~7.4 pp: 10 episodios NO alcanzan para juzgar (error estandar ~2.3 pp); ~25 episodios dan una idea gruesa; un monitor")
    print("  secuencial de degradacion necesita ~100 episodios (~10 anios). Mientras tanto: gobernar el RIESGO, no concluir sobre el edge.")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'app/agent_state/rumor_radar.jsonl')
