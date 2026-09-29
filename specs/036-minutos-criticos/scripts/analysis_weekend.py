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
