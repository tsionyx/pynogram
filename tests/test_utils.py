# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from unittest import TestCase

# to import 'use_test_instance'
# and prevent auto capturing the name by tox
from pyngrm import utils as src_utils
from pyngrm.utils import merge_dicts, pad_list


class TestMergeDicts(TestCase):
    def test_with_empty(self):
        d = {'foo': 1, 'bar': 2}
        self.assertDictEqual(merge_dicts(d, {}), d)

    def test_simple(self):
        d = {'foo': 1, 'bar': 2}
        d2 = {'baz': 3}
        self.assertDictEqual(merge_dicts(d, d2), {
            'foo': 1,
            'bar': 2,
            'baz': 3,
        })

    def test_overlapped(self):
        d = {'foo': 1, 'bar': 2}
        d2 = {'baz': 3, 'foo': 4}
        self.assertDictEqual(merge_dicts(d, d2), {
            'foo': 4,
            'bar': 2,
            'baz': 3,
        })

        self.assertDictEqual(merge_dicts(d2, d), {
            'foo': 1,
            'bar': 2,
            'baz': 3,
        }, 'Merge is not a communicative operation')


class TestPadList(TestCase):
    def setUp(self):
        self.to_pad = [1, 2, 3]

    def test_already_enough(self):
        self.assertEqual(
            pad_list(self.to_pad, 2, 5),
            self.to_pad
        )

    def test_simple(self):
        self.assertEqual(
            pad_list(self.to_pad, 5, 5),
            [5, 5, 1, 2, 3]
        )

    def test_right(self):
        self.assertEqual(
            pad_list(self.to_pad, 5, 5, left=False),
            [1, 2, 3, 5, 5]
        )


class TestUseTestInstance(TestCase):
    def setUp(self):
        self._id = id(self)

    def test_another(self):
        self.assertEqual(
            src_utils.use_test_instance(TestPadList).to_pad,
            [1, 2, 3])

    def test_me_another_instance(self):
        self.assertNotEqual(
            src_utils.use_test_instance(self.__class__)._id,
            self._id)
