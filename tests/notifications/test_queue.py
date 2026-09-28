"""
Tests para NotificationQueue (specs/004-core-pipeline-test-coverage/).
"""
import pytest

from notifications.queue import NotificationQueue


def _msg(market='BTC/USDT', indicator='rsi', status='hot', quality='B', score=50.0):
    return {'market': market, 'indicator': indicator, 'status': status,
            'quality': quality, 'score': score}


class TestQualityFiltering:
    def test_below_min_quality_is_rejected(self):
        queue = NotificationQueue(min_quality='B')

        added = queue.add(_msg(quality='C'))

        assert added is False
        assert queue.size() == 0

    def test_at_or_above_min_quality_is_accepted(self):
        queue = NotificationQueue(min_quality='B')

        added = queue.add(_msg(quality='A'))

        assert added is True
        assert queue.size() == 1


class TestPriorityOrdering:
    def test_sort_by_priority_orders_descending(self):
        queue = NotificationQueue(min_quality='C')
        queue.add(_msg(market='A', score=10))
        queue.add(_msg(market='B', score=90))
        queue.add(_msg(market='C', score=50))

        queue.sort_by_priority()

        order = [queue.get_next().symbol for _ in range(3)]
        assert order == ['B', 'C', 'A']


class TestDuplicateDetection:
    def test_repeated_signal_marked_as_update(self):
        queue = NotificationQueue(min_quality='C')
        queue.add(_msg())
        first = queue.get_next()
        queue._mark_sent(first.get_signature())

        queue.add(_msg())
        second = queue.get_next()

        assert second.is_update is True


class TestProcessAll:
    def test_calls_send_func_once_per_item_in_priority_order(self):
        queue = NotificationQueue(min_quality='C')
        queue.add(_msg(market='LOW', score=10))
        queue.add(_msg(market='HIGH', score=90))

        sent_order = []

        def send_func(message, chart_file, is_update):
            sent_order.append(message['market'])

        count = queue.process_all(send_func, delay_msg=0, delay_photo=0)

        assert count == 2
        assert sent_order == ['HIGH', 'LOW']
        assert queue.size() == 0

    def test_exception_in_one_item_does_not_abort_batch(self):
        queue = NotificationQueue(min_quality='C')
        queue.add(_msg(market='FAILS', score=90))
        queue.add(_msg(market='OK', score=10))

        sent = []

        def send_func(message, chart_file, is_update):
            if message['market'] == 'FAILS':
                raise RuntimeError('boom')
            sent.append(message['market'])

        count = queue.process_all(send_func, delay_msg=0, delay_photo=0)

        assert sent == ['OK']
        assert count == 1
        assert queue.size() == 0
