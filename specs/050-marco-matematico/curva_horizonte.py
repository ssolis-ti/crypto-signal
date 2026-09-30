"""
Curva de retorno acumulado por horizonte de la canasta de springs en dias de capitulacion amplia (medicion descriptiva, sin criterio de aprobacion).
Responde con datos: ¿el rebote es rapido o lento?, ¿72 h es un buen horizonte?, ¿cuanto de la ganancia ya esta en 24/48 h?
Cada spring: entrada a la apertura de t (columna t de events_universo.csv), retorno acumulado en cada vela de 4h hasta 30 velas (120 h), con el stop -10% sobre minimos
(una vez tocado el retorno queda fijo en -10% - comision), comision 0.1%. Episodio = media de los springs de ese dia amplio (>= 20% de los pares).
"""
import glob, os
import numpy as np
import pandas as pd

DATA = '/freqtrade/user_data/data/binance/futures'
DELISTED = '/work043/data_delisted'
STOP, FEE, H = -10.0, 0.1, 30
rng = np.random.default_rng(51)

ev = pd.read_csv('/exp044/events_universo.csv', parse_dates=['conf', 't'])
ev['t'] = pd.to_datetime(ev.t, utc=True)
w = ev[ev.frac >= 0.20].copy()

series = {}
for p in glob.glob(f'{DATA}/*_USDT_USDT-4h-futures.feather'):
    series[os.path.basename(p).split('_USDT_USDT')[0]] = pd.read_feather(p).set_index('date').sort_index()
for p in glob.glob(f'{DELISTED}/*.pkl'):
    series['D_' + os.path.basename(p)[:-8]] = pd.read_pickle(p)

paths, meta = [], []
for r in w.itertuples():
    df = series.get(r.sym)
    if df is None or r.t not in df.index:
        continue
    e = df.index.get_loc(r.t)
    if e + H > len(df):
        continue
    entry = df['open'].iloc[e]
    lows = df['low'].values[e:e + H]
    closes = df['close'].values[e:e + H]
    cum = (closes / entry - 1) * 100
    stopped = np.maximum.accumulate(lows <= entry * (1 + STOP / 100))
    cum = np.where(stopped, STOP, cum) - FEE
    paths.append(cum)
    meta.append((r.t.normalize(), r.t))
P = np.array(paths)
m = pd.DataFrame(meta, columns=['day', 't'])
m['period'] = np.where(m.t < pd.Timestamp('2025-01-01', tz='UTC'), 'IS', 'OOS')
days = m.day.unique()
print(f'springs en dias amplios con {H} velas de datos: {len(P)} | dias: {len(days)}')

# canasta por dia: media de los springs del dia en cada horizonte
D = np.array([P[(m.day == d).values].mean(axis=0) for d in days])           # (dias, H)
pers = np.array([m[m.day == d].period.iloc[0] for d in days])
hours = (np.arange(H) + 1) * 4


def ci(col):
    res = [D[rng.integers(0, len(D), len(D))][:, col].mean() for _ in range(2000)]
    return np.percentile(res, [2.5, 97.5])


print(f"\n{'horizonte':>10s} | {'media dias':>10s} {'IC95':>17s} | {'mediana':>7s} {'%dias>0':>7s} | {'2022-24':>8s} {'2025-26':>8s}")
for col in (0, 1, 2, 3, 5, 7, 9, 11, 14, 17, 20, 23, 29):
    lo, hi = ci(col)
    print(f"{hours[col]:8d} h | {D[:, col].mean():+10.2f} [{lo:+6.2f},{hi:+6.2f}] | {np.median(D[:, col]):+7.2f} {(D[:, col] > 0).mean()*100:6.0f}% | {D[pers == 'IS', col].mean():+8.2f} {D[pers == 'OOS', col].mean():+8.2f}")

mean_curve = D.mean(axis=0)
best = int(np.argmax(mean_curve))
print(f'\nmaximo de la curva media: {hours[best]} h ({mean_curve[best]:+.2f}%); a 72 h: {mean_curve[17]:+.2f}%; a 24 h: {mean_curve[5]:+.2f}%; a 48 h: {mean_curve[11]:+.2f}%; a 120 h: {mean_curve[29]:+.2f}%')
print(f'fraccion de la ganancia a 72 h ya presente a 24 h: {mean_curve[5] / mean_curve[17]:.0%} | a 48 h: {mean_curve[11] / mean_curve[17]:.0%}')
# ajuste OU/exponencial: X(h) = A (1 - exp(-h/tau)) sobre la curva media (descriptivo)
from scipy.optimize import curve_fit
f = lambda h, A, tau: A * (1 - np.exp(-h / tau))
try:
    (A, tau), _ = curve_fit(f, hours.astype(float), mean_curve, p0=[3.0, 30.0], maxfev=10000)
    resid = mean_curve - f(hours, A, tau)
    print(f'ajuste exponencial de saturacion: A={A:+.2f}% tau={tau:.1f} h (media-vida {tau * np.log(2):.1f} h) | RMSE {np.sqrt((resid ** 2).mean()):.3f}')
except Exception as e:
    print('sin ajuste exponencial:', e)
# diferencias pareadas por dia entre horizontes (IC95 por dia)
for a_, b_ in ((5, 17), (11, 17), (17, 29)):
    diff = D[:, b_] - D[:, a_]
    res = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(3000)]
    lo, hi = np.percentile(res, [2.5, 97.5])
    print(f'  retorno a {hours[b_]} h menos retorno a {hours[a_]} h (pareado por dia): {diff.mean():+.2f} pp IC95 [{lo:+.2f}, {hi:+.2f}] | sd de la diferencia {diff.std(ddof=1):.2f}')
print(f'\nCORRELACION entre el retorno a 24 h y a 72 h (por dia): {np.corrcoef(D[:, 5], D[:, 17])[0, 1]:.2f}; entre 48 h y 72 h: {np.corrcoef(D[:, 11], D[:, 17])[0, 1]:.2f}')
q = np.percentile(D[:, 17], [5, 10, 25, 50, 75, 90, 95])
print('cuantiles de la media diaria a 72 h (5,10,25,50,75,90,95):', np.round(q, 2).tolist(), '| asimetria:', round(float(pd.Series(D[:, 17]).skew()), 2), '| curtosis exceso:', round(float(pd.Series(D[:, 17]).kurt()), 2))


pd.DataFrame({'day': days, 'ret72': D[:, 17], 'ret24': D[:, 5], 'ret48': D[:, 11], 'period': pers,
              'n_springs': [int((m.day == d).sum()) for d in days]}).to_csv('/exp/basket_diario_72h.csv', index=False)
print('guardado basket_diario_72h.csv')
