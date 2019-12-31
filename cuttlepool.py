# -*- coding: utf-8 -*-
"""
CuttlePool.

:license: BSD 3-clause, see LICENSE for details.
"""

__version__ = '0.9.2-dev'

try:
    import threading
except ImportError:
    import dummy_threading as threading
import time
import warnings
import weakref


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

        # The reference queue is divided in two sections. One section is a
        # queue of resources that are ready for use (the available region).
        # The other section is an unordered list of resources that are
        # currently in use and NoneType objects (the unavailable region).
        self._reference_queue = [None] * self.maxsize
        self._resource_start = self._resource_end = 0
        # _size is the number of existing resources. _available is the
        # number of available resources.
        self._size = self._available = 0

        # Required for locking the resource pool in multi-threaded
        # environments.
        self._lock = threading.RLock()
        # Notify thread waiting for resource that the queue is not empty when
        # a resource is returned to the pool.
        self._not_empty = threading.Condition(self._lock)

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
        Return a copy of the factory arguments used to create a resource.
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
        with self._lock:
            return self._size

    @property
    def timeout(self):
        """
        The duration to wait for a resource to be returned to the pool when the
        pool is depleted.
        """
        return self._timeout

    def _get(self, timeout, resource_wrapper=None):
        """
        Get a resource from the pool. If timeout is ``None`` waits
        indefinitely.

        :param timeout: Time in seconds to wait for a resource.
        :type timeout: int
        :param resource_wrapper: A Resource subclass.
        :return: A tuple containing a ``_ResourceTracker`` and ``Resource``.

        :raises PoolEmptyError: When timeout has elapsed and unable to
            retrieve resource.
        """
        if resource_wrapper is None:
            resource_wrapper = self._resource_wrapper

        with self._lock:
            if timeout is None:
                while self.empty():
                    self._not_empty.wait()
            else:
                time_end = time.time() + timeout
                while self.empty():
                    time_left = time_end - time.time()
                    if time_left < 0:
                        raise PoolEmptyError

                    self._not_empty.wait(time_left)

            rtracker = self._reference_queue[self._resource_start]
            self._resource_start = (self._resource_start + 1) % self.maxsize
            self._available -= 1

            wrapped_resource = rtracker.wrap_resource(self, resource_wrapper)

            return rtracker, wrapped_resource

    def _get_tracker(self, resource):
        """
        Return the resource tracker that is tracking ``resource``.

        :param resource: A resource.
        :return: A resource tracker.
        :rtype: :class:`_ResourceTracker`
        """
        with self._lock:
            for rt in self._reference_queue:
                if rt is not None and resource is rt.resource:
                    return rt

        raise UnknownResourceError('Resource not created by pool')

    def _harvest_lost_resources(self):
        """Return lost resources to pool."""
        with self._lock:
            for i in self._unavailable_range():
                rtracker = self._reference_queue[i]
                if rtracker is not None and rtracker.available():
                    self.put_resource(rtracker.resource)

    def _make_resource(self, resource_wrapper=None):
        """
        Returns a resource instance.

        :param resource_wrapper: A Resource subclass.
        :return: A tuple containing a ``_ResourceTracker`` and ``Resource``.
        """
        if resource_wrapper is None:
            resource_wrapper = self._resource_wrapper

        with self._lock:
            for i in self._unavailable_range():
                if self._reference_queue[i] is None:
                    rtracker = _ResourceTracker(
                        self._factory(**self._factory_arguments))

                    self._reference_queue[i] = rtracker
                    self._size += 1
                    # tell the resource-tracker to wrap the resource. We return the resource-tracker an the wrapped resource
                    wrapped_resource = rtracker.wrap_resource(
                        self, resource_wrapper)
                    return rtracker, wrapped_resource

            raise PoolFullError

    def _put(self, rtracker):
        """
        Put a resource back in the queue.

        :param rtracker: A resource.
        :type rtracker: :class:`_ResourceTracker`

        :raises PoolFullError: If pool is full.
        :raises UnknownResourceError: If resource can't be found.
        """
        with self._lock:
            if self._available < self.capacity:
                for i in self._unavailable_range():
                    if self._reference_queue[i] is rtracker:
                        # i retains its value and will be used to swap with
                        # first "empty" space in queue.
                        break
                else:
                    raise UnknownResourceError

                j = self._resource_end
                rq = self._reference_queue
                rq[i], rq[j] = rq[j], rq[i]

                self._resource_end = (self._resource_end + 1) % self.maxsize
                self._available += 1

                self._not_empty.notify()
            else:
                raise PoolFullError

    def _remove(self, rtracker):
        """
        Remove a resource from the pool.

        :param rtracker: A resource.
        :type rtracker: :class:`_ResourceTracker`
        """
        with self._lock:
            i = self._reference_queue.index(rtracker)
            self._reference_queue[i] = None
            self._size -= 1

    def _unavailable_range(self):
        """
        Return a generator for the indices of the unavailable region of
        ``_reference_queue``.
        """
        with self._lock:
            i = self._resource_end
            j = self._resource_start
            if j < i or self.empty():
                j += self.maxsize

            for k in range(i, j):
                yield k % self.maxsize

    def empty(self):
        """Return ``True`` if pool is empty."""
        with self._lock:
            return self._available == 0

    def get_connection(self, connection_wrapper=None):
        """For compatibility with older versions, will be removed in 1.0."""
        warnings.warn(('get_connection() is deprecated in favor of '
                       'get_resource() and will be removed in 1.0'),
                      DeprecationWarning)
        return self.get_resource(connection_wrapper)

    def get_resource(self, resource_wrapper=None):
        """
        Returns a ``Resource`` instance.

        :param resource_wrapper: A Resource subclass.
        :return: A ``Resource`` instance.

        :raises PoolEmptyError: If attempt to get resource fails or times
            out.
        """
        rtracker = None
        wrapped_resource = None

        if resource_wrapper is None:
            resource_wrapper = self._resource_wrapper

        if self.empty():
            self._harvest_lost_resources()

        try:
            # Try to get a resource from the pool. Do not wait.
            rtracker, wrapped_resource = self._get(0, resource_wrapper)
        except PoolEmptyError:
            pass

        if rtracker is None:
            # Could not find resource, try to make one.
            try:
                rtracker, wrapped_resource = self._make_resource(
                    resource_wrapper)
            except PoolFullError:
                pass

        if rtracker is None:
            # Could not find or make resource, so must wait for a resource
            # to be returned to the pool.
            try:
                rtracker, wrapped_resource = self._get(
                    self._timeout, resource_wrapper)
            except PoolEmptyError:
                pass

        if rtracker is None:
            raise PoolEmptyError

        # Ensure resource is active.
        if not self.ping(rtracker.resource):
            # Lock here to prevent another thread creating a resource in the
            # index that will have this resource removed. This ensures there
            # will be space for _make_resource() to place a newly created
            # resource.
            with self._lock:
                self._remove(rtracker)
                rtracker, wrapped_resource = self._make_resource(
                    resource_wrapper)

        # Ensure all resources leave pool with same attributes.
        # normalize_connection() is used since it calls
        # normalize_resource(), so if a user implements either one, the
        # resource will still be normalized. This will be changed in 1.0 to
        # call normalize_resource() when normalize_connection() is
        # removed.
        self.normalize_connection(rtracker.resource)

        return wrapped_resource

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
        warnings.warn('Failing to implement normalize_resource() can '
                      'result in unwanted behavior.')

    def ping(self, resource):
        """
        A user implemented function that ensures the ``Resource`` object is
        open.

        :param obj resource: A ``Resource`` object.

        :return: A bool indicating if the resource is open (``True``) or
            closed (``False``).
        """
        warnings.warn('Failing to implement ping() can result in unwanted '
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

        :raises UnknownResourceError: If resource was not made by the
                                        pool.
        """
        rtracker = self._get_tracker(resource)

        try:
            self._put(rtracker)
        except PoolFullError:
            self._remove(rtracker)


class _ResourceTracker(object):
    """
    Track if a resource is in use.

    :param resource: A resource instance.
    """

    def __init__(self, resource):
        self.resource = resource
        self._weakref = None

    def available(self):
        """Determine if resource available for use."""
        return self._weakref is None or self._weakref() is None

    def wrap_resource(self, pool, resource_wrapper):
        """
        Return a resource wrapped in ``resource_wrapper``.

        :param pool: A pool instance.
        :type pool: :class:`CuttlePool`
        :param resource_wrapper: A wrapper class for the resource.
        :type resource_wrapper: :class:`Resource`
        :return: A wrapped resource.
        :rtype: :class:`Resource`
        """
        resource = resource_wrapper(self.resource, pool)
        self._weakref = weakref.ref(resource)
        return resource


class Resource(object):
    """
    A wrapper around a resource instance.

    :param resource: A resource instance.
    :param pool: A resource pool.
    """

    def __init__(self, resource, pool):
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


class PoolEmptyError(CuttlePoolError):
    """Exception raised when pool timeouts."""


class PoolFullError(CuttlePoolError):
    """Exception raised when there is no space to add a resource."""


class UnknownResourceError(CuttlePoolError):
    """
    Exception raised when a resource is returned to the pool that was not
    made by the pool.
    """


class PoolConnection(Resource):
    """For compatibility with older versions, will be removed in 1.0."""

    def __init__(self, *args, **kwargs):
        warnings.warn(('PoolConnection is deprecated in favor of Resource and '
                       'will be removed in 1.0'), DeprecationWarning)
        super(PoolConnection, self).__init__(*args, **kwargs)
