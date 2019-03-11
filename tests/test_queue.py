# -*- coding: utf-8 -*-
"""
Queue tests.
"""
import pytest

from cuttlepool.queue import Queue

# Travis CI uses pytest v2.9.2 for Python 3.3 tests. Any fixtures that yield
# a resource using pytest <= v2.9.2 should use yield_fixture explicitly,
# otherwise use fixture as per the docs.
if int(pytest.__version__.split('.')[0]) >= 3:
    pytest.yield_fixture = pytest.fixture


@pytest.fixture
def queue():
    return Queue()


def test_push(queue):
    """
    Test pushing a value to a queue.
    """
    queue.push(object())

    assert queue.size == 1
    assert queue._start == queue._end


def test_push_multiple(queue):
    """
    Test pushing multiple values to a queue.
    """
    queue.push(object())
    queue.push(object())

    assert queue._start != queue._end
    assert queue.size == 2


def test_top(queue):
    """
    Test checking the first value in the queue.
    """
    obj = object()
    queue.push(obj)

    assert queue.top is obj


def test_top_empty(queue):
    """
    Test checking the first value in the queue when empty.
    """
    with pytest.raises(ValueError):
        queue.top


def test_pop(queue):
    """
    Test popping a value from the queue.
    """
    obj = object()
    queue.push(obj)

    assert obj is queue.pop()
    assert queue.size == 0


def test_pop_multiple(queue):
    """
    Test popping multiple values from the queue.
    """
    obj1 = object()
    obj2 = object()
    queue.push(obj1)
    queue.push(obj2)

    assert obj1 is queue.pop()
    assert obj2 is queue.pop()
    assert queue.size == 0


def test_pop_empty(queue):
    """
    Test popping the first value in the queue when empty.
    """
    with pytest.raises(ValueError):
        queue.pop()
