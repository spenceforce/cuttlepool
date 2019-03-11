# -*- coding: utf-8 -*-
"""
Queue class
"""


class _Node(object):
    def __init__(self, item):
        self.item = item
        self.next = None


class Queue(object):
    """
    A queue implementation using a linked list.
    """

    def __init__(self):
        self._start = self._end = None
        self.size = 0

    @property
    def top(self):
        """
        Get the first item in the queue.
        """
        if self.size == 0:
            raise ValueError("Queue is empty")

        return self._start.item

    def pop(self):
        """
        Pop value from queue.
        """
        if self.size == 0:
            raise ValueError("Queue is empty")

        node = self._start
        self._start = node.next
        self.size -= 1

        return node.item

    def push(self, item):
        """
        Push value onto queue.

        :param item: An item to put in the queue.
        """
        node = _Node(item)

        if self.size == 0:
            self._start = self._end = node
        else:
            self._end.next = node
            self._end = node

        self.size += 1
