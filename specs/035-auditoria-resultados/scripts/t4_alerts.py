"""
Auditoria crypto-signal - Tarea 4 (alertas reales del bot).
- Separa registros invalidos (vela sin cerrar) y duplicados por reinicio.
- Baja precios publicos (ccxt, solo lectura) y calcula lo que SE PUEDE:
  retorno a 24h/72h (marcar NO DISPONIBLE si el futuro no existe), MAE/MFE y stop.
- Radar: compara |retorno| posterior vs una vela de volumen normal del mismo par.
Salida: audit/out_t4.json
"""
import json, collections, statistics
from datetime import datetime, timezone, timedelta
import ccxt

CANDLE = timedelta(hours=4)
rec = [json.loads(l) for l in open('audit_data/bot_alertas_registro.jsonl', encoding='utf-8') if l.strip()]

# --- clasificacion ---
invalidos, vistos, validos = [], {}, []
for i, e in enumerate(rec):
    c = datetime.fromisoformat(e['candle']); close = c + CANDLE
    r = datetime.fromisoformat(e['recorded_at'])
    if r < close:
        invalidos.append(('vela_sin_cerrar', i, e))
        continue
    key = (e['pair'], e['type'], e.get('direction'), e['candle'])
    if key in vistos:
        invalidos.append(('duplicado_reinicio', i, e))
        continue
    vistos[key] = i
    validos.append((i, e))

print(f"registros totales={len(rec)}  invalidos={len(invalidos)}  validos unicos={len(validos)}")
print("INVALIDOS:")
for motivo, i, e in invalidos:
    print(f"  #{i} {motivo}: {e['recorded_at'][:19]} {e['type']} {e['pair']} candle={e['candle'][:19]}")
print("VALIDOS UNICOS:")
for i, e in validos:
    print(f"  #{i} {e['recorded_at'][:19]} {e['type']} {e['pair']} dir={e.get('direction')} candle={e['candle'][:19]} rel_vol={e.get('relative_volume')}")

# --- precios publicos ---
ex = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
now = datetime.now(timezone.utc)
print("\nHora actual (UTC):", now.isoformat())

results = []
for i, e in validos:
    sym = e['pair'].replace('/USDT', '/USDT:USDT')
    c = datetime.fromisoformat(e['candle']); close = c + CANDLE
    entry_ts = int(close.timestamp() * 1000)
    r = datetime.fromisoformat(e['recorded_at'])
    try:
        o = ex.fetch_ohlcv(sym, '15m', since=int(c.timestamp() * 1000), limit=300)
    except Exception as ex2:
        results.append({'pair': e['pair'], 'error': str(ex2)})
        continue
    if not o:
        results.append({'pair': e['pair'], 'error': 'sin datos'})
        continue
    by_ts = {int(x[0]): x for x in o}
    entry = by_ts.get(entry_ts)
    if entry is None:
        # primer candle >= entry_ts
        cand = [x for x in o if x[0] >= entry_ts]
        entry = cand[0] if cand else None
    ent = entry[1] if entry else None
    # precio al momento del aviso
    alert_c = [x for x in o if x[0] <= int(r.timestamp() * 1000)]
    alert_px = alert_c[-1][4] if alert_c else None
    last = o[-1]
    last_t = datetime.fromtimestamp(last[0] / 1000, tz=timezone.utc)
    horizon = (last_t - close).total_seconds() / 3600.0

    def ret_at(hours):
        tgt = entry_ts + int(hours * 3600 * 1000)
        cand = [x for x in o if x[0] >= tgt]
        if not cand:
            return None
        return 100.0 * (cand[0][1] - ent) / ent  # open del candle en tgt (mas cercano)

    # MAE/MFE sobre la ventana disponible (desde entry)
    after = [x for x in o if x[0] >= entry_ts]
    mae = 100.0 * (min(x[3] for x in after) - ent) / ent if after else None
    mfe = 100.0 * (max(x[2] for x in after) - ent) / ent if after else None
    is_short = e.get('direction') == 'cold'
    if is_short:
        mae_side, mfe_side = 100.0 * (max(x[2] for x in after) - ent) / ent, 100.0 * (min(x[3] for x in after) - ent) / ent
    else:
        mae_side, mfe_side = mae, mfe
    stop = None
    if is_short:
        stop = (100.0 * (max(x[2] for x in after) - ent) / ent >= 10.0) if after else None
    else:
        stop = (100.0 * (min(x[3] for x in after) - ent) / ent <= -10.0) if after else None
    results.append({
        'pair': e['pair'], 'type': e['type'], 'direction': e.get('direction'),
        'candle_close': close.isoformat(), 'entry_15m_open': ent,
        'precio_al_avisar': alert_px,
        'slippage_aviso_vs_entrada_pct': round(100.0 * (alert_px - ent) / ent, 3) if alert_px and ent else None,
        'horas_disponibles_desde_cierre': round(horizon, 1),
        'ret_24h_pct': ret_at(24), 'ret_72h_pct': ret_at(72),
        'ret_disponible_pct': ret_at(horizon) if horizon > 0 else None,
        'mae_lado_pct': round(mae_side, 2) if mae_side is not None else None,
        'mfe_lado_pct': round(mfe_side, 2) if mfe_side is not None else None,
        'stop_10pct_tocado': stop,
        'alert_sent': e.get('alert_sent'),
    })

print("\nRESULTADO POR EVENTO VALIDO:")
for r in results:
    print(" ", json.dumps(r, ensure_ascii=False))

# --- radar: comparar |retorno| vs vela de volumen normal del mismo par ---
print("\nRADAR: |retorno| posterior del evento vs una vela 4h de volumen normal (mismo par, misma ventana disponible):")
radar_cmp = []
for r in results:
    if r.get('type') != 'radar' or r.get('entry_15m_open') is None:
        continue
    sym = r['pair'].replace('/USDT', '/USDT:USDT')
    c = datetime.fromisoformat(r['candle_close']) - CANDLE
    o4 = ex.fetch_ohlcv(sym, '4h', limit=80)
    if len(o4) < 25:
        continue
    vols = [x[5] for x in o4]
    relvol = [None] * len(o4)
    for k in range(20, len(o4)):
        m = sum(vols[k - 20:k]) / 20
        relvol[k] = vols[k] / m if m else None
    # ultima vela 4h con relvol < 2.5, ya cerrada, anterior al evento
    norm = None
    for k in range(len(o4) - 2, 19, -1):
        if o4[k][0] < int(c.timestamp() * 1000) and relvol[k] is not None and relvol[k] < 2.5:
            norm = o4[k]
            break
    if norm is None:
        continue
    nt = int(norm[0])
    after = [x for x in o4 if x[0] > nt]
    if not after:
        continue
    # ventana comparable: misma cantidad de horas que el evento
    h = r['horas_disponibles_desde_cierre']
    window = [x for x in after if x[0] <= nt + int(h * 3600 * 1000)]
    if not window:
        continue
    norm_move = 100.0 * (window[-1][4] - norm[4]) / norm[4]
    cmp = {
        'pair': r['pair'], 'event_abs_move_pct': abs(r['ret_disponible_pct']),
        'normal_candle_date': datetime.fromtimestamp(nt / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M'),
        'normal_abs_move_pct': round(abs(norm_move), 2),
        'horas': round(h, 1),
        'evento_mayor': abs(r['ret_disponible_pct']) > abs(norm_move),
    }
    radar_cmp.append(cmp)
    print(" ", json.dumps(cmp, ensure_ascii=False))

json.dump({'invalidos': [(m, i) for m, i, _ in invalidos], 'validos': [i for i, _ in validos],
           'resultados': results, 'radar_cmp': radar_cmp},
          open('audit/out_t4.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False, default=str)
print("\n-> audit/out_t4.json escrito")
