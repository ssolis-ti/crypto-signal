"""Analisis de los experimentos de spec 038 (criterio en spec.md, fijado antes). Corre en la imagen Freqtrade."""
import glob, json, os, zipfile
import numpy as np
import pandas as pd

RES = '/freqtrade/user_data/backtest_results'
rng = np.random.default_rng(5)
N_TESTS, N_BOOT = 6, 3000
LO, HI = 100 * (0.05 / N_TESTS / 2), 100 * (1 - 0.05 / N_TESTS / 2)
IS_RANGE, OOS_RANGE = ('2022-01-01', '2025-01-01'), ('2025-01-01', '2026-09-22')


def load_all():
    """{(estrategia, periodo): DataFrame de trades} leyendo los zips por su meta (estrategia + rango)."""
    out = {}
    for meta in sorted(glob.glob(f'{RES}/*.meta.json')):
        m = json.load(open(meta))
        for strat, info in m.items():
            zf = meta.replace('.meta.json', '.zip')
            start = pd.Timestamp(info.get('backtest_start_ts', 0), unit='s').strftime('%Y-%m-%d') if 'backtest_start_ts' in info else None
            per = 'IS' if start and start.startswith('2022') else 'OOS' if start and start.startswith('2025') else None
            if per is None or not os.path.exists(zf):
                continue
            z = zipfile.ZipFile(zf)
            name = [n for n in z.namelist() if n.endswith('.json') and 'meta' not in n and 'config' not in n][0]
            data = json.loads(z.read(name))['strategy'].get(strat)
            if not data:
                continue
            if not data['trades']:
                continue
            t = pd.DataFrame(data['trades'])
            t['open_date'] = pd.to_datetime(t['open_date'])
            t['ret'] = t['profit_ratio'] * 100
            t['day'] = t['open_date'].dt.normalize()
            t['key'] = t['pair'] + '|' + t['open_date'].astype(str)
            out[(strat, per, data.get('stake_amount', 100), data.get('max_open_trades'))] = t
    return out


def pick(all_t, strat, per):
    c = [(k, v) for k, v in all_t.items() if k[0] == strat and k[1] == per and k[2] == 100 and (k[3] in (100, 28))]
    # modo senal: max_open_trades alto; nos quedamos con la corrida mas reciente si hay varias
    return c[-1][1] if c else None


def boot_ci(d, stat):
    days = d['day'].unique()
    groups = {k: g for k, g in d.groupby('day')}
    res = []
    for _ in range(N_BOOT):
        s = pd.concat([groups[days[i]] for i in rng.integers(0, len(days), len(days))])
        v = stat(s)
        if v is not None:
            res.append(v)
    return np.percentile(res, [LO, HI])


if __name__ == '__main__':
    A = load_all()
    base_names = {'IS': 'WyckoffLab_SpringH72_SL10', 'OOS': 'WyckoffLab_SpringH72_SL10'}
    base = {p: pick(A, 'WyckoffLab_SpringH72_SL10', p) for p in ('IS', 'OOS')}
    ctrl = {p: pick(A, 'Exp_E0_Base', p) for p in ('IS', 'OOS')}
    print('trades base:', {p: (None if v is None else len(v)) for p, v in base.items()},
          '| control E0:', {p: (None if v is None else len(v)) for p, v in ctrl.items()})
    for p in ('IS', 'OOS'):
        print(f"  {p}: media base {base[p].ret.mean():+.2f}  control {ctrl[p].ret.mean():+.2f}")

    def summary(name, t):
        return f"n={len(t):4d} media={t.ret.mean():+6.2f}% acierto={(t.ret>0).mean()*100:4.0f}% peor={t.ret.min():+7.2f}%"

    print(f"\n{'exp':16s} {'per':5s} {'variante':48s} | dif vs {'(excluidos / base pareada)'}")
    verdict = {}
    for name in ('Exp_E1_Sweep10', 'Exp_E2_Sweep15', 'Exp_E3_Drop24h', 'Exp_E4_Trailing', 'Exp_E5_TP48h', 'Exp_E6_H48'):
        kind = 'filtro' if name in ('Exp_E1_Sweep10', 'Exp_E2_Sweep15', 'Exp_E3_Drop24h') else 'salida'
        difs, worst_ok = {}, True
        parts = []
        for p in ('IS', 'OOS'):
            v, b = pick(A, name, p), ctrl[p]
            if v is None or b is None:
                difs[p] = None
                continue
            if kind == 'filtro':
                rest = b[~b.key.isin(v.key)]
                dif = v.ret.mean() - rest.ret.mean()
                extra = f"excluidos: {summary('', rest)}"
            else:
                m = v.merge(b[['key', 'ret']], on='key', suffixes=('', '_b'))
                dif = (m.ret - m.ret_b).mean()
                extra = f"base pareada: media={m.ret_b.mean():+.2f}% peor={m.ret_b.min():+.2f}% (n pareados {len(m)})"
                worst_ok &= v.ret.min() >= b.ret.min() - 0.5
            difs[p] = dif
            print(f"{name:16s} {p:5s} {summary('', v)} | {dif:+5.2f} pp | {extra}")
        # unido
        if all(difs.get(p) is not None for p in ('IS', 'OOS')):
            v = pd.concat([pick(A, name, p) for p in ('IS', 'OOS')])
            b = pd.concat([ctrl[p] for p in ('IS', 'OOS')])
            if kind == 'filtro':
                b = b.assign(_m=b.key.isin(v.key))
                stat = lambda s: (s.loc[s._m, 'ret'].mean() - s.loc[~s._m, 'ret'].mean()) if s._m.any() and (~s._m).any() else None
                lo, hi = boot_ci(b, stat)
            else:
                m = v.merge(b[['key', 'ret', 'day']].rename(columns={'ret': 'ret_b'}), on='key', suffixes=('', '_x'))
                m['d'] = m.ret - m.ret_b
                lo, hi = boot_ci(m.rename(columns={'day': 'day'}), lambda s: s['d'].mean())
            ok = difs['IS'] > 0 and difs['OOS'] > 0 and lo > 0 and (worst_ok if kind == 'salida' else True)
            verdict[name] = ok
            print(f"{'':16s} unido IC{100-2*LO:.1f}% por dia [{lo:+.2f}, {hi:+.2f}] -> {'APRUEBA' if ok else 'NO aprueba'}\n")
    print('VEREDICTO:', {k: ('APRUEBA' if v else 'NO aprueba') for k, v in verdict.items()})
