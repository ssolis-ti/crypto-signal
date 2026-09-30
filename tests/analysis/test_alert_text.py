"""Textos de las alertas: lenguaje sencillo, pasos concretos, cifras honestas (analysis/alert_text.py)."""
import re

import pandas as pd
import pytest

from analysis.alert_text import (AlertItem, MAX_LIST, build_group_buy, build_info_bearish, build_radar,
                                 build_single_buy, exit_time, close_time, fmt_price, sizing_line, stop_price)

T = pd.Timestamp('2026-09-30T16:00:00Z')  # vela 16:00-20:00 UTC
TZ = 'America/Santiago'
JARGON = ('Spring', 'Upthrust', 'Wyckoff', 'backtest', 'Backtest', 'trampa', 'percentil', 'p10', 'sigma')


def item(pair='SOL/USDT', price=142.3, concurrent=2, watched=30, dvol=900e6, direction='hot'):
    return AlertItem(pair, direction, price, 3.4, T, concurrent=concurrent, watched=watched, dvol24h=dvol)


def plain(html):
    return re.sub(r'</?(b|i)>', '', html)


class TestPrices:
    def test_price_formats_by_magnitude(self):
        assert fmt_price(64210.5) == '64,210' or fmt_price(64210.5) == '64,211'
        assert fmt_price(142.3) == '142.3'
        assert fmt_price(2.4813) == '2.48'
        assert fmt_price(0.0921) == '0.0921'

    def test_tiny_prices_keep_four_significant_digits(self):
        assert fmt_price(0.00000871) == '0.00000871'
        assert fmt_price(0.000123456) == '0.0001235'

    def test_missing_or_invalid_price(self):
        assert fmt_price(None) == '?' and fmt_price(float('nan')) == '?' and fmt_price(0) == '?'

    def test_stop_is_ten_percent_below_the_reference(self):
        assert stop_price(100.0) == pytest.approx(90.0)
        assert stop_price(None) is None


class TestTimes:
    def test_exit_is_72_hours_after_the_candle_closes(self):
        assert close_time(item()) == pd.Timestamp('2026-09-30T20:00:00Z')
        assert exit_time(item()) == pd.Timestamp('2026-10-03T20:00:00Z')


class TestSingleBuyMessage:
    def test_has_the_steps_with_concrete_prices_and_times(self):
        msg = plain(build_single_buy(item(), TZ, 0.1))
        assert 'OPORTUNIDAD DE COMPRA: SOL/USDT' in msg
        assert 'precio de referencia: 142.3' in msg
        assert 'stop loss en 128.1' in msg
        assert 'sáb 20:00 UTC (17:00 Santiago)' in msg          # salida a las 72 h, en hora local tambien
        assert 'mié 20:00 UTC (17:00 Santiago)' in msg          # cierre de la vela

    def test_plain_language_without_jargon(self):
        msg = plain(build_single_buy(item(), TZ, 0.1))
        assert not any(word in msg for word in JARGON)

    def test_fits_comfortably_in_one_telegram_message(self):
        assert len(build_single_buy(item(concurrent=9), TZ, 6.0)) < 3500

    def test_sizing_uses_the_stop_arithmetic_and_never_assumes_capital(self):
        msg = plain(build_single_buy(item(), TZ, 0.1))
        assert 'hasta ~10% de tu capital' in msg and 'pierdes ~1% de tu capital' in msg
        assert 'USDT' not in msg.replace('SOL/USDT', '')

    def test_wide_day_shows_the_honest_daily_distribution_and_30_percent_cap(self):
        msg = plain(build_single_buy(item(concurrent=9), TZ, 0.1))
        assert '+0.6%' in msg and '4 a 5 de cada 10 días terminaron en pérdida' in msg
        assert 'no más de ~30% de tu capital' in msg

    def test_late_notice_only_when_late(self):
        assert 'Aviso tardío' not in build_single_buy(item(), TZ, 0.5)
        late = plain(build_single_buy(item(), TZ, 5.3))
        assert 'Aviso tardío' in late and 'hace 5.3 h' in late

    def test_low_liquidity_warns(self):
        assert 'Moneda poco líquida' in build_single_buy(item(dvol=5e6), TZ, 0.1)
        assert 'poco líquida' not in build_single_buy(item(dvol=500e6), TZ, 0.1)

    def test_twitter_section_is_appended_when_available(self):
        it = item()
        it.twitter_section = 'SECCION TWITTER'
        assert build_single_buy(it, TZ, 0.1).endswith('SECCION TWITTER')


class TestGroupBuyMessage:
    def items(self, n=9):
        return [item(pair=f'C{i}/USDT', price=10.0 + i, concurrent=n, watched=30, dvol=100e6 + i) for i in range(n)]

    def test_lists_every_coin_with_reference_and_stop(self):
        msg = plain(build_group_buy(self.items(), TZ, 0.1))
        assert 'pánico generalizado' in msg
        for i in range(9):
            assert f'C{i}/USDT' in msg
        assert 'stop 9.0' in msg          # 10.0 * 0.9

    def test_says_to_buy_several_and_how_much_in_total(self):
        msg = plain(build_group_buy(self.items(), TZ, 0.1))
        assert 'varias monedas de la lista' in msg and 'no más de ~30% de tu capital' in msg
        assert 'No es seguro' in msg or 'no es seguro' in msg.lower()

    def test_long_lists_are_truncated(self):
        msg = build_group_buy(self.items(MAX_LIST + 6), TZ, 0.1)
        assert f'y 6 más' in msg

    def test_narrow_group_uses_the_small_size_advice(self):
        its = [item(pair=f'C{i}/USDT', concurrent=3, watched=30) for i in range(3)]
        msg = plain(build_group_buy(its, TZ, 0.1))
        assert 'varias monedas a la vez' in msg and 'pánico generalizado' not in msg.lower().replace('caso', '')
        assert 'hasta ~10% de tu capital' in msg

    def test_low_liquidity_coins_are_flagged_in_the_list(self):
        its = self.items(3) + [item(pair='ENA/USDT', dvol=5e6, concurrent=4, watched=30)]
        for it in its:
            it.concurrent = 4
        msg = plain(build_group_buy(its, TZ, 0.1))
        assert 'ENA/USDT' in msg and '⚠️' in msg and 'poco líquidas (ENA)' in msg


class TestBearishAndRadar:
    def test_bearish_is_informative_and_says_to_do_nothing(self):
        msg = plain(build_info_bearish([item(direction='cold')], TZ, 0.1))
        assert 'sin acción' in msg and 'Nada.' in msg and 'Paso a paso' not in msg
        assert not any(word in msg for word in JARGON)

    def test_bearish_group_lists_the_coins(self):
        msg = plain(build_info_bearish([item(pair=f'C{i}/USDT', direction='cold') for i in range(3)], TZ, 0.1))
        assert '3 monedas' in msg and 'C0, C1, C2' in msg

    def test_radar_says_there_is_no_proven_edge(self):
        msg = plain(build_radar('WLD/USDT', 4.1, 6.3, T, TZ, 0.1, 'TWITTER'))
        assert 'No hay ventaja comprobada' in msg and 'TWITTER' in msg and 'subió 6.3%' in msg
        assert 'bajó 2.0%' in plain(build_radar('WLD/USDT', 4.1, -2.0, T, TZ, 0.1))


class TestSizingLine:
    def test_wide_and_narrow_advice_differ(self):
        assert '30%' in sizing_line(9, 30, several=True)
        assert '10%' in sizing_line(2, 30, several=False) and '30%' not in sizing_line(2, 30, several=False)
