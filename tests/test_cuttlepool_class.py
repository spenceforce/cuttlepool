# -*- coding: utf-8
"""
Tests related to the CuttlePool class.
"""
import os
import threading
import time
import unittest
import warnings

from cuttlepool import CuttlePool, PoolConnection


DB = '_cuttlepool_test_db'
HOST = 'localhost'


class CuttlePoolTestCase(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings('ignore')
        self.db = DB
        self.host = HOST
        self.sql_type = os.environ['TEST_CUTTLE_POOL'].lower()

        if self.sql_type == 'mysql':
            import pymysql
            from mysql_credentials import USER, PASSWD

            self.Connection = pymysql.connections.Connection
            self.Cursor = pymysql.cursors.Cursor
            self.DiffCursor = pymysql.cursors.DictCursor

            self.connect = pymysql.connect

            self.credentials = dict(user=USER, passwd=PASSWD, host=self.host)

        elif self.sql_type == 'sqlite3':
            import sqlite3
            self.sqlite3 = sqlite3

            self.Connection = sqlite3.Connection
            self.row_factory = None
            self.diff_row_factory = sqlite3.Row

            self.connect = sqlite3.connect

            self.credentials = dict()

        if self.sql_type != 'sqlite3':
            self.con = self.connect(**self.credentials)

            cur = self.con.cursor()
            cur.execute('CREATE DATABASE IF NOT EXISTS {}'.format(self.db))
            cur.close()

        else:
            self.con = self.connect(self.db)

        self.credentials.update(database=self.db)

        self.cp = CuttlePool(self.connect, capacity=1, overflow=1,
                             timeout=1, **self.credentials)
        self.cp.ping = lambda x: True

    def tearDown(self):
        self.cp._close_connections()

        if self.sql_type != 'sqlite3':
            cur = self.con.cursor()
            cur.execute('DROP DATABASE {}'.format(self.db))
            cur.close()
        else:
            os.remove(self.db)

        self.con.close()


class CuttlePoolInstanceTestCase(CuttlePoolTestCase):

    def test_connection_class_set(self):
        cp = CuttlePool(self.connect, **self.credentials)
        self.assertEqual(cp.Connection, self.Connection)

    def test_instantiate_wrong_capacity(self):
        with self.assertRaises(ValueError):
            CuttlePool(self.connect, capacity=0)

    def test_instantiate_wrong_overflow(self):
        with self.assertRaises(ValueError):
            CuttlePool(self.connect, overflow=-1)


class CuttleConnectionArgumentsPropertyTestCase(CuttlePoolTestCase):

    def test_connection_arguments_property(self):
        self.assertEqual(self.cp.connection_arguments,
                         self.cp._connection_arguments)

    def test_connection_arguments_copy(self):
        connection_arguments = self.cp.connection_arguments
        self.assertNotEqual(id(connection_arguments),
                            id(self.cp._connection_arguments))

        connection_arguments['db'] = 'different_db'

        self.assertNotEqual(connection_arguments,
                            self.cp._connection_arguments)
        self.assertNotEqual(connection_arguments,
                            self.cp.connection_arguments)


class CuttlePoolGetConnection(CuttlePoolTestCase):

    def test_get_connection(self):
        con = self.cp.get_connection()
        self.assertTrue(isinstance(con, PoolConnection))
        self.assertTrue(isinstance(con._connection,
                                   self.Connection))

        con.close()

    def test_get_max_connections(self):
        con = [self.cp.get_connection() for __ in range(self.cp._maxsize)]

        # Ensure all connections are open
        self.assertTrue(all(map(lambda x: isinstance(x, PoolConnection), con)))
        self.assertTrue(all(map(
            lambda x: isinstance(x._connection,
                                 self.Connection),
            con
        )))

        map(lambda x: x.close(), con)

    def test_get_connection_from_queue(self):
        con = self.cp.get_connection()
        con_id = id(con._connection)

        con.close()

        con = self.cp.get_connection()

        self.assertEqual(con_id, id(con._connection))

        con.close()

    def test_get_lost_connection(self):
        # create connections to deplete pool
        con = self.cp.get_connection()
        con2 = self.cp.get_connection()
        con_id = id(con._connection)

        # lose connection to the ether
        con._connection = None
        self.assertEqual(0, self.cp._pool.qsize())

        # get connection from pool and check for equality
        con = self.cp.get_connection()
        self.assertEqual(con_id, id(con._connection))

    def test_get_connection_timeout_success(self):

        self.cp._timeout = 10

        def exhaust_pool(pool):
            cons = [pool.get_connection() for __ in range(pool._maxsize)]
            time.sleep(5)
            cons[0].close()

        t = threading.Thread(target=exhaust_pool, args=(self.cp,))
        t.start()
        time.sleep(1)

        con_id = id(self.cp._reference_pool[0])

        con = self.cp.get_connection()

        self.assertEqual(con_id, id(con._connection))

    def test_get_connection_timeout_failure(self):
        with self.assertRaises(AttributeError):
            [self.cp.get_connection()
             for __ in range(self.cp._maxsize + 1)]


class CuttlePoolNormalizeConnection(CuttlePoolTestCase):

    def setUp(self):
        super(CuttlePoolNormalizeConnection, self).setUp()

        if self.sql_type == 'mysql':
            Cursor = self.Cursor

            class Pool(CuttlePool):

                def normalize_connection(self, connection):
                    with threading.RLock():
                        connection.cursorclass = Cursor

            self.change_con = lambda x: setattr(x,
                                                'cursorclass',
                                                self.DiffCursor)
            self.is_normalized = lambda x: x.cursorclass == self.Cursor

        elif self.sql_type == 'sqlite3':
            row_factory = self.row_factory

            class Pool(CuttlePool):

                def normalize_connection(self, connection):
                    with threading.RLock():
                        connection.row_factory = row_factory

            self.change_con = lambda x: setattr(x,
                                                'row_factory',
                                                self.diff_row_factory)
            self.is_normalized = lambda x: x.row_factory == self.row_factory

        self.cp = Pool(self.connect, **self.credentials)

    def test_normalize_connection(self):
        con = self.cp.get_connection()

        # change connection property
        self.change_con(con._connection)

        # normalize connection
        self.cp.normalize_connection(con._connection)

        # ensure connection property was reset
        self.assertTrue(self.is_normalized(con._connection))


class CuttlePoolPingConnection(CuttlePoolTestCase):

    def setUp(self):
        super(CuttlePoolPingConnection, self).setUp()

        if self.sql_type == 'mysql':

            class Pool(CuttlePool):

                def ping(self, connection):
                    with threading.RLock():
                        try:
                            connection.ping()
                            return connection.open
                        except Exception:
                            return False

        elif self.sql_type == 'sqlite3':
            sqlite3 = self.sqlite3

            class Pool(CuttlePool):

                def ping(self, connection):
                    with threading.RLock():
                        try:
                            rv = connection.execute('SELECT 1').fetchall()
                            return True if rv == [(1,)] else False
                        except sqlite3.Error:
                            return False

        self.cp = Pool(self.connect, **self.credentials)

    def test_ping(self):
        self.assertTrue(self.cp.ping(self.cp._make_connection()))


class CuttlePoolPutConnection(CuttlePoolTestCase):

    def test_put_connection(self):
        self.assertEqual(0, self.cp._pool.qsize())

        self.cp.put_connection(self.cp._make_connection())

        self.assertEqual(1, self.cp._pool.qsize())

    def test_put_connection_handle_overflow(self):
        self.assertEqual(0, self.cp._pool.qsize())
        self.assertEqual(0, self.cp._size)

        con = self.cp._make_connection()
        con2 = self.cp._make_connection()

        self.assertEqual(2, self.cp._size)

        self.cp.put_connection(con)
        self.cp.put_connection(con2)

        self.assertEqual(1, self.cp._pool.qsize())
        self.assertEqual(1, self.cp._size)

    def test_put_connection_wrong_arg(self):
        with self.assertRaises(ValueError):
            self.cp.put_connection(1)


class CuttlePoolEmptyPool(CuttlePoolTestCase):

    def test_empty_pool(self):
        # make connections
        cons = [self.cp.get_connection() for __ in range(self.cp._capacity)]

        # place connections back in pool
        [con.close() for con in cons]

        self.cp.empty_pool()

        self.assertEqual(0, self.cp._size)
        self.assertTrue(self.cp._pool.empty())
