# -*- coding: utf-8 -*-
"""
CuttlePool tests.
"""
import threading
import time

import pytest

from cuttlepool import CuttlePool, PoolConnection
import mocksql


class MockPool(CuttlePool):
    def normalize_connection(self, connection):
        pass

    def ping(self, connection):
        return connection.open


@pytest.fixture()
def pool():
    """A CuttlePool object."""
    p = MockPool(mocksql.connect)
    yield p
    p.empty_pool()


@pytest.fixture()
def connection(pool):
    """A PoolConnection object."""
    c = pool.get_connection()
    yield c
    c.close()


def test_connection_attribute_set(pool):
    """
    Tests that the _connection attribute is set with the right class after a
    connection is requested.
    """
    assert pool._Connection is None
    pool.get_connection()
    assert pool._Connection is mocksql.MockConnection


def test_nonpositive_capacity():
    """Tests error is raised when nonpositive capacity is specified."""
    with pytest.raises(ValueError):
        MockPool(mocksql.connect, capacity=0)


def test_negative_overflow():
    """Tests error is raised when negative overflow is specified."""
    with pytest.raises(ValueError):
        MockPool(mocksql.connect, overflow=-1)


def test_improper_timeout():
    """Tests error is raised for improper timeout argument."""
    with pytest.raises(ValueError):
        MockPool(mocksql.connect, timeout=-1)

    with pytest.raises(TypeError):
        MockPool(mocksql.connect, timeout=-0.1)


def test_make_connection(pool):
    """
    Tests the connection object returned from _make_connection is the
    proper class instance.
    """
    con = pool._make_connection()
    assert isinstance(con, mocksql.MockConnection)


def test_harvest_lost_connections(pool):
    """Tests unreferenced connections are returned to the pool."""
    con_id = id(pool.get_connection())
    pool._harvest_lost_connections()
    assert con_id == id(pool.get_connection())


def test_empty_pool(pool):
    """Tests empty_pool closes the connections and throws them away."""
    con = pool.get_connection()
    pool.empty_pool()
    assert con.open is False
    assert pool._size == 0


def test_get_connection(pool):
    """
    Tests the connection object returned from get_connection is the
    proper class instance.
    """
    con = pool.get_connection()
    assert isinstance(con, PoolConnection)


def test_get_connection_overflow(pool):
    """
    Tests the pool creates proper number of overflow connections properly.
    """
    cons = []
    for __ in range(pool._capacity):
        cons.append(pool.get_connection())

    con = pool.get_connection()
    assert pool._size == pool._maxsize

    con.close()
    for con in cons:
        con.close()

    assert pool._size == pool._pool.qsize() == pool._capacity


def test_get_connection_depleted(pool):
    """Tests the pool will return a connection once one is available."""
    def worker(pool):
        con = pool.get_connection()
        time.sleep(3)
        con.close()

    for _ in range(pool._maxsize):
        t = threading.Thread(target=worker, args=(pool,))
        t.start()

    time.sleep(1)
    con = pool.get_connection()


def test_get_connection_depleted_error():
    """Tests the pool will raise an error when depleted."""
    pool = MockPool(mocksql.connect, timeout=1)
    with pytest.raises(AttributeError):
        cons = []
        while True:
            cons.append(pool.get_connection())


def test_normalize_connection():
    """
    Tests that the normalize_connection method is properly called on
    connections returned from get_connection.
    """
    class Normalize(MockPool):
        def normalize_connection(self, connection):
            setattr(connection, 'one', 1)

    pool = Normalize(mocksql.connect)
    con = pool.get_connection()
    con_id = id(con._connection)
    setattr(con, 'one', 2)
    assert con.one == 2
    con.close()

    con2 = pool.get_connection()
    con2_id = id(con2._connection)
    assert (con2.one == 1 and con_id == con2_id)


def test_ping(pool):
    """
    Tests that the ping method is properly called on connections returned
    from get_connection.
    """
    con = pool.get_connection()
    con_id = id(con._connection)
    con._connection.close()     # Close the underlying connection object.
    con.close()                 # Return the connection to the pool.

    # Calling get_connection() should create a new connection object since
    # the previous one (which is the only one currently in the pool) is not
    # open.
    con2 = pool.get_connection()
    con2_id = id(con2._connection)
    assert con_id != con2_id


def test_put_connection(pool):
    """
    Tests that the connection is properly returned to the pool.
    """
    con = pool.get_connection()
    con_id = id(con._connection)
    assert pool._pool.empty() is True

    pool.put_connection(con._connection)
    assert pool._pool.qsize() == 1
    assert id(pool._pool.get_nowait()) == con_id


def test_with_poolconnection(pool):
    """Tests PoolConnection context manager."""
    with pool.get_connection() as con:
        assert isinstance(con, PoolConnection)

    assert con._connection is None

    con2 = pool.get_connection()

    with con2:
        assert isinstance(con2, PoolConnection)

    assert con2._connection is None


def test_poolconnection_getattr_setattr(connection):
    """Tests that attributes are set on the underlying connection object."""
    connection.one = 1
    assert connection.one == 1
    assert 'one' not in connection.__dict__
    assert connection._connection.one == 1
    assert 'one' in connection._connection.__dict__


def test_close(pool):
    """Tests the close method of a PoolConnection object."""
    con = pool.get_connection()
    assert pool._pool.empty() is True

    con.close()
    assert con._connection is None
    assert con._pool is None
    assert pool._pool.qsize() == 1
