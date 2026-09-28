"""
Tests para el fix UTC de CalibrationLogger (specs/006-deferred-cleanup-findings/,
cierra el hallazgo 002-F3).
"""
from datetime import datetime, timezone

from utils.calibration import CalibrationLogger


class _RecordingLogger:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []
        self.warning_calls = []

    def info(self, msg, *a, **kw):
        self.info_calls.append(msg)

    def error(self, msg, *a, **kw):
        self.error_calls.append(msg)

    def warning(self, msg, *a, **kw):
        self.warning_calls.append(msg)


def _calib():
    calib = CalibrationLogger(enabled=True)
    calib.logger = _RecordingLogger()
    return calib


class TestLogOhlcvUsesUtc:
    def test_logged_time_string_matches_utc_not_host_local(self, monkeypatch):
        monkeypatch.setenv("TZ", "America/Santiago")
        calib = _calib()

        # 1735689600000 ms == 2025-01-01T00:00:00Z
        ts_ms = 1735689600000
        candle = [ts_ms, 100.0, 101.0, 99.0, 100.5, 10.0]

        calib.log_ohlcv('BTC/USDT', [candle])

        expected_time_str = datetime.fromtimestamp(
            ts_ms / 1000, tz=timezone.utc
        ).strftime('%Y-%m-%d %H:%M')
        assert any(expected_time_str in line for line in calib.logger.info_calls)
        # host-local (America/Santiago, UTC-3/UTC-4) would show a different hour
        assert not any('2024-12-31' in line for line in calib.logger.info_calls)


class TestReportAnomalyTimestampIsUtc:
    def test_anomaly_timestamp_is_utc_aware_iso_string(self):
        calib = _calib()

        # high < low triggers _report_anomaly internally
        candle = [1735689600000, 100.0, 90.0, 95.0, 100.5, 10.0]
        calib.log_ohlcv('BTC/USDT', [candle])

        assert len(calib.anomalies) == 1
        timestamp_str = calib.anomalies[0]['timestamp']
        parsed = datetime.fromisoformat(timestamp_str)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset().total_seconds() == 0
