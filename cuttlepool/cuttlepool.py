# -*- coding: utf-8 -*-
"""

Cuttle Pool class.

"""
try:
    import queue
except ImportError:
    import Queue as queue


class CuttlePool(object):
    """
    A connection pool for SQL databases.

    :param int capacity: Max number of connections in pool. Defaults to 5.

    :raises ValueError: If capacity <= 0.
    """

    def __init__(self, capacity=5):
        if capacity <= 0:
            raise ValueError('connection pool requires a capacity of 1+ '
                             'connections')
        self.capacity = capacity
        self.size = 0
        self.pool = queue.Queue()
