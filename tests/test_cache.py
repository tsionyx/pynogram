# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import time

from pyngrm.cache import Cache


class TestCache(object):
    def test_basic(self):
        c = Cache()
        c.save('foo', 42)
        c.save('bar', 288)

        assert c.get('foo') == 42
        assert c.get('bar') == 288
        assert c.get('unknown') is None

    def test_capacity(self):
        c = Cache(10)
        c.save('foo', 42)

        for i in range(10):
            assert c.get('foo') == 42
            c.save(i, i)

        assert c.get('foo') is None

    def test_expiration(self):
        c = Cache(10)
        c.save('foo', 42, 0.000001)

        time.sleep(0.01)
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
