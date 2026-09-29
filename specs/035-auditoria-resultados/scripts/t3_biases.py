"""
Auditoria crypto-signal - Tarea 3 (sesgos que se pueden cuantificar con los datos dados).
- (a) supervivencia / historia incompleta (config + logs)
- (b) retraso de ejecucion (bot_alertas_registro.jsonl + ccxt 15m)
- (c) funding y comisiones incluidos (zips + logs)
- (d) numero de hipotesis (conteo manual citado del README) -> se documenta aqui el conteo.
Salida: audit/out_t3.json
"""
import json, zipfile, os, glob, collections
from datetime import datetime, timezone, timedelta

OUT = {}

# ---------- (a) supervivencia ----------
cfg = json.load(open('audit_data/strategies/config_wyckoff_lab.json', encoding='utf-8'))
whitelist = cfg['exchange']['pair_whitelist']
# warnings vistos en los logs de este clon (grep): EOS removido; ICP y APE sin historia completa 2022
out = {
    'pares_en_whitelist': len(whitelist),
    'pares_incluye_BTC': 'BTC/USDT:USDT' in whitelist,
    'removidos_por_incompatibles': ['EOS/USDT:USDT'],
    'sin_historia_completa_2022': {
        'ICP/USDT:USDT': '2022-09-27',
        'APE/USDT:USDT': '2022-03-17',
    },
    'pares_efectivos_backtest': len(whitelist) - 1,
    'nota_delistados': 'NO VERIFICABLE: no hay datos de pares delistados ni del universo point-in-time de 2022.',
}
OUT['supervivencia'] = out
print("[3a]", json.dumps(out, ensure_ascii=False, indent=1))

# ---------- (c) funding y comisiones ----------
zips = {
    'springSL10_signal_IS': 'backtest-result-2026-09-29_15-29-54.zip',
    'springSL10_signal_OOS': 'backtest-result-2026-09-29_15-29-19.zip',
    'springSL10_real_IS': 'backtest-result-2026-09-29_15-31-01.zip',
    'springSL10_real_OOS': 'backtest-result-2026-09-29_15-30-46.zip',
}
fund = {}
for label, z in zips.items():
    zz = zipfile.ZipFile(os.path.join('audit_data/lab_trades', z))
    name = [n for n in zz.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
    d = json.loads(zz.read(name)); m = d['strategy'][list(d['strategy'])[0]]
    tr = m['trades']
    fx = sum(t.get('funding_fees') or 0 for t in tr)
    gross = sum(abs(t['profit_abs']) for t in tr)
    # fee implicito: compare safe_price de entrada/salida con open/close rate (approx)
    fund[label] = {
        'n': len(tr),
        'trades_con_funding_distinto_de_0': sum(1 for t in tr if (t.get('funding_fees') or 0) != 0),
        'funding_total_abs': round(fx, 3),
        'fee_open_uniforme': sorted(set(round(t['fee_open'], 6) for t in tr)),
        'fee_close_uniforme': sorted(set(round(t['fee_close'], 6) for t in tr)),
        'funding_pct_del_bruto': round(100 * fx / gross, 3) if gross else None,
    }
OUT['funding_comisiones'] = fund
print("\n[3c] funding/comisiones:", json.dumps(fund, ensure_ascii=False, indent=1))

# ---------- (b) retraso de ejecucion ----------
rec = [json.loads(l) for l in open('audit_data/bot_alertas_registro.jsonl', encoding='utf-8') if l.strip()]
CANDLE = timedelta(hours=4)
rows = []
for e in rec:
    c = datetime.fromisoformat(e['candle'])
    close = c + CANDLE
    r = datetime.fromisoformat(e['recorded_at'])
    rows.append({
        'pair': e['pair'], 'type': e['type'], 'direction': e.get('direction'),
        'candle': e['candle'], 'recorded_at': e['recorded_at'],
        'min_tras_cierre': round((r - close).total_seconds() / 60, 1),
        'cerrada_antes_de_avisar': r >= close,
    })
OUT['retraso_jsonl'] = rows
print("\n[3b] registros y latencia (min desde el cierre de la vela):")
for r in rows:
    print(f"   {r['recorded_at'][:19]} type={r['type']:8} {r['pair']:12} candle={r['candle'][:19]} "
          f"lat={r['min_tras_cierre']:>7}min cerrada={r['cerrada_antes_de_avisar']}")

with open('audit/out_t3.json', 'w', encoding='utf-8') as f:
    json.dump(OUT, f, indent=1, ensure_ascii=False, default=str)
print("\n-> audit/out_t3.json escrito")
