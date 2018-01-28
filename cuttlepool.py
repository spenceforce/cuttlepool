# -*- coding: utf-8 -*-
"""
Cuttle Pool class.

:license: BSD 3-clause, see LICENSE for details.
"""

__version__ = '0.6.0'


try:
    import queue
except ImportError:
    import Queue as queue
import sys
import threading
import warnings


CAPACITY = 5
OVERFLOW = 1
TIMEOUT = None


class CuttlePool(object):
    """
    A connection pool for SQL databases.

    :param func connect: The ``connect`` function of the chosen sql driver.
    :param int capacity: Max number of connections in pool. Defaults to ``5``.
    :param int timeout: Time in seconds to wait for connection. Defaults to
                        ``None``.
    :param int overflow: The number of extra connections that can be made if
                         the pool is exhausted. Defaults to ``1``.
    :param \**kwargs: Connection arguments for the underlying database
                      connector.

    :raises ValueError: If capacity <= 0 or overflow < 0 or timeout < 0.
    :raises TypeError: If timeout is not int.
    """

    def __init__(self, connect, capacity=CAPACITY,
                 overflow=OVERFLOW, timeout=TIMEOUT, **kwargs):
        if capacity <= 0:
            raise ValueError('Connection pool requires a capacity of at least '
                             '1 connection')
        if overflow < 0:
            raise ValueError('Pool overflow must be non negative')
        if timeout is not None:
            msg = 'Timeout must be non negative integer'
            if type(timeout) != int:
                raise TypeError(msg)
            if timeout < 0:
                raise ValueError(msg)

        self._connect = connect
        self._connection_arguments = kwargs
        # The class of the connection object which will be set when the first
        # connection is requested.
        self._Connection = None

        self._capacity = capacity
        self._overflow = overflow
        self._timeout = timeout

        self._pool = queue.Queue(self._capacity)
        self._reference_pool = []

        # Required for locking the connection pool in multi-threaded
        # environments.
        self.lock = threading.RLock()

    def __del__(self):
        self.empty_pool()

    @property
    def _maxsize(self):
        """
        The maximum possible number of connections that can exist at any one
        time.
        """
        return self._capacity + self._overflow

    @property
    def _size(self):
        """
        The number of active connections made by the connection pool.

        :note: This is not the number of connections *in* the pool, but the
               number of existing connections. This includes connections in the
               pool and connections in use.

        .. warning:: This is not threadsafe. ``_size`` can change when context
                     switches to another thread.
        """
        with self.lock:
            return len(self._reference_pool)

    @property
    def connection_arguments(self):
        """
        Returns a copy of the connection arguments used to create connections.
        """
        return {k: v for k, v in self._connection_arguments.items()}

    def _make_connection(self):
        """
        Returns a connection object.
        """
        connection = self._connect(**self._connection_arguments)

        with self.lock:
            if self._Connection is None:
                self._Connection = type(connection)

            self._reference_pool.append(connection)

        return connection

    def _harvest_lost_connections(self):
        """
        Returns lost connections to pool.
        """
        # A connection should be referenced by 3 things at any given time,
        # ``_reference_pool``, ``sys.getrefcount`` (it's referenced by
        # sys.getrefcount when sys.getrefcount is called), and either a
        # ``PoolConnection`` or ``_pool``.# If the refcount is less than 3 this
        # means it's only referenced by ``_reference_pool`` and
        # ``sys.getrefcount`` and should be returned to the pool. Iterating over
        # ``_reference_pool`` by index instead of directly was chosen to prevent
        # additional references to the connection objects from being made, which
        # would further cloud the refcount.
        with self.lock:
            for idx in range(self._size):
                if sys.getrefcount(self._reference_pool[idx]) < 3:
                    self.put_connection(self._reference_pool[idx])

    def empty_pool(self):
        """
        Closes and removes all connections associated with the pool.

        .. warning:: This function is not safe and will close any connection
                     in use *outside* of the pool as well as those in the
                     pool.
        """
        with self.lock:
            for con in self._reference_pool:
                if self.ping(con):
                    con.close()

        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except queue.Empty:
                break

        with self.lock:
            self._reference_pool = []

    def get_connection(self):
        """
        Returns a ``PoolConnection`` object. This method will try to retrieve
        a connection in the following order. First if the pool is empty, it
        will return any unreferenced connections back to the pool. Second it
        will attempt to get a connection from the pool without a timeout. Third
        it will create a new connection if the maximum number of open
        connections hasn't been exceeded. Fourth it will try to get a
        connection from the pool with the specified timeout and will finally
        raise an error if the timeout is exceeded without finding a connection.
        Fifth if the connection is closed, a new connection is created to
        replace it.

        :return: A ``PoolConnection`` object.

        :raises PoolDepletedError: If attempt to get connection fails or times
                                   out.
        """
        connection = None

        if self._pool.empty():
            self._harvest_lost_connections()

        try:
            connection = self._pool.get_nowait()

        except queue.Empty:
            if self._size < self._maxsize:
                connection = self._make_connection()

        if connection is None:
            # Could not find or make connection, so must wait for a connection
            # to be returned to the pool.
            try:
                connection = self._pool.get(timeout=self._timeout)
            except queue.Empty:
                pass

        if connection is None:
            raise PoolDepletedError('Could not get connection, the pool is '
                                    'depleted')

        # Ensure connection is active.
        if not self.ping(connection):
            with self.lock:
                self._reference_pool.remove(connection)
            connection = self._make_connection()

        # Ensure all connections leave pool with same attributes.
        self.normalize_connection(connection)

        return PoolConnection(connection, self)

    def normalize_connection(self, connection):
        """
        A user implemented function that resets the properties of the
        ``Connection`` object. This prevents unwanted behavior from a
        connection retrieved from the pool as it could have been changed when
        previously used.

        :param obj connection: A ``Connection`` object.
        """
        warnings.warn('Failing to implement `normalize_connection()` can '
                      'result in unwanted behavior.')

    def ping(self, connection):
        """
        A user implemented function that ensures the ``Connection`` object is
        open.

        :param obj connection: A ``Connection`` object.

        :return: A bool indicating if the connection is open (``True``) or
                 closed (``False``).
        """
        warnings.warn('Failing to implement `ping()` can result in unwanted '
                      'behavior.')
        return True

    def put_connection(self, connection):
        """
        Adds a connection back to the pool.

        :param connection: A connection object.

        :raises ConnectionTypeError: If improper connection object.
        :raises UnknownConnectionError: If connection was not made by the
                                        pool.
        """
        if not isinstance(connection, self._Connection):
            raise ConnectionTypeError('Improper connection object')

        with self.lock:
            if connection not in self._reference_pool:
                raise UnknownConnectionError('Connection returned to pool was '
                                             'not created by pool')

        try:
            self._pool.put_nowait(connection)

        except queue.Full:
            with self.lock:
                self._reference_pool.remove(connection)

            if self.ping(connection):
                connection.close()


class PoolConnection(object):
    """
    A wrapper around a connection object.

    :param connection: A connection object.
    :param pool: A connection pool.

    :raises PoolTypeError: If improper pool object.
    :raises ConnectionTypeError: If improper connection object.
    """

    def __init__(self, connection, pool):
        if not isinstance(pool, CuttlePool):
            raise PoolTypeError('Improper pool object')
        if not isinstance(connection, pool._Connection):
            raise ConnectionTypeError('Improper connection object')

        self._connection = connection
        self._pool = pool

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __getattr__(self, attr):
        """
        Gets attributes of connection object.
        """
        if attr != 'close':
            return getattr(self._connection, attr)

    def __setattr__(self, attr, value):
        """Sets attributes of connection object."""
        if attr not in ['close', '_connection', '_pool']:
            return setattr(self._connection, attr, value)

        if attr != 'close':
            self.__dict__[attr] = value

    def close(self):
        """
        Returns the connection to the connection pool.
        """
        if self._connection is not None:
            self._pool.put_connection(self._connection)
            self._connection = None
            self._pool = None


class CuttlePoolError(Exception):
    """Base class for exceptions in this module."""


class PoolDepletedError(CuttlePoolError):
    """Exception raised when pool timeouts."""


class UnknownConnectionError(CuttlePoolError):
    """
    Exception raised when a connection is returned to the pool that was not
    made by the pool.
    """


class ConnectionTypeError(CuttlePoolError):
    """
    Exception raised when the object returned to the pool is not the correct
    type.
    """


class PoolTypeError(CuttlePoolError):
    """
    Exception raised when the object is not the proper connection pool.
    """
