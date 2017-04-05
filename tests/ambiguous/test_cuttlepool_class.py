# -*- coding: utf-8
"""
Tests related to the CuttlePool class.
"""
import unittest

from cuttlepool import CuttlePool


class CuttlePoolInstanceTestCase(unittest.TestCase):

    def test_cuttlepool_instantiate_wrong_capacity(self):
        with self.assertRaises(ValueError):
            CuttlePool(capacity=0)

    def test_cuttlepool_instantiate_wrong_overflow(self):
        with self.assertRaises(ValueError):
            CuttlePool(overflow=-1)
