# -*- coding: utf-8
"""
Tests related to the PoolConnection class.
"""
import unittest

from cuttlepool import CuttlePool
from cuttlepool.cuttlepool import PoolConnection


class PoolConnectionInstanceTestCase(unittest.TestCase):

    def test_poolconnection_instantiate_wrong_connection(self):
        with self.assertRaises(AttributeError):
            PoolConnection(connection=0, pool=CuttlePool())

    def test_poolconnection_instantiate_wrong_pool(self):
        with self.assertRaises(AttributeError):
            PoolConnection(connection=0, pool=0)
