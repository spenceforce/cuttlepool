# -*- coding: utf-8
"""
Tests related to the CuttlePool class.
"""
import unittest

import pymysql
from cuttlepool import CuttlePool
from cuttlepool.cuttlepool import PoolConnection

from mysql_credentials import USER, PASSWD

DB = '_cuttlepool_test_db'
HOST = 'localhost'

credentials = dict(user=USER, passwd=PASSWD, host=HOST)


class CuttlePoolTestCase(unittest.TestCase):

    def setUp(self):
        self.con = pymysql.connect(**credentials)
        cur = self.con.cursor()
        cur.execute('CREATE DATABASE {}'.format(DB))
        cur.close()

        self.cp = CuttlePool(capacity=1, overflow=1, timeout=1,
                             db=DB, **credentials)

    def tearDown(self):
        self.cp._close_connections()

        cur = self.con.cursor()
        cur.execute('DROP DATABASE {}'.format(DB))
        cur.close()
        self.con.close()


class CuttlePoolMakeConnectionTestCase(CuttlePoolTestCase):

    def test_cuttlepool_make_connection(self):
        self.assertEqual(0, self.cp._size)

        connection = self.cp._make_connection()

        self.assertTrue(isinstance(connection, pymysql.connections.Connection))
        self.assertEqual(1, self.cp._size)


class CuttlePoolCollectLostConnectionsTestCase(CuttlePoolTestCase):

    def test_cuttlepool_collect_lost_connections(self):
        # create connection
        con = self.cp.get_connection()
        con_id = id(con._connection)

        # lose connection to the ether
        con._connection = None

        # return connection to pool
        self.assertEqual(0, self.cp._pool.qsize())
        self.cp._collect_lost_connections()
        self.assertEqual(1, self.cp._pool.qsize())

        # get connection from pool and check for equality
        con = self.cp.get_connection()
        self.assertEqual(con_id, id(con._connection))


class CuttlePoolCloseConnectionsTestCase(CuttlePoolTestCase):

    def test_cuttlepool_close_connections(self):
        con = self.cp.get_connection()
        con_ref = con._connection
        con.close()

        self.assertEqual(self.cp._pool.qsize(), 1)
        self.assertTrue(con_ref.open)

        self.cp._close_connections()
        self.assertEqual(self.cp._pool.qsize(), 0)
        self.assertFalse(con_ref.open)


class CuttlePoolGetConnection(CuttlePoolTestCase):

    def test_cuttlepool_get_connection(self):
        con = self.cp.get_connection()
        self.assertTrue(isinstance(con, PoolConnection))
        self.assertTrue(isinstance(con._connection,
                                   pymysql.connections.Connection))
        self.assertTrue(con.open)

        con.close()

    def test_cuttlepool_get_max_connections(self):
        con = [self.cp.get_connection() for __ in range(self.cp._maxsize)]

        # Ensure all connections are open
        self.assertTrue(all(map(lambda x: isinstance(x, PoolConnection), con)))
        self.assertTrue(all(map(
            lambda x: isinstance(x._connection,
                                 pymysql.connections.Connection),
            con
        )))
        self.assertTrue(all(map(lambda x: x.open, con)))

        map(lambda x: x.close(), con)

    def test_cuttlepool_get_connection_from_queue(self):
        con = self.cp.get_connection()
        con_id = id(con._connection)

        con.close()

        con = self.cp.get_connection()

        self.assertEqual(con_id, id(con._connection))

        con.close()

    def test_cuttlepool_get_connection_timeout(self):
        with self.assertRaises(AttributeError):
            [self.cp.get_connection()
             for __ in range(self.cp._maxsize + 1)]


class CuttlePoolPutConnection(CuttlePoolTestCase):

    def test_cuttlepool_put_connection(self):
        self.assertEqual(0, self.cp._pool.qsize())

        self.cp.put_connection(self.cp._make_connection())

        self.assertEqual(1, self.cp._pool.qsize())

    def test_cuttlepool_put_connection_handle_overflow(self):
        self.assertEqual(0, self.cp._pool.qsize())
        self.assertEqual(0, self.cp._size)

        con = self.cp._make_connection()
        con2 = self.cp._make_connection()

        self.assertEqual(2, self.cp._size)

        self.cp.put_connection(con)
        self.cp.put_connection(con2)

        self.assertEqual(1, self.cp._pool.qsize())
        self.assertEqual(1, self.cp._size)

        self.assertTrue(con.open)
        self.assertFalse(con2.open)

    def test_cuttlepool_put_connection_revert_cursorclass(self):
        con = self.cp._make_connection()
        con_id = id(con)

        new_cursorclass = pymysql.cursors.DictCursor

        # set con cursorclass to different cursor
        con.cursorclass = new_cursorclass

        # return to pool
        self.cp.put_connection(con)

        # check cursorclass changed to default
        self.assertEqual(con_id, id(self.cp._reference_pool[0]))
        self.assertNotEqual(self.cp._reference_pool[0].cursorclass,
                            new_cursorclass)
        self.assertEqual(self.cp._reference_pool[0].cursorclass,
                         self.cp._connection_arguments['cursorclass'])

    def test_cuttlepool_put_connection_wrong_arg(self):
        with self.assertRaises(ValueError):
            self.cp.put_connection(1)
