[0m
> plan · deepseek-flash
[0m→ [0mRead . 
[0m→ [0mRead README.md 
[0m→ [0mRead audit_data/DATOS_LEEME.md 
[0m→ [0mRead docs/ESTADO_Y_PENDIENTES.md 
> plan · deepseek-flash
[0m→ [0mRead specs/036-minutos-criticos 
[0m→ [0mRead app 
[0m→ [0mRead specs/039-springs-perdidos-y-eql/spec.md 
> plan · deepseek-flash
[0m→ [0mRead specs/036-minutos-criticos/resultado_m1.txt 
[0m→ [0mRead specs/036-minutos-criticos/spec.md 
[0m→ [0mRead specs/036-minutos-criticos/resultado_be.txt 
[0m→ [0mRead specs/036-minutos-criticos/resultado_levels.txt 
> plan · deepseek-flash
[0m✱ [0mGrep "datetime|timezone|astimezone|tzinfo|utcnow|now\(\)|pytz|zoneinfo|fromtimestamp|utcfromtimestamp" [90min app · 59 matches[0m
[0m✱ [0mGrep "dayofweek|weekday|strftime|isoformat|timestamp|sleep|update_interval|schedule|apscheduler|timedelta" [90min app · 94 matches[0m
> plan · deepseek-flash
[0m→ [0mRead app/analysis/wyckoff_alerts.py 
> plan · deepseek-flash
[0m→ [0mRead app/app.py 
[0m→ [0mRead app/data/manager.py 
[0m→ [0mRead app/analysis/twitter_sentiment.py 
> plan · deepseek-flash
[0m→ [0mRead app/behaviour/core.py 
[0m→ [0mRead app/notifications/builder.py 
> plan · deepseek-flash
[0m→ [0mRead Dockerfile 
[0m→ [0mRead docker-compose.yml 
[0m→ [0mRead app/conf.py 
[0m→ [0mRead app/defaults.yml 
> plan · deepseek-flash
[0m→ [0mRead app/notifications/queue.py 
[0m→ [0mRead app/analysis/market_microstructure.py 
[0m→ [0mRead app/notifications/core.py 
> plan · deepseek-flash
[0m→ [0mRead config-clean.yml 
[0m→ [0mRead app/behaviour/data.py 
[0m→ [0mRead app/exchanges/driver.py 
> plan · deepseek-flash
[0m→ [0mRead app/outputs.py 
[0m→ [0mRead app/notifications/smart.py 
[0m→ [0mRead app/rendering/core.py 
> plan · deepseek-flash
[0m→ [0mRead audit_data/bot_alertas_registro.jsonl [90m[limit=30][0m
[0m→ [0mRead audit_data/bot_alertas_log.txt [90m[limit=60][0m
[0m→ [0mRead app/analysis/strategy_analyzer.py 
> plan · deepseek-flash
[0m✱ [0mGrep "weekend|dayofweek|weekday|sab|dom" [90min audit_data/strategies · 2 matches[0m
[0m✱ [0mGrep "weekend|dayofweek|weekday" [90min specs/036-minutos-criticos · 4 matches[0m
[0m$ [0mls tests; echo ---; ls tests/unit 2>/dev/null; echo ---; ls specs/002-utc-internal-time specs/003-utc-start-date specs/006-deferred-cleanup-findings 2>/dev/null
__init__.py
__pycache__
analysis
analyzers
api
behaviour
data
exchanges
notifications
notifiers
rendering
test_qa_conf_adversarial.py
utils
---
---
specs/002-utc-internal-time:
checklists
data-model.md
plan.md
quickstart.md
research.md
spec.md
tasks.md

specs/003-utc-start-date:
checklists
data-model.md
plan.md
quickstart.md
research.md
spec.md
tasks.md

specs/006-deferred-cleanup-findings:
checklists
data-model.md
plan.md
quickstart.md
research.md
spec.md
tasks.md
> plan · deepseek-flash
[0m→ [0mRead specs/003-utc-start-date/spec.md 
[0m→ [0mRead specs/002-utc-internal-time/spec.md 
[0m→ [0mRead specs/006-deferred-cleanup-findings/spec.md 
> plan · deepseek-flash
[0m→ [0mRead app/logs.py 
[0m✱ [0mGrep "timezone|utc|dayofweek|_is_weekend|_stale|drop_unclosed|timestamp" [90min tests · 105 matches[0m
[0m✱ [0mGrep "creation_date|set_timezone|timezone_str" [90min app · 14 matches[0m
> plan · deepseek-flash
[0m✱ [0mGrep "timezone|UTC|utc|hora|Santiago|weekend|fin de semana" [90min AUDIT_RESULTADOS.md · 3 matches[0m
[0m✱ [0mGrep "timezone|UTC|hora|Santiago|creation_date|timestamp" [90min QA_REPORT_senales_mensajes.md · 3 matches[0m
[0m$ [0mgit log --oneline -15
17a2490 improvements
ee27cd4 improvements
c05eced fix
e7c8728 improvements
05360a8 improvements
f2e51be improvements
b3205c9 improvements
1a5324d improvements
f652c6d improvements
b7394da improvements
c39365b fix
fa0a7b5 fix
38ef158 improvements
b9fac2c improvements
b0d3128 fix
> plan · deepseek-flash
[0m→ [0mRead QA_REPORT_senales_mensajes.md [90m[offset=1, limit=130][0m
[0m→ [0mRead AUDIT_RESULTADOS.md [90m[offset=160, limit=60][0m
> plan · deepseek-flash
[0m✱ [0mGrep "hour|dow|dayofweek|open_date|close_date|UTC|utc" [90min specs/036-minutos-criticos/scripts · 28 matches[0m
[0m$ [0mls specs/036-minutos-criticos/scripts; echo ---; sed -n '1,60p' specs/036-minutos-criticos/scripts/analysis_weekend.py; echo === AN_BE ===; sed -n '1,60p' specs/036-minutos-criticos/scripts/analysis_be.py
analysis_be.py
analysis_levels.py
analysis_m1.py
analysis_weekend.py
fetch_m1.py
---
import pickle, sys
import numpy as np, pandas as pd
rng = np.random.default_rng(9)
ev = pickle.load(open(sys.argv[1], 'rb'))
rows = []
for e in ev:
    if e['is_short']:
        continue
    d = 1.0
    P0 = e['m1'][0][1]
    rows.append(dict(period='IS' if e['open_date'] < pd.Timestamp('2025-01-01', tz='UTC') else 'OOS',
                     day=e['open_date'].normalize(), dow=e['open_date'].dayofweek, fin0=(e['close_rate'] / P0 - 1) * 100))
df = pd.DataFrame(rows)
for per in ('IS', 'OOS', 'TODO'):
    d = df if per == 'TODO' else df[df.period == per]
    wk = d.dow >= 5
    g = {k: v for k, v in d.groupby('day')}
    keys = list(g)
    diffs = []
    for _ in range(3000):
        s = pd.concat([g[keys[i]] for i in rng.choice(len(keys), len(keys), replace=True)])
        w = s.dow >= 5
        if w.sum() and (~w).sum():
            diffs.append(s[~w].fin0.mean() - s[w].fin0.mean())
    print(f'{per:5s} fin de semana n={wk.sum():3d} media {d[wk].fin0.mean():+.2f}% (acierto {(d[wk].fin0>0).mean()*100:.0f}%) | lun-vie n={(~wk).sum():3d} media {d[~wk].fin0.mean():+.2f}% | dif lun-vie menos finde = {d[~wk].fin0.mean()-d[wk].fin0.mean():+.2f} IC95 por dia [{np.percentile(diffs,2.5):+.2f}, {np.percentile(diffs,97.5):+.2f}] | dias finde distintos: {d[wk].day.nunique()}')
=== AN_BE ===
"""
Ideas de gestion: break-even, toma parcial en spike y fin de semana. Solo ESPRING (long) y UPTHRUST (short) por separado.
BE: usa velas de 1h de las 72h completas (datos del laboratorio). Trigger = un high/low de 1h alcanza +X% a favor; despues,
si alguna vela de 1h posterior toca el precio de entrada (P0), sale en P0 (0%, sin contar comisiones extra); si no, sale como siempre.
Es CONSERVADOR: no cuenta lo que ocurre dentro de la misma vela horaria que activa el BE.
"""
import pickle, sys
import numpy as np
import pandas as pd

rng = np.random.default_rng(3)
DATA = '/freqtrade/user_data/data/binance/futures'
ev = pickle.load(open(sys.argv[1], 'rb'))
cache = {}


def h1(pair):
    if pair not in cache:
        base = pair.replace('/USDT:USDT', '')
        cache[pair] = pd.read_feather(f'{DATA}/{base}_USDT_USDT-1h-futures.feather').set_index('date').sort_index()
    return cache[pair]


rows = []
for e in ev:
    d = -1.0 if e['is_short'] else 1.0
    P0 = e['m1'][0][1]
    fin0 = d * (e['close_rate'] / P0 - 1) * 100
    r = dict(side='upthrust' if e['is_short'] else 'spring', period='IS' if e['open_date'] < pd.Timestamp('2025-01-01', tz='UTC') else 'OOS',
             day=e['open_date'].normalize(), dow=e['open_date'].dayofweek, fin0=fin0)
    df = h1(e['pair'])
    w = df.loc[e['open_date']: e['open_date'] + pd.Timedelta(hours=72)]
    hi, lo = w['high'].values, w['low'].values
    fav = (hi / P0 - 1) * 100 if d > 0 else -(lo / P0 - 1) * 100          # mejor excursion a favor por vela
    adv = (lo / P0 - 1) * 100 if d > 0 else -(hi / P0 - 1) * 100          # peor excursion (negativa) por vela
    for X in (1.0, 2.0, 3.0):
        idx = np.where(fav >= X)[0]
        if len(idx) and idx[0] + 1 < len(w):
            back = np.where(adv[idx[0] + 1:] <= 0)[0]
            r[f'be{X}'] = 0.0 if len(back) else fin0
            r[f'be{X}_trig'] = True
            r[f'be{X}_hit'] = bool(len(back))
        else:
            r[f'be{X}'] = fin0
            r[f'be{X}_trig'] = bool(len(idx))
            r[f'be{X}_hit'] = False
    # toma parcial 50% al alcanzar +3.5% en los primeros 60 min (1m)
    m = np.array(e['m1'], dtype=float)
    fav1 = ((m[:60, 2] / P0 - 1) * 100) if d > 0 else (-(m[:60, 3] / P0 - 1) * 100)
    hit = (fav1 >= 3.5).any()
    r['tp_hit'] = bool(hit)
    r['tp'] = 0.5 * 3.5 + 0.5 * fin0 if hit else fin0
    rows.append(r)
df = pd.DataFrame(rows)


def boot_diff(a, b, days, n=1500):
    s = pd.DataFrame({'d': (a - b).values, 'day': days.values})
    g = {k: v['d'].values for k, v in s.groupby('day')}
    keys = list(g)
> plan · deepseek-flash
[0m$ [0mwc -l specs/036-minutos-criticos/brainstorm/*.md; echo ---; sed -n '1,40p' specs/036-minutos-criticos/brainstorm/BRAINSTORM_OPENCODE.md
379 specs/036-minutos-criticos/brainstorm/BRAINSTORM_AGY.md
  364 specs/036-minutos-criticos/brainstorm/BRAINSTORM_OPENCODE.md
  743 total
---
[0m
> plan · deepseek-flash
[0m→ [0mRead README.md 
[0m→ [0mRead audit_data/DATOS_LEEME.md 
[0m→ [0mRead specs/035-auditoria-resultados/VERIFICACION_FILTROS.md 
> plan · deepseek-flash
[0m→ [0mRead audit_data 
[0m→ [0mRead specs/035-auditoria-resultados 
[0m→ [0mRead audit_data/lab_trades/INDEX.md 
> plan · deepseek-flash
[0m→ [0mRead specs/035-auditoria-resultados/AUDIT_MEJORAS.md 
[0m→ [0mRead specs/035-auditoria-resultados/AUDIT_RESULTADOS.md 
> plan · deepseek-flash
[0m→ [0mRead audit_data/strategies/wyckoff_lab.py 
[0m$ [0mls "C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\audit_data\strategies" "C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\audit_data\lab_logs" "C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\specs\035-auditoria-resultados\scripts" "C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\specs\035-auditoria-resultados\scripts_estrategia"
C:\Users\Proyecto Z\Desktop\github\opencode\crypto-signal\audit_data\lab_logs:
LR10_H24_IS_signal.log
LR10_H24_OOS_signal.log
LR15_H24_IS_signal.log
LR15_H24_OOS_signal.log
LR15_H24_SL10_IS_real.log
LR15_H24_SL10_IS_signal.log
LR15_H24_SL10_OOS_real.log
LR15_H24_SL10_OOS_signal.log
LR15_H72_IS_signal.log
LR15_H72_OOS_signal.log
LR15_H72_SL10_IS_real.log
LR15_H72_SL10_IS_signal.log
LR15_H72_SL10_OOS_real.log
LR15_H72_SL10_OOS_signal.log
MR10_H24_IS.log
MR10_H24_OOS.log
MR10_H72_IS.log
MR10_H72_OOS.log
MR15_H24_IS.log
MR15_H24_OOS.log
MR15_H72_IS.log
MR15_H72_OOS.log
MR20_H24_IS.log
MR20_H24_OOS.log
[0m✱ [0mGrep "^#|^\*\*|^[0-9]+\.|Sesion|sesion|funding|CME|opcion|DST|semana|hora|Wall|macro|FOMC|CPI" [90min specs/036-minutos-criticos/brainstorm/BRAINSTORM_OPENCODE.md · 120 matches[0m
> plan · deepseek-flash
He leído el contexto (`audit_data/DATOS_LEEME.md`, `README.md`, `docs/ESTADO_Y_PENDIENTES.md`, `specs/036-minutos-criticos/` y sus `resultado_*.txt`/scripts, `specs/039-springs-perdidos-y-eql/spec.md`) y recorrí `app/` completo. Solo lectura; no modifiqué nada. Aclaro de entrada: crypto-signal es el bot de alertas; Freqtrade es el laboratorio; no asumo tu capital. Hoy en el repo hay **1.385 eventos de spring** (860 IS / 525 OOS) y el operador está en `America/Santiago`.

---

# PARTE A

## Antes de proponer: qué de esto YA está medido y no se repropone

Para no violar la regla del README (lo refutado no se re-propone), dejo fijado lo que **ya tiene veredicto** y solo agrego el ángulo nuevo:

| Área pedida | Estado real (de los archivos) | Qué NO voy a reproponer |
|---|---|---|
| Las 6 velas 4h por separado | **Medido y ruido**: `specs/036.../resultado_m1.txt` §7; README slice 036 "hora UTC son ruido". IS/OOS invierten signo en 08/12/16 (spring) y en 00/12/16 (upthrust). | La tabla de 6 horas crudas. |
| Minutos dentro de la vela | **Medido y ruido** (036). | Recortes de minutos. |
| Fin de semana | **Candidato débil ya registrado** (036 §"Fin de semana"; `resultado_be.txt`: IS −0.27 vs +1.69 lun–vie; OOS −0.83 vs +2.19; IC95 por día `[−0.21, +5.92]`). | El corte sab/dom como filtro nuevo. |
| Hora UTC / ventana funding como filtro | El propio brainstorm de 036 (I14) ya anticipó "probable ruido" por inversión de signo (`AUDIT_MEJORAS`), y 036 lo confirmó. | El corte crudo 00/08/16. |
| Hora del aviso / costo del retraso | **Medido en 039**: ~−0.5 pp por cada 4 h; a 12 h acierto ~47–52%. | El costo del retraso "en general". |

Lo que sigue es **ángulo distinto** sobre el reloj: agregación por sesión, interacción con el mecanismo (clúster), normalización DST, calendario con etiqueta *pre-conocida*, origen de flujo por par, y el lado del operador.

## Tabla ordenada por (valor esperado × P(real)) / costo

| # | Idea | Dirección fijada a priori | P(real) | Costo |
|---|---|---|---|---|
| A1 | Clúster ≥5 pares **× sesión de cierre** | Clúster en sesión líquida (UE–EEUU) > clúster en Asia/valle | Media | Medio |
| A2 | Sesión de cierre agregada en 4 bloques | Sesión líquida (UE–EEUU) > Asia/valle | Baja-Media | Muy bajo |
| A3 | Diagnóstico DST: recortar la hora en hora **local** (Berlín / Nueva York), no UTC | Si el efecto es de sesión, la hora local es más estable IS↔OOS que la UTC | Baja (pero cierra la pregunta) | Muy bajo |
| A4 | Funding 00/08/16 vs resto **condicionado a clúster** | Funding + clúster > no-funding + clúster | Baja | Bajo |
| A5 | Apertura Wall Street 13:30/14:30 UTC (recorte 1 min) | Springs cuyo primer tramo cae justo en el open > fuera | Baja-Media | Medio |
| A6 | Costo del retraso **por hora local Santiago** | Los avisos de madrugada (00–07 local) se ejecutan peor | Media | Bajo-Medio |
| A7 | Continente "dueño" del flujo por par | Un spring en la sesión dominante del par > fuera de ella | Media | Medio-Alto |
| A8 | Fin/inicio de mes (turn-of-month) | Capitulaciones de cierre de mes > mitad de mes | Baja-Media | Bajo |
| A9 | Tapa/reapertura CME y "domingo noche" UTC | Vela que cierra 00:00º lunes (reapertura CME) distinta del resto | Baja | Medio |
| A10 | Vencimiento de opciones (vie 08:00 UTC; mensual/trimestral) | Post-vencimiento el pin se libera → springs mejores | Muy baja (n chico) | Medio |
| A11 | Calendario macro (FOMC/CPI/NFP) por agenda pre-conocida | Springs en ventana post-macro rinden menos (el macro manda) | Baja-Media | Medio |
| A12 | Año Nuevo Chino / feriados de Asia | Springs en sesión Asia en feriado rinden menos | Muy baja (n chico) | Bajo |
| A13 | Lunes (bootstrap limpio por día) | Lunes > resto | Baja (ya se ve inestable) | Muy bajo |
| A14 | Producto: hora local en el aviso + resumen matutino | — (no estadístico) | — | Bajo |
| A15 | Interacción doble: clúster × funding × sesión | Solo exploratorio; alto riesgo de p-hacking | Muy baja | Bajo |
| A16 | "Noche en Santiago": el plan de la alerta debe decirlo | Los avisos de madrugada exigen una instrucción distinta | Media (de producto) | Bajo |

---

### A1 — Clúster ≥5 pares × sesión de cierre  *(el de mayor valor)*
- **Definición operativa**: para cada spring del lab (registro `SpringH72_SL10`, 860 IS/525 OOS), ya existe el conteo de pares con evento en la misma vela (`specs/035`, "pares simultáneos"). Crear dos indicadores: `concurrent>=5` sí/no y `session` = bloque de la hora **UTC de cierre** (ver A2). Comparar media/win a 72 h de `clúster ∧ sesión` contra `clúster` solo.
- **Hipótesis (dirección fija)**: las capitulaciones de todo el mercado ocurren y se *resuelven* mejor en la ventana líquida UE–EEUU; un clúster en Asia rinde menos. Es la única idea que **condiciona el mecanismo conocido** en vez de cortar la hora en crudo, por eso es la primera.
- **Por qué podría ser real**: el edge es beta común (`AUDIT_RESULTADOS.md` §2c); el rebote necesita contraparte que absorba, y la contraparte está en la ventana de EEUU/UE.
- **Cuántos eventos por celda**: **hay que contarlo** (no lo tengo). Advertencia dura: el audit estima **~131 episodios/velas de mercado en IS** (el `n=827` son eventos muy correlacionados, 81% en clústeres de hasta 20–23 pares). Partir esos ~131 días en 4 sesiones deja ~30 días IS por celda; varias celdas quedarán por debajo del mínimo. **Si `clúster≥5` da <30 días por sesión en IS, la idea no es evaluable con este estándar y se declara "no concluyente".**
- **Riesgo de comparaciones múltiples**: alto (2 condiciones × 4 sesiones × 2 direcciones). La corrección por k debe declararse antes.

### A2 — Sesión de cierre agregada en 4 bloques (nuevo: agrega, no trocea)
- **Definición operativa**: asignar cada spring por la hora UTC de **cierre** de la vela de confirmación (la del trade, `open_date`), en 4 bloques disjuntos:
  - `US_tarde` = cierra 20:00 (16–20 UTC)
  - `US_cierre/Asia_abre` = cierra 00:00 (20–00 UTC)
  - `Asia` = cierra 04:00 y 08:00 (00–08 UTC)
  - `Europa/US_open` = cierra 12:00 y 16:00 (08–16 UTC)
- **n reales** (de `resultado_m1.txt` §7, springs): US_tarde **184 IS / 110 OOS**; US_cierre **209 / 102**; Asia **227 / 168**; Europa/US **160 / 112**.
- **Hipótesis (fija)**: `Europa/US_open` y `US_tarde` > `Asia`.
- **Por qué podría ser real**: aunque las 6 horas sueltas son ruido, agrupar por liquidez puede revelar estructura que el troceo destruye (menos comparaciones y celdas más grandes).
- **Riesgo múltiple**: 4 celdas × 2 pruebas (media y win) → k=2 corregido (IC 97.5%) como en 039, o k=3 si se agrega A3 a la misma familia.
- **Honestidad**: la dirección fija choca con lo observado (`US_tarde` IS +0.57 vs `Asia` IS +1.22/+3.29 mezclado). Es una apuesta a que la agrupación por liquidez ordena lo que la hora suelta no; puede fallar rápido y barato.

### A3 — Normalización DST (diagnóstico, no nueva señal)
- **Definición**: repetir exactamente el corte de las 6 velas de 036 (`analysis_m1.py` §7) pero agrupando por la hora **local** de `Europe/Berlin` y de `America/New_York` (con `pytz`, DST resuelto por instante), además de UTC.
- **Hipótesis (fija)**: si detrás de la "hora" hay una sesión, la hora local debe mostrar menos inversión de signo IS↔OOS que la UTC; si no hay diferencia, el corte UTC es ruido puro y se cierra la línea para siempre.
- **Por qué podría ser real**: DST mueve todas las sesiones 1 h en UTC dos veces por año; un corte en UTC mezcla dos regímenes horarios. Es la forma correcta de descartar contaminación.
- **n**: los mismos 780 IS / 492 OOS, sin pérdida.
- **Costo**: ~1–2 h (es un `groupby` distinto sobre datos ya bajados).
- **Riesgo múltiple**: bajo si se plantea como diagnóstico; no se "elige" la mejor normalización.

### A4 — Funding 00/08/16 condicionado a clúster
- **Definición**: `funding_hour = close∈{00,08,16}` vs `{04,12,20}`; IS: 445 vs 335, OOS: 250 vs 242. Probar (a) crudo (ya implícitamente refutado por 036) y (b) **dentro de `concurrent≥5`**.
- **Hipótesis (fija)**: springs de clúster que cierran en hora de funding rinden más (liquidaciones forzadas + pago de funding).
- **Por qué podría ser real**: el funding marca liquidaciones; el crudo ya invirtió signo, pero condicionado al clúster es un subconjunto no medido.
- **Advertencia honesta**: es re-cortar datos ya refutados; solo el subconjunto clúster lo justifica.

### A5 — Apertura de Wall Street (13:30/14:30 UTC según DST de EEUU)
- **Definición**: con las velas de 1 min ya bajadas en 036, marcar los eventos cuyo tramo [P0, P0+60min] cruza 13:30 UTC (invierno EEUU) o 14:30 UTC (verano EEUU). Comparar media a 72 h y MAE de los primeros 60 min.
- **Hipótesis (fija)**: el impulso de la apertura de acciones "confirma o desmiente" el spring → los que cruzan el open rinden peor si el open es adverso.
- **Por qué podría ser real**: flujo de acciones (ETF/mineras) entra a esa hora; es un evento anclado no alineado a la grilla 4h.
- **n**: subconjunto de los 780/492; calcular cuántos caen en esa franja (probablemente 15–25%).
- **Riesgo**: el horario de EEUU cambia dos veces por año → dos reglas fijas (13:30/14:30), no una; declararlas antes.

### A6 — Costo del retraso por hora local Santiago  *(alto valor para el operador)*
- **Definición**: sobre los 860/525 del lab y el `delay_cost.py` de 039, agrupar el costo de entrar a +4/8/12 h según la hora local Santiago del **cierre**. Comparar el costo del retraso en "madrugada Santiago" (≈00–07) vs "horario despierto".
- **Hipótesis (fija)**: los eventos que cierran de madrugada Santiago tienen mayor MAE overnight y el retraso cuesta más que el promedio −0.5 pp/4 h.
- **Por qué podría ser real**: el mercado europeo/americano mueve más en la madrugada chilena; el operador duerme y entra tarde.
- **n**: mismo total, pero 4 franjas → ~200 IS/130 OOS por franja de 6 h; aceptable.
- **Múltiple**: k=4.
- **Uso directo**: decidir si el aviso de madrugada debería traer una instrucción distinta (ver A16).

### A7 — Continente "dueño" del flujo por par
- **Definición**: con velas 1h de futuros, calcular para cada par la fracción de volumen en 3 franjas (Asia 00–07, Europa 07–13, EEUU 13–21 UTC) sobre 2022–2026; clasificar cada par como "asiático/occidental" por su pico. Marcar cada spring `in_dominant_session` sí/no.
- **Hipótesis (fija)**: un spring en la sesión dominante del par revierte mejor que uno fuera (hay manos locales para absorber).
- **Por qué podría ser real**: hay pares (p. ej. asiáticos) cuyo volumen real ocurre en Asia; el spring fuera de su sesión puede ser iliquidez, no absorción.
- **n**: se parte por par → celdas chicas; puede no llegar a 30 días.
- **Costo**: medio-alto (construir el perfil de volumen).

### A8 — Turn-of-month
- **Definición**: `fin_inicio_mes` = últimos 3 y primeros 3 días del mes (UTC), vs resto. Comparar media/win a 72 h.
- **Hipótesis (fija)**: capitulaciones de cierre de mes (rebalanceos/flujos) rebotan mejor.
- **n**: ~20% de 1385 ≈ 277 eventos, ~170 IS; aceptable.
- **Múltiple**: k=1 si se fija la ventana (3+3) antes.

### A9 — Tapa/reapertura de CME y "domingo noche"
- **Definición**: aislar la vela que cierra **lunes 00:00 UTC** (abre domingo 20:00, contiene la reapertura de CME a las 22:00/23:00 UTC) y la que cierra **viernes 20:00 UTC** (contiene el cierre del CME). Comparar con el resto.
- **Hipótesis (fija)**: la vela de reapertura de CME del domingo tiene comportamiento de hueco y rinde distinto (peor) que un lunes normal.
- **Ojo**: esa vela hoy se clasifica **weekday** (lunes) por `_is_weekend_close`, así que no está capturada por el candidato de fin de semana ya medido.
- **n**: ~1 vela/semana → ~150 IS / 90 OOS, pero solo ~30/18 son lunes-00; borderline.

### A10 — Vencimiento de opciones
- **Definición**: marcar springs que cierran en la vela de 08:00 UTC de un viernes (vencimiento semanal Deribit) y separar mensual/trimestral (tercer viernes). Comparar.
- **Hipótesis (fija)**: tras el vencimiento se libera el "pin" → mejores rebotes.
- **n**: muy chico (mensual ~36 IS / ~20 OOS; trimestral ~12). **Poder insuficiente; probablemente no concluyente.**
- **Costo**: bajo si se obtiene la lista de fechas (se puede construir a mano, sin red).

### A11 — Calendario macro (FOMC / CPI / NFP)
- **Definición y etiquetado SIN mirar el futuro**: la agenda es **pre-conocida** (fechas/horas publicadas con antelación), así que etiquetar un evento por "cae en las 4–8 h siguientes a un comunicado" no usa información futura. Se necesita un archivo histórico de fechas/horas (FOMC 18:00/19:00 UTC; CPI y NFP 12:30/13:30 UTC), curado a mano una vez.
- **Hipótesis (fija)**: springs que confirman en la ventana post-macro rinden menos (el macro manda sobre el patrón).
- **Por qué podría ser real**: capitulaciones macro-driven pueden seguir, no revertir.
- **n**: CPI mensual + NFP mensual + FOMC ~8/año → ~50–60 días macro en 4.75 años → pocos eventos; **riesgo de no concluyente**.
- **Riesgo**: si se elige la ventana después de ver resultados, es p-hacking; fijar 4 h y 8 h antes.

### A12 — Año Nuevo Chino / feriados de Asia
- **Definición**: springs en la sesión Asia durante la semana del CNY (fechas lunares, pre-conocidas). 
- **Hipótesis (fija)**: liquidez asiática ausente → peor.
- **n**: mínima; solo exploratorio.

### A13 — Lunes, limpio
- **Definición**: bootstrap por día de "lunes vs resto" con el estándar completo (036 solo hizo weekend vs lun–vie).
- **Hipótesis (fija)**: lunes rebota más.
- **Honestidad**: los datos ya muestran inestabilidad (lun IS +4.27 vs OOS +2.95; mar IS −1.50 vs OOS +2.05; mié +2.53 vs +7.84). Esperaría ruido; barato descartarlo.

### A14 — Producto: hora local + resumen matutino (no estadístico)
- **Qué**: agregar la hora local Santiago al aviso (ver PARTE B, texto propuesto) y, opcionalmente, un resumen a una hora fija de Santiago (p. ej. 08:00) con las alertas de la madrugada. No es un edge; es reducir el error humano.
- **Por qué**: el costo del retraso ya medido (~0.5 pp/4 h) se paga sobre todo cuando el aviso llega mientras dormís.
- **Cómo evaluarlo**: usabilidad (¿actuaste distinto?), no p-valor; nunca prometer rendimiento.

### A15/A16 — Interacciones y "noche en Santiago"
- **A15**: clúster × funding × sesión son 12+ celdas sobre pocos días efectivos → **alto riesgo de falso positivo**; solo como exploratorio descriptivo, nunca como filtro.
- **A16**: si A6 confirma que la madrugada cuesta más, el mensaje debería decirlo explícitamente (p. ej. "alerta de madrugada: el plan sigue siendo el mismo, pero el retraso medido aquí es mayor").

## Criterio de aprobación concreto para las 3 mejores (A1, A2, A3)

Se fija **antes** de correr y es el mismo estándar del proyecto, con las celdas chicas tratadas con dureza:

1. **Datos y herramienta**: eventos de spring del lab (`SpringH72_SL10`, señal: 860 IS / 525 OOS), klines 4h de futuros 2021+ y funding real; reusar `wyckoff_lab.wyckoff_events()` como en 036. IS = 2022–24, OOS = 2025–26.
2. **Pre-registro**: escribir en `spec.md` la dirección fija, los puntos de corte y `k` (familia de comparaciones) **antes** de mirar números.
3. **Consistencia**: la diferencia (celda − baseline) debe tener **el mismo signo en IS y OOS** y, para un filtro, mejorar la media en **ambos**.
4. **Bootstrap por día** sobre la muestra unida (los eventos comparten vela), 5.000 remuestreos, IC de dos colas al nivel `1 − 0.05/k`. Para el top-3 como familia: k=3 → IC **98.33%** (cuantiles 0.0083 / 0.9917). Reportar el `k` explícitamente.
5. **Tamaño de efecto mínimo**: `|dif| ≥ 0.5 pp` vs baseline (la unidad que ya te importa: el costo de 4 h de retraso), además del win-rate. Un efecto significativo de +0.1 pp no se lleva al bot.
6. **Poder mínimo**: **≥ 30 días distintos** (no eventos) por celda y período. Si no llega → "no concluyente", y **no se actúa** aunque el signo guste.
7. **Si aprueba**: no filtra ni cambia el gate de la alerta; se **muestra y registra** como hipótesis hasta ≥50 alertas reales maduras (regla de 039/040).
8. **Se descarta** si: el signo cambia entre IS y OOS, el IC incluye 0, una celda tiene <30 días, o (para A3) el efecto desaparece al normalizar por DST.

---

# PARTE B

Método: `grep` de `datetime|timezone|utc|astimezone|timestamp|pytz|zoneinfo|dayofweek|weekday|strftime|isoformat|sleep|update_interval|schedule` en `app/`, y lectura de cada uso. No leí `.env` ni `config.yml` (usé `config-clean.yml`).

## Hallazgos

### B1 — `settings.timezone` NO llega al builder: `creation_date` sale siempre en UTC  · Severidad: MEDIA
- **Archivo:línea**: `app/notifications/core.py:37` (construye `MessageBuilder(self.logger, self.market_data)` → `timezone_str` default `'UTC'`) y `:84-86` (`set_timezone` actualiza `self.chart_renderer.timezone_str` **pero no** `self.builder.timezone_str`). Consumo en `app/notifications/builder.py:19-22` y `:184-185`.
- **Escenario de fallo**: con `timezone: America/Santiago`, el **título del gráfico** sí sale en hora de Santiago, pero el `📅 {{creation_date}}` del mensaje de Telegram detallado sale en UTC. Dos mensajes del mismo ciclo muestran horas distintas. Para un cierre 16:00 UTC, en invierno verías "16:00" cuando son las 12:00 en Santiago.
- **Arreglo mínimo**: en `set_timezone` agregar `self.builder.timezone_str = timezone` (o pasar el TZ al construir el builder).
- **Nota**: esto solo afecta a los mensajes heredados de indicadores; la alerta Wyckoff (el edge) no usa `creation_date` (ver B2). Test actual (`tests/notifications/test_builder.py:91`) solo verifica que el código menciona `timezone(self.timezone_str)`, no que se propague.

### B2 — La alerta Wyckoff/radar no muestra ninguna hora  · Severidad: MEDIA
- **Archivo:línea**: `app/analysis/wyckoff_alerts.py:437-447` (mensaje spring/upthrust) y `:333-346` (radar). El mensaje no tiene ni hora UTC ni local; solo, si aplica, `_stale_notice` (`:376-386`).
- **Escenario de fallo**: con `MAX_LATE_CANDLES=3`, un aviso puede referirse a una vela cerrada hasta 12 h antes; y tras un reinicio el operador no puede distinguir "vela nueva" de "vela ya avisada". No hay forma de saber a qué vela corresponde el aviso mirando el mensaje.
- **Arreglo propuesto (texto exacto)**: agregar una línea calculada con `pytz` (ya es dependencia; ver B6):
  ```
  🕐 Vela 4h: 12:00–16:00 UTC · cerró 16:00 UTC = 12:00 en Santiago (hace 7 min)
  ```
  y para tardías (reemplaza/complementa el recuadro actual):
  ```
  🕐 Vela 4h: 04:00–08:00 UTC · cerró 08:00 UTC = 04:00 en Santiago (hace 8.1 h)
  ⏱️ ALERTA RETARDADA: el bot estuvo sin revisar. Cada 4 h de demora cuesta ~0.5 pp; a 12 h el acierto baja a ~47-52%.
  ```
  Implementarlo en un helper `_candle_label(timestamp)` para no repetir lógica.

### B3 — Los logs no tienen timestamp (modo `text`/`json`, que es el default)  · Severidad: MEDIA (auditoría)
- **Archivo:línea**: `app/logs.py:23-35` (formatters `'%(message)s'` sin `asctime`) y `:53-63` (los `structlog` processors no incluyen `TimeStamper`).
- **Escenario de fallo**: `docker logs crypto-signal` no permite reconstruir la hora en que salió cada alerta; el "aviso ~7 min después del cierre" y el caso "PC apagada" son **no auditables** desde el log. El único timestamp vive en `rumor_radar.jsonl` (`recorded_at`).
- **Arreglo mínimo**: agregar `structlog.processors.TimeStamper(fmt='iso', utc=True)` a los processors (UTC explícito) o incluir `asctime` en el formatter.

### B4 — `drop_unclosed_candle` confía en el reloj del host sin margen ni chequeo de alineación  · Severidad: MEDIA-ALTA
- **Archivo:línea**: `app/data/manager.py:52-64` (`now_utc = datetime.now(timezone.utc)`), usado en `app/behaviour/data.py:92-94` (camino principal del pipeline) y `app/data/manager.py:266`.
- **Escenario de fallo**: el contenedor usa el reloj del **host Windows** (VM/reanudación puede adelantarse). Si el reloj va **adelantado** > cierre real, la última vela en formación pasa la prueba `last_candle_close_ms > now_ms` como **cerrada** → se calculan indicadores/Wyckoff sobre una vela que aún se mueve → **repintado** (viola el Principio II, justo lo que el proyecto protege). Si va atrasado, descarta una vela cerrada (mitigado por `MAX_LATE_CANDLES`). No hay aserción de que el `timestamp` de la última vela esté alineado a la grilla de 4 h.
- **Arreglo mínimo**: anclar al tiempo del exchange (`ccxt.fetch_time`/`fetch_status`) en vez del reloj local, o exigir un margen (p. ej. descartar la última vela si `now_ms − close_ms < margen`) y validar `timestamp % 14400 == 0`.

### B5 — Fin de semana definido en UTC, operador en Santiago; "domingo noche" cae como lunes  · Severidad: BAJA
- **Archivo:línea**: `app/analysis/wyckoff_alerts.py:388-393`.
- **Escenario**: la vela que abre 20:00 UTC viernes cierra 00:00 UTC sábado → se marca "fin de semana" aunque en Santiago son las 20:00/21:00 del viernes. La vela de reapertura de CME (abre domingo 20:00, cierra lunes 00:00) se clasifica **weekday**. Es **consistente con el backtest** (`specs/036.../analysis_be.py` usa `open_date.dayofweek`), así que no es un error estadístico, pero puede confundir al operador.
- **Arreglo mínimo**: aclarar el texto ("sáb/dom **UTC**") o mostrar el día local junto al UTC.

### B6 — Contenedor sin TZ y sin `tzdata` del sistema  · Severidad: BAJA (de implementación)
- **Archivo:línea**: `Dockerfile:1-30` (no hay `ENV TZ`); `docker-compose.yml` tampoco.
- **Estado real**: `python:3.12-slim` arranca con reloj/zonas en UTC. `pytz` trae su propia base de zonas, por lo que `timezone('America/Santiago')` funciona sin `tzdata` del SO. **Cuidado**: si para B2/A14 se usa `zoneinfo.ZoneInfo` (stdlib), la imagen slim puede no tener `tzdata` → error de zona. Usar `pytz` (ya instalado) o agregar `tzdata` al `Dockerfile`.
- El DST de Chile o del host Windows **no rompe** nada crítico: el código decide en UTC; solo la presentación usa local.

### B7 — Conteo de concurrency por pares se subcuenta si hay >1 worker  · Severidad: BAJA-MEDIA (config-dependente)
- **Archivo:línea**: `app/app.py:103-127` (`market_data_chunk_size`) vs `app/analysis/wyckoff_alerts.py:148-178` (`check_cycle`/`_count_concurrent` por instancia). Cada `Behaviour` tiene su propio `WyckoffAlerter`; con `top_n > chunk_size` hay varios workers y `concurrent_pairs` solo cuenta la mitad del mercado. Hoy con `top_n:20` y `chunk_size:20` hay 1 worker, así que no se manifiesta; si subís `top_n`, el "Pares con evento en esta misma vela" del mensaje queda mal.

### B8 — Imports de tiempo muertos  · Severidad: COSMÉTICA
- `app/analysis/strategy_analyzer.py:5` importa `datetime` sin usarlo; `app/notifications/queue.py:21` importa `datetime, timedelta` sin usarlos (usa `time.time()`). No afecta nada.

## Lo que está bien (una línea cada uno)

- **UTC de punta a punta en las decisiones**: no queda ningún `datetime.now()` naive; `drop_unclosed_candle`, `_stale_notice`, `_is_weekend_close`, dedup, anti-spam y registros usan instantes UTC-aware (`app/data/manager.py:53`, `app/analysis/wyckoff_alerts.py:373-393`, `app/notifications/builder.py:34,59`). Coincide con specs 002/003/006.
- **`_calculate_start_date`** (`app/exchanges/driver.py:154-159`) usa `datetime.now(timezone.utc)`: correcto y sin depender del TZ del host.
- **Clasificación de fin de semana** = `(apertura + 4 h).dayofweek`, que es exactamente el `open_date.dayofweek` del backtest (`analysis_be.py:30`, `analysis_m1.py:28`).
- **Dedup y ventana de springs perdidos**: `MAX_LATE_CANDLES=3` cubre bien las 4 últimas velas (`_recent_events`, `:184-199`), y la firma por `timestamp.isoformat()` es estable entre reinicios vía `rumor_radar.jsonl` (`:108-127`).
- **Relojes de terceros coherentes**: `mention_velocity` (`twitter_sentiment.py:80-103`) usa `now` UTC y `until_time` en segundos; `_mentions_per_hour` (`:137-150`) parsea `createdAt` con `%z` (aware) y resta aware−aware → seguro ante DST. Open interest 24 h y ratio long/short usan las últimas filas sin zona. No encontré incoherencia.
- **DST de Chile/EU/US no contamina ningún corte** porque las decisiones son UTC; la hora local solo aparece en presentación (título de gráfico y `creation_date`).
- **`update_interval: 300`** con 20 pares y 1 worker es coherente con el aviso observado (~6:46 min para la vela 12:00: `bot_alertas_registro.jsonl:9`, 16:06:46). No es bug; solo notar que subir `update_interval` atrasa el aviso y que `start_worker_interval: 60` escalona workers.
- **`time.time()`** (cachés, ventana de duplicado, heartbeat) es época Unix: inmune al TZ.

## Los 3 experimentos de horario que yo correría primero

1. **A2+A3 juntos** — sesión de cierre en 4 bloques + recorte de la hora en **hora local** (Berlín/Nueva York) para descartar/confirmar contaminación DST. Es baratísimo y cierra definitivamente la pregunta "¿hora importa?" que 036 dejó en ruido.
2. **A1 — clúster ≥5 × sesión**. Es el único que condiciona el mecanismo real del edge (capitulación de mercado). Antes de correrlo, **contar los días por celda**; si quedan <30 días por sesión, se archiva como no concluyente sin gastar más.
3. **A6 — costo del retraso por hora local Santiago**. Tiene valor directo para vos: dice si un aviso de madrugada debería traer otra instrucción (A16) y reusa exactamente los datos de 039.

## Los 3 bugs de reloj más graves

1. **B4** — `drop_unclosed_candle` depende del reloj del PC Windows sin margen ni alineación → riesgo de tratar una vela en formación como cerrada (**repintado**, Principio II). `app/data/manager.py:52-64`.
2. **B1** — `settings.timezone` nunca se propaga al `MessageBuilder`: `creation_date` siempre en UTC, mientras el gráfico del mismo ciclo sale en Santiago. `app/notifications/core.py:37,84-86` + `app/notifications/builder.py:184-185`.
3. **B2** (y su hermano B3) — la alerta Wyckoff y los logs no muestran ninguna hora, así que no se puede saber a qué vela corresponde un aviso ni auditar el retraso real. `app/analysis/wyckoff_alerts.py:437-447` y `app/logs.py:23-35`.
