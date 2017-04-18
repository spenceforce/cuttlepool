# -*- coding: utf-8
"""
Tests related to the CuttlePool class.
"""
import unittest

import pymysql
from cuttlepool import CuttlePool, PoolConnection

from mysql_credentials import USER, PASSWD

DB = '_cuttlepool_test_db'
HOST = 'localhost'


class CuttlePoolTestCase(unittest.TestCase):

    def setUp(self):
        self.Connection = pymysql.connections.Connection
        self.DiffCursor = pymysql.cursors.DictCursor
        self.credentials = dict(user=USER, passwd=PASSWD, host=HOST)

        self.con = pymysql.connect(**self.credentials)
        cur = self.con.cursor()
        cur.execute('CREATE DATABASE {}'.format(DB))
        cur.close()

        self.cp = CuttlePool(capacity=1, overflow=1, timeout=1,
                             db=DB, **self.credentials)

    def tearDown(self):
        self.cp._close_connections()

        cur = self.con.cursor()
        cur.execute('DROP DATABASE {}'.format(DB))
        cur.close()
        self.con.close()


class CuttlePoolInstanceTestCase(unittest.TestCase):

    def test_instantiate_wrong_capacity(self):
        with self.assertRaises(ValueError):
            CuttlePool(capacity=0)

    def test_instantiate_wrong_overflow(self):
        with self.assertRaises(ValueError):
            CuttlePool(overflow=-1)


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
        self.assertTrue(con.open)

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
        self.assertTrue(all(map(lambda x: x.open, con)))

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

    def test_get_connection_timeout(self):
        with self.assertRaises(AttributeError):
            [self.cp.get_connection()
             for __ in range(self.cp._maxsize + 1)]


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

        self.assertTrue(con.open)
        self.assertFalse(con2.open)

    def test_put_connection_revert_cursorclass(self):
        con = self.cp._make_connection()
        con_id = id(con)

        new_cursorclass = self.DiffCursor

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

    def test_put_connection_wrong_arg(self):
        with self.assertRaises(ValueError):
            self.cp.put_connection(1)
