"""
Instrumento en dias de capitulacion amplia (>= 20% de los pares con spring; seguimiento exploratorio de spec 044, idea de
opencode E2). Episodio = primera vela de cada grupo de senales dentro de 72h (unidad no solapada). Se compara, con las mismas
reglas (entrada apertura siguiente, 72h, stop -10% sobre minimos, 0.1% comision):
  - canasta de los springs de esa vela (lo que el bot avisa, tomando todos)
  - BTC solo, ETH solo, y BTC+ETH
  - control: BTC/ETH en cualquier vela (deriva del mercado)
Pocos episodios: es descriptivo, no un filtro.
"""
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
HOLD, STOP, FEE = 18, -10.0, 0.1
SPLIT = pd.Timestamp('2025-01-01', tz='UTC')
rng = np.random.default_rng(48)
ev = pd.read_csv('/exp044/events_universo.csv', parse_dates=['conf', 't'])
ev['t'] = pd.to_datetime(ev.t, utc=True)
ev['conf'] = pd.to_datetime(ev.conf, utc=True)


def load(base):
    return pd.read_feather(f'{DATA}/{base}_USDT_USDT-4h-futures.feather').set_index('date').sort_index()


def sim(df, t):
    if t not in df.index:
        return np.nan, np.nan
    e = df.index.get_loc(t)
    if e + HOLD > len(df):
        return np.nan, np.nan
    entry = df['open'].iloc[e]
    stopped = (df['low'].iloc[e:e + HOLD] <= entry * (1 + STOP / 100)).any()
    r = STOP if stopped else (df['close'].iloc[e + HOLD - 1] / entry - 1) * 100
    return r - FEE, float(stopped)


btc, eth = load('BTC'), load('ETH')
wide = ev[ev.frac >= 0.20]
ts = sorted(wide.t.unique())
eps, last = [], None
for t in ts:
    t = pd.Timestamp(t)
    if last is None or (t - last) > pd.Timedelta(hours=72):
        eps.append(t)
    last = t
rows = []
for t in eps:
    basket = wide[wide.t == t]
    rb, sb = sim(btc, t)
    re_, se = sim(eth, t)
    rows.append(dict(t=t, day=t.normalize(), period='IS' if t < SPLIT else 'OOS', n_springs=len(basket), frac=basket.frac.iloc[0],
                     basket=basket.ret.mean(), btc=rb, eth=re_, btc_stop=sb, eth_stop=se))
d = pd.DataFrame(rows).dropna(subset=['btc', 'eth'])
d['btc_eth'] = (d.btc + d.eth) / 2
print(f'episodios de capitulacion amplia (>= 20% de los pares, no solapados): {len(d)} | dias {d.day.nunique()} | 2022-24: {(d.period == "IS").sum()}, 2025-26: {(d.period == "OOS").sum()}')

# control: media incondicional de BTC/ETH en cualquier vela 2022-26
uncond = {}
for name, df in (('btc', btc), ('eth', eth)):
    vals = [sim(df, t)[0] for t in df.index[(df.index >= '2022-01-01') & (df.index <= '2026-09-01')][::6]]
    uncond[name] = np.nanmean(vals)
print(f"control (media en cualquier vela): BTC {uncond['btc']:+.2f}%  ETH {uncond['eth']:+.2f}%")

print(f"\n{'instrumento':22s} | {'2022-24 media':>13s} {'acierto':>7s} | {'2025-26 media':>13s} {'acierto':>7s} | {'unido':>6s} {'acierto':>7s} {'stop':>5s}")
for col, label in (('basket', 'canasta de springs'), ('btc', 'BTC'), ('eth', 'ETH'), ('btc_eth', 'BTC+ETH')):
    a, b = d[d.period == 'IS'][col], d[d.period == 'OOS'][col]
    stop = ''
    if col in ('btc', 'eth'):
        stop = f"{d[col + '_stop'].mean()*100:4.0f}%"
    print(f"{label:22s} | {a.mean():+13.2f} {(a > 0).mean()*100:6.0f}% | {b.mean():+13.2f} {(b > 0).mean()*100:6.0f}% | {d[col].mean():+6.2f} {(d[col] > 0).mean()*100:6.0f}% {stop:>5s}")


def boot(x, col, base, n=3000):
    days = x.day.unique(); g = {k: v for k, v in x.groupby('day')}
    res = [pd.concat([g[days[i]] for i in rng.integers(0, len(days), len(days))])[col].mean() - base for _ in range(n)]
    return np.percentile(res, [2.5, 97.5])


print('\nEXCESO sobre la media incondicional (IC95 por dia, unido)')
for col, base, label in (('btc', uncond['btc'], 'BTC'), ('eth', uncond['eth'], 'ETH')):
    lo, hi = boot(d, col, base)
    print(f'  {label}: {d[col].mean() - base:+.2f} pp  [{lo:+.2f}, {hi:+.2f}]')
print('\nEpisodios (los ultimos 12):')
print(d.tail(12)[['t', 'n_springs', 'frac', 'basket', 'btc', 'eth']].round(2).to_string(index=False))


lo, hi = boot(d, 'basket', 0.0)
print(f'Canasta de springs en dias de capitulacion amplia: media {d.basket.mean():+.2f}%  IC95 por dia [{lo:+.2f}, {hi:+.2f}]  (n={len(d)} episodios)')
for per in ('IS', 'OOS'):
    x = d[d.period == per]
    lo, hi = boot(x, 'basket', 0.0)
    print(f'  {per}: n={len(x)} media {x.basket.mean():+.2f}%  IC95 [{lo:+.2f}, {hi:+.2f}]  acierto {(x.basket > 0).mean()*100:.0f}%')
