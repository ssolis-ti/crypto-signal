"""
Tests para el calculo UTC de la fecha de inicio en CCXTDriver (specs/003-utc-start-date/).
"""
from datetime import datetime, timedelta, timezone

import pytest

from exchanges.driver import CCXTDriver


def _driver():
    # _calculate_start_date es pura (no usa self.exchanges ni credenciales), asi que se
    # puede probar sin pasar por __init__ (que requiere config de exchange real).
    return CCXTDriver.__new__(CCXTDriver)


class TestCalculateStartDate:
    @pytest.mark.parametrize("time_unit,expected_kwargs", [
        ("5m", {"minutes": 5}),
        ("4h", {"hours": 4}),
        ("1d", {"days": 1}),
        ("2w", {"weeks": 2}),
        ("1M", {"days": 30}),   # aproximacion existente, sin cambios (FR-003)
        ("1y", {"days": 365}),  # aproximacion existente, sin cambios (FR-003)
    ])
    def test_matches_utc_based_expectation(self, time_unit, expected_kwargs):
        max_periods = 10
        before = datetime.now(timezone.utc)
        result_ms = _driver()._calculate_start_date(time_unit, max_periods)
        after = datetime.now(timezone.utc)

        expected_delta = max_periods * timedelta(**expected_kwargs)
        expected_low = int((before - expected_delta).timestamp() * 1000)
        expected_high = int((after - expected_delta).timestamp() * 1000)

        # tolerancia = el tiempo que tardo en ejecutarse el propio calculo, no offsets de horas
        assert expected_low <= result_ms <= expected_high

    def test_invalid_time_unit_still_raises(self):
        with pytest.raises(ValueError):
            _driver()._calculate_start_date("not-a-timeframe", 10)

    def test_zero_max_periods_returns_now(self):
        before = datetime.now(timezone.utc)
        result_ms = _driver()._calculate_start_date("4h", 0)
        after = datetime.now(timezone.utc)
        assert int(before.timestamp() * 1000) <= result_ms <= int(after.timestamp() * 1000)
