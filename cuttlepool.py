# -*- coding: utf-8 -*-
"""
Cuttle Pool.

:license: BSD 3-clause, see LICENSE for details.
"""

__version__ = '0.8.0-dev'


try:
    import queue
except ImportError:
    import Queue as queue
try:
    import threading
except ImportError:
    import dummy_threading as threading
import sys
import warnings


_OVERFLOW = 0
_TIMEOUT = None


class CuttlePool(object):
    """
    A resource pool.

    :param func factory: A factory that produces the desired resource.
    :param int capacity: Max number of resource instances in the pool.
    :param int overflow: The number of extra resource instances that can be
        made if the pool is exhausted. Defaults to ``0``.
    :param int timeout: Time in seconds to wait for a resource. Defaults to
        ``None``.
    :param resource_wrapper: A Resource subclass.
    :param \**kwargs: Keyword arguments that are passed to ``factory`` when
        a resource instance is created.

    :raises ValueError: If capacity <= 0 or overflow < 0 or timeout < 0.
    :raises TypeError: If timeout is not int or ``None``.
    """

    def __init__(self,
                 factory,
                 capacity,
                 overflow=_OVERFLOW,
                 timeout=_TIMEOUT,
                 resource_wrapper=None,
                 **kwargs):
        if capacity <= 0:
            raise ValueError('CuttlePool requires a minimum capacity of 1')
        if overflow < 0:
            raise ValueError('Overflow must be non negative integer')
        if timeout is not None:
            msg = 'Timeout must be non negative integer'
            if type(timeout) != int:
                raise TypeError(msg)
            if timeout < 0:
                raise ValueError(msg)

        self._capacity = capacity
        self._overflow = overflow
        self._timeout = timeout

        self._factory = factory
        self._resource_wrapper = resource_wrapper or Resource
        self._factory_arguments = kwargs

        self._pool = queue.Queue(self._capacity)
        self._reference_pool = []

        # Required for locking the resource pool in multi-threaded
        # environments.
        self.lock = threading.RLock()

    @property
    def capacity(self):
        """
        The maximum capacity the pool will hold under normal circumstances.
        """
        return self._capacity

    @property
    def connection_arguments(self):
        """For compatibility with older versions, will be removed in 1.0."""
        warnings.warn(('connection_arguments is deprecated in favor of '
                       'factory_arguments and will be removed in 1.0'),
                      DeprecationWarning)
        return self.factory_arguments

    @property
    def factory_arguments(self):
        """
        Returns a copy of the factory arguments used to create a resource.
        """
        return self._factory_arguments.copy()

    @property
    def maxsize(self):
        """
        The maximum possible number of resource instances that can exist at any
        one time.
        """
        return self._capacity + self._overflow

    @property
    def overflow(self):
        """
        The number of additional resource instances the pool will create when
        it is at capacity.
        """
        return self._overflow

    @property
    def size(self):
        """
        The number of existing resource instances that have been made by the
        pool.

        :note: This is not the number of resources *in* the pool, but the
            number of existing resources. This includes resources in the
            pool and resources in use.

        .. warning:: This is not threadsafe. ``size`` can change when context
                     switches to another thread.
        """
        with self.lock:
            return len(self._reference_pool)

    @property
    def timeout(self):
        """
        The duration to wait for a resource to be returned to the pool when the
        pool is depleted.
        """
        return self._timeout

    def _harvest_lost_resources(self):
        """
        Returns lost resources to pool.
        """
        # A resource should be referenced by 3 things at any given time,
        # ``_reference_pool``, ``sys.getrefcount`` (it's referenced by
        # sys.getrefcount when sys.getrefcount is called), and either a
        # ``Resource`` or ``_pool``. If the refcount is less than 3 this
        # means it's only referenced by ``_reference_pool`` and
        # ``sys.getrefcount`` and should be returned to the pool. Iterating over
        # ``_reference_pool`` by index instead of directly was chosen to prevent
        # additional references to the resource objects from being made, which
        # would further cloud the refcount.
        with self.lock:
            for idx in range(self.size):
                if sys.getrefcount(self._reference_pool[idx]) < 3:
                    self.put_resource(self._reference_pool[idx])

    def _make_resource(self):
        """
        Returns a resource instance.
        """
        resource = self._factory(**self._factory_arguments)

        with self.lock:
            self._reference_pool.append(resource)

        return resource

    def get_connection(self, connection_wrapper=None):
        """For compatibility with older versions, will be removed in 1.0."""
        warnings.warn(('get_connection() is deprecated in favor of '
                       'get_resource() and will be removed in 1.0'),
                      DeprecationWarning)
        return self.get_resource(connection_wrapper)

    def get_resource(self, resource_wrapper=None):
        """
        Returns a ``Resource`` instance. This method will try to retrieve
        a resource in the following order. First if the pool is empty, it
        will return any unreferenced resources back to the pool. Second it
        will attempt to get a resource from the pool without a timeout. Third
        it will create a new resource if the maximum number of open
        resources hasn't been exceeded. Fourth it will try to get a
        resource from the pool with the specified timeout and will finally
        raise an error if the timeout is exceeded without finding a resource.
        Fifth if the resource is closed, a new resource is created to
        replace it.

        :param resource_wrapper: A Resource subclass.
        :return: A ``Resource`` instance.

        :raises PoolDepletedError: If attempt to get resource fails or times
            out.
        """
        resource = None

        if resource_wrapper is None:
            resource_wrapper = self._resource_wrapper

        if self._pool.empty():
            self._harvest_lost_resources()

        try:
            resource = self._pool.get_nowait()

        except queue.Empty:
            if self.size < self.maxsize:
                resource = self._make_resource()

        if resource is None:
            # Could not find or make resource, so must wait for a resource
            # to be returned to the pool.
            try:
                resource = self._pool.get(timeout=self._timeout)
            except queue.Empty:
                pass

        if resource is None:
            raise PoolDepletedError('Could not get resource, the pool is '
                                    'depleted')

        # Ensure resource is active.
        if not self.ping(resource):
            with self.lock:
                self._reference_pool.remove(resource)
            resource = self._make_resource()

        # Ensure all resources leave pool with same attributes.
        # ``normalize_connection()`` is used since it calls
        # ``normalize_resource()``, so if a user implements either one, the
        # resource will still be normalized. This will be changed in 1.0 to
        # call ``normalize_resource()`` when ``normalize_connection()`` is
        # removed.
        self.normalize_connection(resource)

        return resource_wrapper(resource, self)

    def normalize_connection(self, connection):
        """For compatibility with older versions, will be removed in 1.0."""
        warnings.warn(('normalize_connection is deprecated in favor of '
                       'normalize_resource and will be removed in 1.0'),
                      DeprecationWarning)
        return self.normalize_resource(connection)

    def normalize_resource(self, resource):
        """
        A user implemented function that resets the properties of the
        resource instance that was created by `factory`. This prevents
        unwanted behavior from a resource retrieved from the pool as it could
        have been changed when previously used.

        :param obj resource: A resource instance.
        """
        warnings.warn('Failing to implement `normalize_resource()` can '
                      'result in unwanted behavior.')

    def ping(self, resource):
        """
        A user implemented function that ensures the ``Resource`` object is
        open.

        :param obj resource: A ``Resource`` object.

        :return: A bool indicating if the resource is open (``True``) or
            closed (``False``).
        """
        warnings.warn('Failing to implement `ping()` can result in unwanted '
                      'behavior.')
        return True

    def put_connection(self, connection):
        """For compatibility with older versions, will be removed in 1.0."""
        warnings.warn(('put_connection is deprecated in favor of '
                       'put_resource and will be removed in 1.0'),
                      DeprecationWarning)
        return self.put_resource(connection)

    def put_resource(self, resource):
        """
        Adds a resource back to the pool or discards it if the pool is full.

        :param resource: A resource object.

        :raises ResourceTypeError: If improper resource object.
        :raises UnknownResourceError: If resource was not made by the
                                        pool.
        """
        with self.lock:
            if resource not in self._reference_pool:
                raise UnknownResourceError('Resource returned to pool was '
                                           'not created by pool')

        try:
            self._pool.put_nowait(resource)

        except queue.Full:
            with self.lock:
                self._reference_pool.remove(resource)


class Resource(object):
    """
    A wrapper around a resource object.

    :param resource: A resource object.
    :param pool: A resource pool.

    :raises PoolTypeError: If improper pool object.
    :raises ResourceTypeError: If improper resource object.
    """

    def __init__(self, resource, pool):
        if not isinstance(pool, CuttlePool):
            raise PoolTypeError('Improper pool object')
        if resource not in pool._reference_pool:
            raise UnknownResourceError('Improper resource object')

        object.__setattr__(self, '_resource', resource)
        object.__setattr__(self, '_pool', pool)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __getattr__(self, name):
        """
        Gets attributes of resource object.
        """
        return getattr(self._resource, name)

    def __setattr__(self, name, value):
        """Sets attributes of resource object."""
        if name not in self.__dict__:
            setattr(self._resource, name, value)
        else:
            object.__setattr__(self, name, value)

    def close(self):
        """
        Returns the resource to the resource pool.
        """
        if self._resource is not None:
            self._pool.put_resource(self._resource)
            self._resource = None
            self._pool = None


class CuttlePoolError(Exception):
    """Base class for exceptions in this module."""


class PoolDepletedError(CuttlePoolError):
    """Exception raised when pool timeouts."""


class UnknownResourceError(CuttlePoolError):
    """
    Exception raised when a resource is returned to the pool that was not
    made by the pool.
    """


class PoolTypeError(CuttlePoolError):
    """
    Exception raised when the object is not the proper resource pool.
    """


class PoolConnection(Resource):
    """For compatibility with older versions, will be removed in 1.0."""
    def __init__(*args, **kwargs):
        warnings.warn(('PoolConnection is deprecated in favor of Resource and '
                       'will be removed in 1.0'),
                      DeprecationWarning)
        super(PoolConnection, self).__init__(*args, **kwargs)


class UnknownConnectionError(CuttlePoolError):
    """
    Exception raised when a connection is returned to the pool that was not
    made by the pool.

    For compatibility with older versions, will be removed in 1.0.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(('UnknownConnectionError is deprecated in favor of '
                       'UnknownResourceError and will be removed in 1.0'),
                      DeprecationWarning)
