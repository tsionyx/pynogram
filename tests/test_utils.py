# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import sys

import pytest

from pyngrm.utils import merge_dicts, pad_list, interleave, max_safe


class TestMergeDicts(object):
    def test_with_empty(self):
        d = {'foo': 1, 'bar': 2}
        assert merge_dicts(d, {}) == d

    def test_simple(self):
        d = {'foo': 1, 'bar': 2}
        d2 = {'baz': 3}
        assert merge_dicts(d, d2) == {
            'foo': 1,
            'bar': 2,
            'baz': 3,
        }

    def test_overlapped(self):
        d = {'foo': 1, 'bar': 2}
        d2 = {'baz': 3, 'foo': 4}
        assert merge_dicts(d, d2) == {
            'foo': 4,
            'bar': 2,
            'baz': 3,
        }

        assert merge_dicts(d2, d) == {
            'foo': 1,
            'bar': 2,
            'baz': 3,
        }, 'Merge is not a communicative operation'


class TestPadList(object):
    @pytest.fixture(scope='class')
    def to_pad(self):
        return [1, 2, 3]

    def test_already_enough(self, to_pad):
        assert pad_list(to_pad, 2, 5) == to_pad

    def test_simple(self, to_pad):
        assert pad_list(to_pad, 5, 5) == [5, 5, 1, 2, 3]

    def test_right(self, to_pad):
        assert pad_list(to_pad, 5, 5, left=False) == [1, 2, 3, 5, 5]


class TestInterleave(object):
    def test_simple(self):
        assert interleave(
            [0, 2, 4], [1, 3, 5]) == list(range(6))

    def test_first_greater(self):
        assert interleave(
            [0, 2, 4, 6], [1, 3, 5]) == list(range(7))

    def test_second_greater(self):
        with pytest.raises(ValueError):
            assert interleave(
                [0, 2, 4], [1, 3, 5, 7]) == list(range(7))

    def test_first_greater_by_two(self):
        with pytest.raises(ValueError) as ei:
            interleave([0, 2, 4, 6], [1, 3])
        assert str(ei.value) == "The lists' sizes are too different: (4, 2)"

    def test_second_empty(self):
        assert interleave([1], []) == [1]

    def test_two_empties(self):
        assert interleave([], []) == []


class TestMaxSafe(object):
    @classmethod
    def _the_same_as_max(cls, *args, **kwargs):
        a = max_safe(*args, **kwargs)
        b = max(*args, **kwargs)
        assert a == b
        return a

    def test_simple(self):
        assert self._the_same_as_max([1, 2, 3]) == 3

    def test_args(self):
        assert self._the_same_as_max(3, 4, 5) == 5

    def test_with_key(self):
        assert self._the_same_as_max([5, 6, 7], key=lambda x: -x) == 5

    def test_args_with_key(self):
        assert self._the_same_as_max(8, 9, 10, key=lambda x: 1.0 / x) == 8

    @pytest.mark.skipif(sys.version_info < (3, 4), reason="requires Python3.4+")
    def test_empty_with_default_on_34(self):
        assert self._the_same_as_max([], default=7) == 7

    @pytest.mark.skipif(sys.version_info >= (3, 4), reason="requires Python<3.4")
    def test_empty_with_default_failed(self):
        with pytest.raises(TypeError, match='got an unexpected keyword argument'):
            self._the_same_as_max([], default=14)

    def test_empty_with_default(self):
        assert max_safe([], default=21) == 21

    def test_empty_true_object_with_default(self):
        assert max_safe(iter([]), default=28) == 28

    def test_generator(self):
        def _gen(n=5):
            while n > 0:
                yield n
                n -= 1

        assert max(_gen()) == 5
        assert max_safe(_gen(), default=3) == 5
