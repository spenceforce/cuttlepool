# -*- coding: utf-8 -*-
"""

Cuttle Pool class.

"""
try:
    import queue
except ImportError:
    import Queue as queue

import pymysql.connections
import pymysql.cursors


class CuttlePool(object):
    """
    A connection pool for SQL databases.

    :param int capacity: Max number of connections in pool. Defaults to ``5``.
    :param int timeout: Time in seconds to wait for connection. Defaults to
                        ``None``.
    :param int overflow: The number of extra connections that can be made if
                         the pool is exhausted. Defaults to ``1``.
    :param \**kwargs: Connection arguments for the underlying database
                      connector.

    :raises ValueError: If capacity <= 0 or overflow < 0.
    :raises Empty: If ``pool`` does not return a connection within ``timeout``
                   seconds.
    """

    def __init__(self, capacity=5, overflow=1, timeout=None, **kwargs):
        if capacity <= 0:
            raise ValueError('connection pool requires a capacity of 1+ '
                             'connections')
        if overflow < 0:
            raise ValueError('pool overflow must be non negative')

        self._connection_arguments = kwargs
        self._capacity = capacity
        self._overflow = overflow
        self._timeout = timeout
        self._size = 0
        self._maxsize = self._capacity + self._overflow
        self._pool = queue.Queue(self._capacity)

    def __del__(self):
        self._close_connections()

    def _make_connection(self):
        """
        Returns a connection object.
        """
        connection = pymysql.connect(**self._connection_arguments)
        self._size += 1

        return connection

    def _close_connections(self):
        """
        Closes all connections in the pool.
        """
        while not self._pool.empty():
            try:
                connection = self._pool.get_nowait()
                connection.close()
            except queue.Empty:
                break

    def get_connection(self):
        """
        Returns a ``PoolConnection`` object.

        :raises AttributeError: If attempt to get connection times out.
        """
        try:
            connection = self._pool.get_nowait()
            connection.ping()
        except:
            if self._size < self._maxsize:
                connection = self._make_connection()
            else:
                try:
                    connection = self._pool.get(timeout=self._timeout)
                except queue.Empty:
                    raise AttributeError('could not get connection, the pool '
                                         'is depleted')

        return PoolConnection(connection, self, **self._connection_arguments)

    def put_connection(self, connection):
        """
        Adds a connection back to the pool.

        :param connection: A connection object.

        :raises ValueError: If improper connection object.
        """
        if not isinstance(connection, pymysql.connections.Connection):
            raise ValueError('improper connection object')

        try:
            self._pool.put_nowait(connection)
        except queue.Full:
            connection.close()
            self._size -= 1


class PoolConnection(object):
    """
    A wrapper around a connection object.

    :param connection: A connection object.
    :param pool: A connection pool.

    :raises AttributeError: If improper connection object or improper pool
                            object.
    """

    def __init__(self, connection, pool):
        if not isinstance(pool, CuttlePool):
            raise AttributeError('improper pool object')
        if not isinstance(connection, pymysql.connections.Connection):
            raise AttributeError('improper connection object')

        self._connection = connection
        self._pool = pool

    def __getattr__(self, attr):
        """
        Gets attributes of connection object.
        """
        return getattr(self._connection, attr)

    def close(self):
        """
        Returns the connection to the connection pool.
        """
        if isinstance(self._connection, pymysql.connections.Connection):
            self._pool.put_connection(self._connection)
            self._connection = None
            self._pool = None
