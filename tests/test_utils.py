# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import os
import random
import sys

import pytest

from pynogram.utils.cache import init_once
from pynogram.utils.iter import (
    merge_dicts,
    pad,
    interleave,
    max_safe,
    avg,
    max_continuous_interval,
)
from pynogram.utils.other import (
    get_version,
    two_powers, from_two_powers,
)
from pynogram.utils.priority_dict import PriorityDict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


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
        assert pad(to_pad, 2, 5) == to_pad

    def test_simple(self, to_pad):
        assert pad(to_pad, 5, 5) == [5, 5, 1, 2, 3]

    def test_right(self, to_pad):
        assert pad(to_pad, 5, 5, left=False) == [1, 2, 3, 5, 5]


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
        with pytest.raises(TypeError, match='unexpected keyword argument'):
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


class TestAvg(object):
    def test_basic(self):
        assert avg([1, 2, 3]) == 2

    def test_float_result(self):
        assert avg([5, 6, 8]) == 19.0 / 3

    def test_float_input(self):
        assert avg([5.5, 6.5]) == 6

    def test_iterator(self):
        it = iter([7, 8, 9])
        assert avg(it) == 8

    def test_empty(self):
        assert avg([]) is None


class TestPriorityDict(object):
    @pytest.fixture
    def p_dict(self):
        res = PriorityDict()
        res['foo'] = 1
        res['bar'] = 3
        res['baz'] = 2
        return res

    def test_basic(self, p_dict):
        assert p_dict.pop_smallest() == ('foo', 1)
        assert p_dict.pop_smallest() == ('baz', 2)
        assert p_dict.pop_smallest() == ('bar', 3)

        assert not p_dict

    def test_repeating_keys(self, p_dict):
        p_dict['foo'] = 0
        assert p_dict.pop_smallest()[0] == 'foo'
        assert p_dict.smallest()[0] == 'baz'
        assert p_dict.smallest()[0] == 'baz'

    def test_update(self, p_dict):
        p_dict.update({'baz': 1, 'foo': 7, 'bar': 5})
        assert p_dict.pop_smallest() == ('baz', 1)
        assert p_dict.pop_smallest() == ('bar', 5)
        assert p_dict.pop_smallest() == ('foo', 7)

        assert not p_dict

    def test_sorted(self, p_dict):
        assert [k for k, v in p_dict.sorted_iter()] == ['foo', 'baz', 'bar']

    def test_set_default(self, p_dict):
        assert 'tutu' not in p_dict
        assert p_dict.setdefault('tutu', 5) == 5
        assert 'tutu' in p_dict

        assert p_dict.setdefault('foo', 'something') == 1


class TestPriorityDictOld(TestPriorityDict):
    def test_repeating_priorities(self, p_dict):
        p_dict['baz'] = 1

        # undefined
        assert p_dict.pop_smallest()[0] == 'baz'
        assert p_dict.pop_smallest()[0] == 'foo'
        assert p_dict.pop_smallest() == ('bar', 3)

        assert not p_dict

    # noinspection PyProtectedMember
    def test_rebuild(self, p_dict):
        old_heap_id = id(p_dict._heap)

        p_dict['baz'] = 1
        p_dict['foo'] = 7
        p_dict['bar'] = 5

        assert id(p_dict._heap) == old_heap_id

        # this action resets the heap
        p_dict['foo'] = 10
        assert id(p_dict._heap) != old_heap_id


# class TestPriorityDict2(TestPriorityDict):
#     @pytest.fixture
#     def p_dict(self):
#         res = PriorityDict2()
#         res['foo'] = 1
#         res['bar'] = 3
#         res['baz'] = 2
#         return res
#
#     def test_repeating_priorities(self, p_dict):
#         p_dict['baz'] = 1
#
#         # undefined
#         assert p_dict.pop_smallest()[0] == 'foo'
#         assert p_dict.pop_smallest()[0] == 'baz'
#         assert p_dict.pop_smallest() == ('bar', 3)
#
#         assert not p_dict


class TestVersion(object):
    @pytest.fixture
    def root_path(self):
        return os.path.join(os.path.dirname(CURRENT_DIR), 'pynogram')

    def test_simple(self, root_path):
        save_path = sys.path
        assert root_path not in sys.path
        try:
            version = get_version()

            assert len(version) == 3
            assert all(isinstance(v, int) for v in version)

            assert root_path not in sys.path
        finally:
            sys.path = save_path

    def test_setup_py_already_in_path(self, root_path):
        save_path = sys.path
        try:
            sys.path = [v for v in sys.path if v != root_path]
            version = get_version()
            assert root_path not in sys.path
        finally:
            sys.path = save_path

        assert len(version) == 3
        assert all(isinstance(v, int) for v in version)


class TestInitOnce(object):
    class Foo(object):
        counter = 0

        @init_once
        def foo(self):
            return self.bar()

        def bar(self):
            self.counter += 1
            return dict()

    def test_without_once_every_time_new_dict(self):
        f = self.Foo()
        a = f.bar()
        b = f.bar()
        assert a is not b

    def test_with_once_the_same_dict(self):
        f = self.Foo()
        a = f.foo()
        b = f.foo()
        assert a is b

    def test_counter_incremented(self):
        f = self.Foo()
        f.bar()
        f.bar()
        f.bar()
        assert f.counter == 3

    def test_counter_do_not_incremented(self):
        f = self.Foo()
        f.foo()
        assert f.counter == 1
        f.foo()
        f.foo()
        f.foo()
        f.foo()
        assert f.counter == 1

        f.bar()
        assert f.counter == 2


class TestPowers(object):
    def test_zero(self):
        assert two_powers(0) == ()

    def test_one(self):
        assert two_powers(1) == (1,)

    def test_simple(self):
        assert two_powers(42) == (2, 8, 32)
        assert two_powers(103) == (1, 2, 4, 32, 64)

    def test_random(self):
        for i in range(100):
            n = random.randint(1, 10 ** 9)

            factors = two_powers(n)
            assert len(factors) > 0
            # factors are unique
            assert len(set(factors)) == len(factors)
            assert sum(factors) == n

            for f in factors:
                b = bin(f)
                assert b == '0b1' + '0' * (len(b) - 3)

    def test_round_trip(self):
        for i in range(100):
            n = random.randint(1, 10 ** 9)

            factors = two_powers(n)
            assert from_two_powers(factors) == n


class TestMaxInterval(object):
    def test_empty(self):
        assert max_continuous_interval([]) == 0

    def test_single(self):
        assert max_continuous_interval([3]) == 1

    def test_sparse(self):
        assert max_continuous_interval([3, 12, 14, 20]) == 1

    def test_min(self):
        assert max_continuous_interval([1, 3, 5, 6, 8, 10]) == 2

    def test_several(self):
        assert max_continuous_interval([1, 3, 5, 6, 8, 9, 10, 12, 13, 15, 16, 17]) == 3

    def test_four(self):
        assert max_continuous_interval([1, 3, 5, 6, 8, 9, 10, 12, 13, 15, 16, 17, 18]) == 4
