"""
Validacion hacia adelante de las alertas REALES (specs/040-validacion-hacia-adelante/).

Lee agent_state/rumor_radar.jsonl, baja las velas 4h de Binance (publico, solo lectura) y calcula el
resultado de cada alerta con el mismo plan del mensaje: entrada a la apertura de la vela siguiente a la
confirmacion, stop -10% sobre minimos (spring/long), salida a las 72h; tambien el retorno a 24h. Luego
compara los grupos que el bot ya registra (pares simultaneos, barrida, fin de semana, caida 24h, y desde
la spec 037 funding / libro / open interest / long-short / menciones).

Uso (desde Desktop/deploy):
  docker cp crypto-signal:/app/agent_state/rumor_radar.jsonl ./rumor_radar.jsonl
  docker run --rm -v "$PWD:/work" -w /work crypto-signal:dev python specs/040-validacion-hacia-adelante/validate_forward.py rumor_radar.jsonl

No concluye nada con menos de MIN_ALERTS alertas maduras (>= 72h): con muestras chicas cualquier
diferencia es ruido (Principio III). Solo describe; nunca modifica el bot.
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
CANDLE = pd.Timedelta(hours=4)


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


def outcome(ex, alert, now):
    """Retornos % (neto de comisiones) a 24h y 72h para spring (long) o upthrust (short), o None si no maduro."""
    symbol = alert['pair'] if ':' in alert['pair'] else alert['pair']
    conf = pd.Timestamp(alert['candle'])
    entry_ts = conf + CANDLE                                   # apertura de la vela siguiente
    if now < entry_ts + timedelta(hours=24):
        return None
    since = int(entry_ts.timestamp() * 1000)
    candles = ex.fetch_ohlcv(symbol, '4h', since=since, limit=20)
    df = pd.DataFrame(candles, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    df['t'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df = df[df.t >= entry_ts].reset_index(drop=True)
    if df.empty:
        return None
    entry = df.o.iloc[0]
    sign = 1 if alert['direction'] == 'hot' else -1
    res = {}
    for label, n in (('r24', 6), ('r72', 18)):
        if len(df) < n or now < entry_ts + timedelta(hours=4 * n):
            res[label] = None
            continue
        part = df.iloc[:n]
        adverse = (part.l.min() / entry - 1) * 100 if sign == 1 else -(part.h.max() / entry - 1) * 100
        if adverse <= STOP_PCT:
            res[label] = STOP_PCT - FEE_ROUNDTRIP_PCT
        else:
            res[label] = sign * (part.c.iloc[-1] / entry - 1) * 100 - FEE_ROUNDTRIP_PCT
    return res


def summarize(name, d, col):
    d = d.dropna(subset=[col])
    if d.empty:
        return f"  {name:34s} n=0"
    return f"  {name:34s} n={len(d):3d} media={d[col].mean():+6.2f}% acierto={(d[col] > 0).mean() * 100:4.0f}%"


def main(path):
    ex = ccxt.binance({'enableRateLimit': True})
    now = pd.Timestamp.now(tz='UTC')
    alerts = load_alerts(path)
    rows = []
    for a in alerts:
        try:
            o = outcome(ex, a, now)
        except Exception as e:
            print(f"  (no se pudo evaluar {a['pair']} {a['candle']}: {e})")
            continue
        micro = a.get('micro') or {}
        rows.append(dict(
            pair=a['pair'], candle=a['candle'], direction=a['direction'],
            r24=(o or {}).get('r24'), r72=(o or {}).get('r72'),
            concurrent=a.get('concurrent_pairs'), watched=a.get('watched_pairs') or 30, sweep=a.get('sweep_depth_pct'),
            weekend=a.get('weekend_close'), chg24=a.get('change_24h_pct'),
            funding=micro.get('funding_rate_pct'), imbalance=micro.get('book_imbalance'),
            oi_chg=micro.get('oi_change_24h_pct'), ls=micro.get('long_short_ratio'),
            mention_ratio=a.get('ratio')))
    df = pd.DataFrame(rows)
    print(f"Alertas wyckoff registradas: {len(alerts)} | evaluadas: {len(df)}")
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
    """Nivel EPISODIO (spec 050): la unidad independiente es el dia/vela de capitulacion amplia, no cada alerta."""
    hot = df[(df.direction == 'hot') & df.r72.notna() & df.concurrent.notna()].copy()
    hot['wide'] = (hot.concurrent / hot.watched) >= 0.20
    ep = hot[hot.wide].groupby('candle').r72.agg(['mean', 'count']).rename(columns={'mean': 'canasta', 'count': 'springs'})
    print(f"== EPISODIOS DE CAPITULACION AMPLIA (>= 20% de los pares): {len(ep)} episodios maduros")
    print("  Referencia historica por dia (49 dias, spec 050): media +1.76%, mediana +0.57%, 45% de los dias en rojo, p10 -9.45%, p90 +12.0%")
    if len(ep):
        print(f"  Observado: media {ep.canasta.mean():+.2f}% | mediana {ep.canasta.median():+.2f}% | dias en rojo {(ep.canasta < 0).mean()*100:.0f}% | springs por episodio: mediana {int(ep.springs.median())}")
    print("  Con sd diaria ~7.4 pp: 10 episodios NO alcanzan para juzgar (error estandar ~2.3 pp); ~25 episodios dan una idea gruesa; un monitor")
    print("  secuencial de degradacion necesita ~100 episodios (~10 anios). Mientras tanto: gobernar el RIESGO, no concluir sobre el edge.")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'agent_state/rumor_radar.jsonl')
