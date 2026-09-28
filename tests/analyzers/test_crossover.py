"""
Tests para CrossOver.analyze (specs/004-core-pipeline-test-coverage/).
"""
import pandas
import pytest

from analyzers.crossover import CrossOver


def _series_df(column, values, index=None):
    if index is None:
        index = pandas.date_range('2026-01-01', periods=len(values), freq='h', tz='UTC')
    return pandas.DataFrame({column: values}, index=index)


class TestCrossOverAnalyze:
    def test_hot_cross_detected(self):
        # key starts below, ends above crossed -> last row is_hot
        key = _series_df('rsi', [10, 20, 40])
        crossed = _series_df('signal', [30, 30, 30])

        result = CrossOver().analyze(key, 'rsi', 0, crossed, 'signal', 0)

        last = result.iloc[-1]
        assert last['is_hot'] is True or bool(last['is_hot']) is True
        assert not bool(last['is_cold'])

    def test_cold_cross_detected(self):
        # key starts above, ends below crossed -> last row is_cold
        key = _series_df('rsi', [50, 40, 20])
        crossed = _series_df('signal', [30, 30, 30])

        result = CrossOver().analyze(key, 'rsi', 0, crossed, 'signal', 0)

        last = result.iloc[-1]
        assert bool(last['is_cold']) is True
        assert not bool(last['is_hot'])

    def test_misaligned_rows_are_dropped(self):
        index_a = pandas.date_range('2026-01-01', periods=3, freq='h', tz='UTC')
        index_b = pandas.date_range('2026-01-01 02:00', periods=3, freq='h', tz='UTC')
        key = _series_df('rsi', [10, 20, 40], index=index_a)
        crossed = _series_df('signal', [30, 30, 30], index=index_b)

        result = CrossOver().analyze(key, 'rsi', 0, crossed, 'signal', 0)

        # only the overlapping timestamp (2026-01-01 02:00) survives dropna
        assert len(result) == 1
        assert not result.isna().any().any()

    def test_no_overlap_returns_empty_dataframe(self):
        index_a = pandas.date_range('2026-01-01', periods=2, freq='h', tz='UTC')
        index_b = pandas.date_range('2026-02-01', periods=2, freq='h', tz='UTC')
        key = _series_df('rsi', [10, 20], index=index_a)
        crossed = _series_df('signal', [30, 30], index=index_b)

        result = CrossOver().analyze(key, 'rsi', 0, crossed, 'signal', 0)

        assert result.empty

    def test_column_names_suffixed_by_config_index(self):
        key = _series_df('rsi', [10, 20, 40])
        crossed = _series_df('rsi', [30, 30, 30])  # same signal name, different config index

        result = CrossOver().analyze(key, 'rsi', 1, crossed, 'rsi', 2)

        assert 'rsi_1' in result.columns
        assert 'rsi_2' in result.columns
