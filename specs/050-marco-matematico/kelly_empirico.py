"""
Kelly EMPIRICO con incertidumbre por remuestreo de dias (sin multiplicadores heuristicos).
g(f) = mean_d ln(1 + f * R_d/100) sobre los 49 dias de capitulacion amplia (R_d = retorno a 72h de la canasta de springs, con stop -10% por par).
- f* = argmax g(f).  Incertidumbre: bootstrap por dia -> distribucion de f*.  Validacion honesta: f* calibrado con 2022-24, evaluado en 2025-26.
- Tope por perdida: f <= L / |q_p10| (perdida aceptada L del capital en un dia malo del decil inferior) y f <= f_worst = L / |peor dia|.
- Monte Carlo a 10 anios (~100 episodios) con bloques de dias para ver riqueza terminal, P(perdida) y drawdown para varias fracciones.
f = fraccion del capital asignada a la canasta (1.0 = 100% del capital, sin apalancamiento).
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

rng = np.random.default_rng(52)
d = pd.read_csv('/exp/basket_diario_72h.csv')
R = d.ret72.values / 100.0
is_ = (d.period == 'IS').values


def g(f, r):
    return np.mean(np.log1p(f * r))


def f_star(r):
    fmax = 0.999 / max(-r.min(), 1e-9)
    res = minimize_scalar(lambda f: -g(f, r), bounds=(0.0, fmax), method='bounded', options={'xatol': 1e-6})
    return res.x if g(res.x, r) > 0 else 0.0


print(f'dias: {len(R)} | media {R.mean()*100:+.2f}% | mediana {np.median(R)*100:+.2f}% | sd {R.std(ddof=1)*100:.2f}% | peor {R.min()*100:.2f}% | mejor {R.max()*100:.2f}% | % dias negativos {np.mean(R<0)*100:.0f}%')
fs = f_star(R)
print(f'\nKelly empirico (todos los dias): f* = {fs:.2f}x del capital; crecimiento log por episodio a f*: {g(fs, R)*100:+.2f}%  (a f=0.25: {g(0.25, R)*100:+.2f}%, f=0.5: {g(0.5, R)*100:+.2f}%, f=1: {g(1.0, R)*100:+.2f}%)')

boot = np.array([f_star(R[rng.integers(0, len(R), len(R))]) for _ in range(4000)])
print(f'incertidumbre (bootstrap por dia, 4000): f* mediana {np.median(boot):.2f} | p10 {np.percentile(boot,10):.2f} | p25 {np.percentile(boot,25):.2f} | p75 {np.percentile(boot,75):.2f} | p90 {np.percentile(boot,90):.2f} | P(f*=0) {np.mean(boot==0)*100:.0f}%')
f_rob = float(np.percentile(boot, 25))
print(f'  fraccion robusta (p25 del bootstrap) = {f_rob:.2f}x')

# validacion fuera de muestra: calibrar con 2022-24, evaluar en 2025-26
f_is = f_star(R[is_])
print(f'\nVALIDACION: f* con 2022-24 ({is_.sum()} dias) = {f_is:.2f}x -> crecimiento log en 2025-26 ({(~is_).sum()} dias): {g(f_is, R[~is_])*100:+.2f}% por episodio (f*=0.25: {g(0.25, R[~is_])*100:+.2f}%, f=0.5: {g(0.5, R[~is_])*100:+.2f}%); media OOS {R[~is_].mean()*100:+.2f}%')
f_oos = f_star(R[~is_])
print(f'  (informativo) f* calibrado con 2025-26 = {f_oos:.2f}x')

# tope por perdida
q10 = np.percentile(R, 10)
worst = R.min()
print(f'\nTOPES POR PERDIDA (fraccion del capital asignada a la canasta):')
for L in (0.01, 0.02, 0.03, 0.05):
    print(f'  perdida aceptada {L*100:.0f}% del capital: en un dia p10 (R={q10*100:.1f}%) -> f <= {L/abs(q10):.2f}x | en el peor dia visto (R={worst*100:.1f}%) -> f <= {L/abs(worst):.2f}x')

# Monte Carlo 10 anios (100 episodios): remuestreo de dias con reemplazo
N = 100
print(f'\nMONTE CARLO {N} episodios (~10 anios), 20000 trayectorias, dias remuestreados con reemplazo:')
print(f"  {'f':>5s} | {'riqueza final p5':>16s} {'mediana':>8s} {'p95':>8s} | {'P(final<1)':>10s} | {'max DD p50':>10s} {'p95':>6s} | {'P(DD>30%)':>9s}")
for f in (0.10, 0.20, 0.25, 0.30, 0.50, round(f_rob, 2), 1.0):
    idx = rng.integers(0, len(R), (20000, N))
    paths = np.cumprod(1 + f * R[idx], axis=1)
    peak = np.maximum.accumulate(paths, axis=1)
    dd = 1 - paths / peak
    fin = paths[:, -1]
    print(f'  {f:5.2f} | {np.percentile(fin,5):16.2f} {np.median(fin):8.2f} {np.percentile(fin,95):8.2f} | {np.mean(fin<1)*100:9.1f}% | {np.percentile(dd.max(axis=1),50)*100:9.1f}% {np.percentile(dd.max(axis=1),95)*100:5.1f}% | {np.mean(dd.max(axis=1)>0.30)*100:8.1f}%')
print('\nNOTA: cada episodio del Monte Carlo es un dia con la CANASTA COMPLETA (~22 springs); el operador a mano tomara ~3, lo que suma varianza dentro del dia:')
print('  var(media de 3) = tau^2 + sigma^2/3 = 53.0 + 32.9/3 = 64.0 (sd 8.0 pp) contra var(canasta de ~22) = 54.5 (sd 7.4 pp).')
