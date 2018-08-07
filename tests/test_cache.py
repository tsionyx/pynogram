# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import time

from pynogram.core.line.base import TwoLayerCache
from pynogram.utils.cache import (
    Cache,
    ExpirableCache,
)


class TestCache(object):
    def test_basic(self):
        c = Cache()
        c.save('foo', 42)
        c.save('bar', 288)

        assert c.get('foo') == 42
        assert c.get('bar') == 288
        assert c.get('unknown') is None

    def test_capacity(self):
        c = Cache(10, increase=True)
        c.save('foo', 42)

        for i in range(10):
            assert c.get('foo') == 42
            c.save(i, i)

        assert c.get('foo') is None
        assert c.max_size == 20

    def test_expiration(self):
        c = ExpirableCache(10)
        c.save('foo', 42, time=0.000001)
        c.save('bar', 28, time=60)

        time.sleep(0.01)
        assert c.get('bar') == 28
        assert c.get('bar') == 28

        assert c.get('foo') == 42
        assert c.get('foo') is None

    def test_hit_rate(self):
        c = Cache(10)

        c.save('foo', 42)
        assert c.hit_rate == 0

        assert c.get('bar') is None
        assert c.hit_rate == 0

        c.get('foo')
        assert c.hit_rate == 0.5

        assert c.get('baz') is None
        assert c.hit_rate == 1.0 / 3

        c.get('foo')
        assert c.get('foo') == 42
        assert c.hit_rate == 0.6

    def test_bad_increase_multiplier(self):
        c = Cache(10, increase=1)

        # for the first iteration to succeed
        c.save('first', 0)

        # 5 times all the same: the max_size does not increase and remains 10
        for _ in range(5):
            c.save('foo', 42)

            for i in range(9):
                assert c.get('foo') == 42
                c.save(i, i)

            assert c.get('foo') is None

    def test_do_not_increase(self):
        c = Cache(10, increase=True, do_not_increase_after=15)

        c.save('foo', 42)
        for i in range(10):
            assert c.get('foo') == 42
            c.save(i, i)
        assert c.get('foo') is None

        assert c.max_size == 15

        c.save('foo', 42)
        for i in range(15):
            assert c.get('foo') == 42
            c.save(i, i)
        assert c.get('foo') is None

        # do not increase after 15
        assert c.max_size == 15

    def test_nonogram_cache(self):
        c = TwoLayerCache(5)
        c.save(('foo', 'bar'), 1)
        c.save(('foo', 'baz'), 2)

        assert len(c) == 2
        # noinspection PyProtectedMember
        assert list(c._storage) == ['foo']

        assert c.get(('foo', 'baz')) == 2
        assert c.delete(('foo', 'baz')) is True
        assert c.get(('foo', 'baz')) is None

        assert len(c) == 1
        # noinspection PyProtectedMember
        assert list(c._storage) == ['foo']
