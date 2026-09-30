"""Componentes de varianza dia/par de los springs en dias de capitulacion amplia (para calibrar modelos jerarquicos con datos reales)."""
import numpy as np
import pandas as pd

ev = pd.read_csv('/exp044/events_universo.csv', parse_dates=['conf', 't'])
ev['t'] = pd.to_datetime(ev.t, utc=True)
w = ev[ev.frac >= 0.20].copy()
w['day'] = w.t.dt.normalize()
days = w.groupby('day').ret.agg(['mean', 'std', 'count'])
print('springs en dias amplios:', len(w), '| dias:', len(days), '| springs por dia: mediana', int(days['count'].median()),
      'p10', int(days['count'].quantile(.1)), 'p90', int(days['count'].quantile(.9)))
within = np.average(days['std'].fillna(0) ** 2, weights=np.maximum(days['count'] - 1, 1))
between_obs = days['mean'].var(ddof=1)
mbar = days['count'].mean()
tau2 = max(0, between_obs - within / mbar)
print(f'media general {w.ret.mean():+.2f}% | sd total {w.ret.std():.2f}')
print(f'varianza DENTRO del dia sigma^2 = {within:.1f} (sd {np.sqrt(within):.2f} pp)')
print(f'varianza de las medias diarias = {between_obs:.1f}; componente ENTRE dias tau^2 = {tau2:.1f} (sd {np.sqrt(tau2):.2f} pp)')
print(f'ICC (parte de la varianza que es del dia) = {tau2 / (tau2 + within):.2f}')
print(f'sd de la media diaria = {days["mean"].std():.2f} pp -> SE con {len(days)} dias = {days["mean"].std() / np.sqrt(len(days)):.2f} pp')
print('media diaria: p10 %.2f  p50 %.2f  p90 %.2f | dias con media<0: %.0f%%' % (days['mean'].quantile(.1), days['mean'].median(), days['mean'].quantile(.9), (days['mean'] < 0).mean() * 100))
sf = (days['count'] * tau2) / (days['count'] * tau2 + within)
print(f'factor de contraccion del efecto-dia (empirical Bayes): mediana {sf.median():.2f}, p10 {sf.quantile(.1):.2f}, p90 {sf.quantile(.9):.2f}')
# efecto par: cuantos episodios por simbolo
per = w.groupby('sym').size()
print(f'simbolos distintos: {len(per)} | episodios por simbolo: mediana {int(per.median())}, max {int(per.max())}')
# tamano y ARL del CUSUM de agy con sus numeros
mu1, mu0, sd = 2.23, 0.0, days['mean'].std()
k = (mu1 + mu0) / 2
h = sd ** 2 / (mu1 - mu0) * np.log(100)
print(f'\nCUSUM (unidades % por episodio): k={k:.3f}, sd episodio={sd:.2f}, h(ARL0=100 segun agy)={h:.1f}')
print(f'  deriva bajo edge muerto (mu=0): +{k - mu0:.3f} por episodio -> tiempo minimo a h: {h / (k - mu0):.1f} episodios (sin ruido)')
