# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import pytest

from pynogram.core.color import (
    Color, ColorMap,
)


class TestColorNames(object):
    def test_rgb_tuple(self):
        c = Color('r', (255, 0, 0))
        assert c.svg_name == 'rgb(255,0,0)'

    def test_rgb_string(self):
        c = Color('r', '255, 0, 0')
        assert c.svg_name == 'rgb(255, 0, 0)'

    def test_rgb_string_without_spaces(self):
        c = Color('r', '255,0,0')
        assert c.svg_name == 'rgb(255,0,0)'

    def test_hex_color(self):
        c = Color('r', 'f00')
        assert c.svg_name == '#f00'

    def test_hex_color_long(self):
        c = Color('r', 'ff0000')
        assert c.svg_name == '#ff0000'

    def test_readable(self):
        c = Color('r', 'red')
        assert c.svg_name == 'red'


class TestColorMap(object):
    def test_symbol_generation(self):
        cm = ColorMap()
        r = cm.make_color('r', 'red')
        g = cm.make_color('g', 'green')
        b = cm.make_color('b', 'blue')

        assert r.symbol == '!'  # Shift + 1
        assert g.symbol == '"'  # Shift + 2
        assert b.symbol == '#'  # Shift + 3

    def test_id_generation(self):
        cm = ColorMap()
        r = cm.make_color('r', 'red')
        g = cm.make_color('g', 'green')
        b = cm.make_color('b', 'blue')

        assert r.id_ == 4
        assert g.id_ == 8
        assert b.id_ == 16

    def test_reassign_symbol(self):
        cm = ColorMap()
        c = cm.make_color('r', 'red', '#')
        assert c.symbol == '#'

        # rewrite the old object
        cm.make_color('r', 'red', '%')
        assert c.symbol == '%'

    def test_do_not_reassign_symbol_if_empty(self):
        cm = ColorMap()
        c = cm.make_color('r', 'red', '&')
        assert c.symbol == '&'

        # rewrite the old object
        cm.make_color('r', 'red')
        assert c.symbol == '&'

    def test_reassign_id(self):
        cm = ColorMap()
        c = cm.make_color('r', 'red', '#')
        assert c.id_ == 4

        # rewrite the old object
        cm.make_color('r', 'red', id_=42)
        assert c.id_ == 42

    def test_reassign_bad_id(self):
        cm = ColorMap()
        c = cm.make_color('r', 'red', '#', id_=8)
        assert c.id_ == 8

        with pytest.raises(ValueError, match='Bad id_ value: 3'):
            cm.make_color('r', 'red', id_=3)

    def test_try_to_store_not_a_color(self):
        cm = ColorMap()
        with pytest.raises(ValueError, match='Only colors can be set as values'):
            cm['foo'] = 'bar'
