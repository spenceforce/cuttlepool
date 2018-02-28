# -*- coding: utf-8 -*-
"""
CuttlePool tests.
"""
import gc
import threading
import time

import pytest

from cuttlepool import (_ResourceTracker, CuttlePool, Resource, PoolEmptyError,
                        PoolFullError)
import mockresource


class MockPool(CuttlePool):
    def normalize_resource(self, resource):
        pass

    def ping(self, resource):
        return resource.open


class SubResource(Resource):
    pass


@pytest.fixture()
def pool():
    """A CuttlePool instance."""
    p = MockPool(mockresource.factory, capacity=5, overflow=1)
    return p


@pytest.fixture()
def rtracker(pool):
    """A _ResourceTracker instance."""
    rt = pool._make_resource()
    return rt


@pytest.fixture()
def resource(pool):
    """A Resource instance."""
    r = pool.get_resource()
    yield r
    r.close()


def test_nonpositive_capacity():
    """Tests error is raised when nonpositive capacity is specified."""
    with pytest.raises(ValueError):
        MockPool(mockresource.factory, capacity=0)


def test_negative_overflow():
    """Tests error is raised when negative overflow is specified."""
    with pytest.raises(ValueError):
        MockPool(mockresource.factory, capacity=1, overflow=-1)


def test_improper_timeout():
    """Tests error is raised for improper timeout argument."""
    with pytest.raises(ValueError):
        MockPool(mockresource.factory, capacity=1, timeout=-1)

    with pytest.raises(TypeError):
        MockPool(mockresource.factory, capacity=1, timeout=-0.1)


def test_resource_wrapper():
    """
    Tests the proper Resource subclass is returned from ``get_resource()``.
    """
    pool = MockPool(mockresource.factory,
                    capacity=1,
                    resource_wrapper=SubResource)
    r = pool.get_resource()
    assert isinstance(r, SubResource)


def test_empty(pool):
    """Tests if pool is empty."""
    assert pool.empty
    r = pool.get_resource()
    assert pool.empty
    r.close()
    assert not pool.empty


def test_resource_wrapper_get_resource():
    """
    Tests the proper Resource subclass is returned from ``get_resource()``.
    """
    pool = MockPool(mockresource.factory, capacity=1)
    r = pool.get_resource(resource_wrapper=SubResource)
    assert isinstance(r, SubResource)


def test_get_empty(pool):
    """Tests the pool raises a ``PoolEmptyError``."""
    with pytest.raises(PoolEmptyError):
        pool._get(0)


def test_get(pool, resource):
    """Tests ``_get()`` gets a resource."""
    resource.close()            # Returns resource to pool.
    rt = pool._get(0)
    assert isinstance(rt, _ResourceTracker)


def test_get_wait():
    def worker(r):
        time.sleep(5)
        r.close()

    pool = MockPool(mockresource.factory, capacity=1)
    resource = pool.get_resource()

    t = threading.Thread(target=worker, args=(resource,))
    t.start()

    rt = pool._get(None)
    assert isinstance(rt, _ResourceTracker)


def test_get_tracker(pool, rtracker):
    """Tests the resource tracker for a resource is returned."""
    rt = pool._get_tracker(rtracker.resource)
    assert rt is rtracker


def test_harvest_lost_resources(pool):
    """Tests unreferenced resources are returned to the pool."""
    def get_resource_id():
        """
        Ensures ``Resource`` falls out of scope before calling
        ``_harvest_lost_resources()``.
        """
        return id(pool.get_resource()._resource)
    r_id = get_resource_id()
    # Run garbage collection to ensure ``Resource`` created in
    # ``get_resource_id()`` is destroyed.
    gc.collect()
    pool._harvest_lost_resources()
    assert r_id == id(pool.get_resource()._resource)


def test_make_resource(pool):
    """
    Tests the resource object returned from _make_resource is the proper class
    instance.
    """
    r = pool._make_resource()
    assert pool.size == 1
    assert isinstance(r, _ResourceTracker)


def test_put_full():
    """Tests ``PoolFullError`` is raised."""
    pool = MockPool(mockresource.factory, capacity=1, overflow=1)
    r1 = pool.get_resource()
    r2 = pool.get_resource()
    print(pool.capacity, pool._available)

    pool._put(pool._get_tracker(r1._resource))
    with pytest.raises(PoolFullError):
        pool._put(pool._get_tracker(r2._resource))


def test_put(pool, rtracker):
    """Tests ``_put()`` returns resource to pool."""
    assert pool._available == 0
    pool._put(rtracker)
    assert pool._available == 1


def test_remove(pool, rtracker):
    """Tests ``_remove()`` removes resource from pool."""
    pool._remove(rtracker)
    assert pool.size == pool._available == 0
    assert list(filter(None, pool._reference_queue)) == []


def test_get_resource(pool):
    """
    Tests the resource object returned from get_resource is the
    proper class instance.
    """
    r = pool.get_resource()
    assert isinstance(r, Resource)


def test_get_resource_overflow(pool):
    """
    Tests the pool creates proper number of overflow resources properly.
    """
    rs = []
    for _ in range(pool.maxsize):
        rs.append(pool.get_resource())

    assert pool.size == pool.maxsize

    for r in rs:
        r.close()

    assert pool.size == pool.capacity


def test_get_resource_depleted(pool):
    """Tests the pool will return a resource once one is available."""
    def worker(pool):
        r = pool.get_resource()
        time.sleep(5)
        r.close()

    for _ in range(pool.maxsize):
        t = threading.Thread(target=worker, args=(pool,))
        t.start()

    time.sleep(2)
    r = pool.get_resource()


def test_get_resource_depleted_error():
    """Tests the pool will raise an error when depleted."""
    pool = MockPool(mockresource.factory, capacity=1, timeout=1)
    with pytest.raises(PoolEmptyError):
        rt = []
        while True:
            rt.append(pool.get_resource())


def test_normalize_resource():
    """
    Tests that the normalize_resource method is properly called on
    resources returned from get_resource.
    """
    class Normalize(MockPool):
        def normalize_resource(self, resource):
            setattr(resource, 'one', 1)

    pool = Normalize(mockresource.factory, capacity=1)
    r = pool.get_resource()
    r_id = id(r._resource)
    r.one = 2
    assert r.one == 2
    r.close()

    r2 = pool.get_resource()
    r2_id = id(r2._resource)
    assert (r2.one == 1 and r_id == r2_id)


def test_ping(pool):
    """
    Tests that the ping method is properly called on resources returned
    from get_resource.
    """
    r = pool.get_resource()
    r_id = id(r._resource)
    r._resource.close()     # Close the underlying resource object.
    r.close()                 # Return the resource to the pool.

    # Calling get_resource() should create a new resource object since
    # the previous one (which is the only one currently in the pool) is not
    # open.
    r2 = pool.get_resource()
    r2_id = id(r2._resource)
    assert r_id != r2_id


def test_put_resource(pool):
    """
    Tests that the resource is properly returned to the pool.
    """
    r = pool.get_resource()
    r_id = id(r._resource)

    pool.put_resource(r._resource)
    assert id(pool.get_resource()._resource) == r_id


def test_with_resource(pool):
    """Tests Resource context manager."""
    with pool.get_resource() as r:
        assert isinstance(r, Resource)

    assert r._resource is None

    r2 = pool.get_resource()

    with r2:
        assert isinstance(r2, Resource)

    assert r2._resource is None


def test_resource_available(pool, rtracker):
    """
    Tests a resource is properly tracked by a ``_ResourceTracker`` instance.
    """
    assert rtracker.available()
    r = rtracker.wrap_resource(pool, Resource)
    assert not rtracker.available()
    del r
    gc.collect()
    assert rtracker.available()


def test_wrap_resource(pool, rtracker):
    """
    Tests a resource is properly wrapped and referenced by
    ``_ResourceTracker``.
    """
    r = rtracker.wrap_resource(pool, Resource)
    assert isinstance(r, Resource)
    assert rtracker._weakref() is not None


def test_resource_getattr_setattr(resource):
    """Tests that attributes are set on the underlying resource object."""
    resource.one = 1
    assert resource.one == 1
    assert 'one' not in resource.__dict__
    assert resource._resource.one == 1
    assert 'one' in resource._resource.__dict__
    assert resource.one == resource._resource.one


def test_close(pool):
    """Tests the close method of a Resource object."""
    r = pool.get_resource()

    r.close()
    assert r._resource is None
    assert r._pool is None


def test_recycling(pool):
    """
    Tests no errors are raised for multiple rounds of getting and putting.
    """
    for _ in range(5):
        rs = [pool.get_resource() for _ in range(pool.maxsize)]
        for r in rs:
            r.close()

    assert pool._available == pool.size == pool.capacity
