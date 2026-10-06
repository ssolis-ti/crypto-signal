"""El marcador hacia adelante mide el stop del cierre y no inventa el universo."""
import importlib.util
from pathlib import Path

import pandas as pd

_PATH = Path(__file__).resolve().parents[2] / 'specs' / '040-validacion-hacia-adelante' / 'validate_forward.py'
_spec = importlib.util.spec_from_file_location('validate_forward', _PATH)
vf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vf)


def test_spot_name_maps_to_the_linear_perpetual():
    assert vf.futures_symbol('BTC/USDT') == 'BTC/USDT:USDT'
    assert vf.futures_symbol('BTC/USDT:USDT') == 'BTC/USDT:USDT'
    assert vf.futures_symbol('PEPE/USDT') == '1000PEPE/USDT:USDT'
    assert vf.futures_symbol('MSTRB/USDT') == 'MSTR/USDT:USDT'


def test_missing_watched_is_not_replaced_by_thirty():
    assert vf.watched_count({}) is None
    assert vf.watched_count({'watched_pairs': 0}) == 0
    assert vf.watched_count({'watched_pairs': 50}) == 50


def test_unknown_liquidity_is_not_eligible():
    assert vf.is_eligible({'eligible': False, 'dvol24h_usd': 50_000_000}) is False
    assert vf.is_eligible({'dvol24h_usd': 20_000_000}) is True
    assert vf.is_eligible({'dvol24h_usd': 19_000_000}) is False
    assert vf.is_eligible({}) is False


def test_stop_uses_the_signal_close_not_the_entry():
    # Entrada 100, cierre de la senal 110. El stop del cierre es 99.
    # El minimo 99 toca ese stop y no tocaria un stop del 90 colgado de la entrada.
    part = pd.DataFrame({'o': [100.0], 'h': [112.0], 'l': [99.0], 'c': [105.0]})
    ret, gap = vf.path_result(part, entry=100.0, signal_close=110.0, sign=1)
    assert ret == (99.0 / 100.0 - 1.0) * 100.0 - 0.1
    assert gap == 0.0


def test_a_wick_through_the_stop_is_recorded_and_does_not_change_the_fill():
    part = pd.DataFrame({'o': [100.0], 'h': [101.0], 'l': [89.0], 'c': [95.0]})
    ret, gap = vf.path_result(part, entry=100.0, signal_close=100.0, sign=1)
    assert round(ret, 10) == -10.1
    assert gap == 1.0


def test_unstopped_path_uses_the_close():
    part = pd.DataFrame({'o': [100.0], 'h': [110.0], 'l': [91.0], 'c': [104.0]})
    ret, gap = vf.path_result(part, entry=100.0, signal_close=100.0, sign=1)
    assert abs(ret - 3.9) < 1e-9
    assert gap is None


def test_episode_mean_drops_illiquid_springs_and_a_missing_universe():
    df = pd.DataFrame([
        dict(direction='hot', candle='a', r72=10.0, concurrent=10, watched=40, eligible=True),
        dict(direction='hot', candle='a', r72=-50.0, concurrent=10, watched=40, eligible=False),
        dict(direction='hot', candle='b', r72=99.0, concurrent=10, watched=None, eligible=True),
        dict(direction='cold', candle='a', r72=1.0, concurrent=10, watched=40, eligible=True),
    ])
    ep = vf.episode_table(df)
    assert list(ep.index) == ['a']
    assert ep.loc['a', 'canasta'] == 10.0
    assert ep.loc['a', 'springs'] == 1
