"""Reloj: ciclo alineado al reloj de pared, un solo worker con Wyckoff, logs en UTC, timezone propagado."""
import importlib.util
import logging
import os
from unittest.mock import MagicMock

from logs import _utc_formatter
from notifications.core import Notifier

_APP_PATH = os.path.join(os.path.dirname(__file__), '..', 'app', 'app.py')
_spec = importlib.util.spec_from_file_location('app_main_clock', _APP_PATH)
app_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(app_module)


class TestSecondsUntilNextCycle:
    def test_wakes_shortly_after_the_next_five_minute_mark(self):
        # 04:01:00 UTC -> el proximo multiplo de 5 min es 04:05:00; despierta a las 04:05:20
        now = 4 * 3600 + 60
        assert app_module.seconds_until_next_cycle(300, now=now) == 4 * 60 + 20

    def test_right_after_a_mark_it_waits_for_the_slack_not_a_whole_interval(self):
        now = 4 * 3600 + 5  # 04:00:05: el aviso de la vela que acaba de cerrar sale a las 04:00:20
        assert app_module.seconds_until_next_cycle(300, now=now) == 15

    def test_after_the_slack_it_waits_for_the_next_interval(self):
        now = 4 * 3600 + 30  # ya pasaron los 20 s del marco actual
        assert app_module.seconds_until_next_cycle(300, now=now) == 290

    def test_short_intervals_are_not_aligned(self):
        assert app_module.seconds_until_next_cycle(1) == 1
        assert app_module.seconds_until_next_cycle(30) == 30

    def test_never_returns_less_than_five_seconds(self):
        for offset in range(0, 300, 7):
            assert app_module.seconds_until_next_cycle(300, now=4 * 3600 + offset) >= 5


class TestEffectiveChunkSize:
    def test_wyckoff_enabled_puts_all_pairs_in_one_worker(self):
        settings = {'market_data_chunk_size': 20, 'wyckoff_alerts': {'enabled': True}}
        assert app_module.effective_chunk_size(settings, 30) == 30

    def test_wyckoff_disabled_keeps_the_configured_chunk(self):
        settings = {'market_data_chunk_size': 20, 'wyckoff_alerts': {'enabled': False}}
        assert app_module.effective_chunk_size(settings, 30) == 20

    def test_fewer_pairs_than_the_chunk_is_unchanged(self):
        settings = {'market_data_chunk_size': 20, 'wyckoff_alerts': {'enabled': True}}
        assert app_module.effective_chunk_size(settings, 12) == 20

    def test_missing_wyckoff_section_is_tolerated(self):
        assert app_module.effective_chunk_size({'market_data_chunk_size': 20}, 30) == 20

    def test_thirty_pairs_make_one_chunk(self):
        pairs = {f'P{i}/USDT': None for i in range(30)}
        settings = {'market_data_chunk_size': 20, 'wyckoff_alerts': {'enabled': True}}
        chunks = app_module.split_market_data(pairs, app_module.effective_chunk_size(settings, len(pairs)))
        assert len(chunks) == 1 and len(chunks[0]) == 30


def test_log_lines_carry_a_utc_timestamp():
    record = logging.LogRecord('x', logging.INFO, __file__, 1, 'hola', None, None)
    record.created = 0  # 1970-01-01 00:00:00 UTC, sin importar la zona del contenedor
    assert _utc_formatter('%(asctime)sZ %(message)s').format(record) == '1970-01-01 00:00:00Z hola'


def test_set_timezone_reaches_the_message_builder():
    notifier = Notifier.__new__(Notifier)
    notifier.chart_renderer = MagicMock()
    notifier.builder = MagicMock()
    notifier.set_timezone('America/Santiago')
    assert notifier.chart_renderer.timezone_str == 'America/Santiago'
    assert notifier.builder.timezone_str == 'America/Santiago'
