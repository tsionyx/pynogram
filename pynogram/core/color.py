# -*- coding: utf-8 -*-
"""
All about nonogram colors
"""

from __future__ import unicode_literals, print_function

import re
import string
from collections import namedtuple, OrderedDict

from six import (
    integer_types, string_types,
    itervalues,
)

from pynogram.utils.other import get_named_logger

LOG = get_named_logger(__name__, __file__)


class Color(object):
    """
    Aggregate a single color different representations

    name: used for referring in clues (e.g. examples/uk.txt)
    rgb: color code to use in SVG (can be a common color name like 'green')
    symbol: ASCII symbol to show the color in terminal
    id: integer, used in solvers
    """

    def __init__(self, name, rgb, symbol=None, id_=None):
        self.name = name
        self.rgb = rgb
        self.symbol = symbol
        self.id_ = id_

    def __repr__(self):
        return '{}({!r}, {!r}, symbol={!r}, id_={!r})'.format(
            self.__class__.__name__,
            self.name, self.rgb, self.symbol, self.id_)

    @classmethod
    def white(cls):
        """Predefined white color (space) representation"""
        return cls('white', 'fff', ' ', 1)

    @classmethod
    def black(cls):
        """Predefined black color (box) representation"""
        return cls('black', '000', 'X', 2)

    RGB_TRIPLET_RE = re.compile(r'([0-9]+),[ \t]*([0-9]+),[ \t]*([0-9]+)')

    @property
    def svg_name(self):
        """Generate an SVG-readable description for a color"""

        rgb = self.rgb
        if isinstance(rgb, (list, tuple)) and len(rgb) == 3:
            return 'rgb({})'.format(','.join(map(str, rgb)))

        if len(rgb) in (3, 6) and all(letter in string.hexdigits for letter in rgb):
            return '#' + rgb

        if isinstance(rgb, string_types) and self.RGB_TRIPLET_RE.match(rgb):
            return 'rgb({})'.format(rgb)

        return rgb


class ColorMap(OrderedDict):
    """
    Store the collection of colors.
    Encapsulate creation, search and iteration among them.
    """

    def __init__(self):
        """Prevent creating from other iterables"""

        super(ColorMap, self).__init__()
        self.by_id = dict()

        for color in [Color.white(), Color.black()]:
            self.push_color(color)

        # only black and white are added ny now
        self.black_and_white = True

    def iter_colors(self):
        """Iterate over stored colors"""
        return itervalues(self)

    _MIN_ID = 1 << 2
    _SYMBOLS = string.punctuation + string.ascii_uppercase + string.ascii_lowercase

    def _new_symbol(self):
        registered_symbols = set(color.symbol for color in self.iter_colors())

        for symbol in self._SYMBOLS:
            if symbol not in registered_symbols:
                return symbol

        return None

    def push_color(self, color):
        """
        Add a color to the map
        :type color: Color
        """
        self[color.name] = color
        # for every added new color, set the map as colored
        self.black_and_white = False

    def _new_id(self):
        if self:
            max_id = max(color.id_ for color in self.iter_colors())
            # every color is a '100...' in binary
            # that was made to allow bitwise OR to signify multiple colors
            return max_id << 1
        return self._MIN_ID

    @classmethod
    def _check_id(cls, id_):
        id_ = int(id_)
        if id_ < cls._MIN_ID:
            raise ValueError('Bad id_ value: {!r}'.format(id_))

    def make_color(self, name, rgb, symbol=None, id_=None):
        """
        Make a new color, optionally filling up id and symbol
        """

        if name in self:
            color = self[name]
            LOG.info('Color %r already found: %r', name, color)

            color.rgb = rgb
            if symbol is not None:
                color.symbol = symbol
            if id_ is not None:
                self._check_id(id_)
                color.id_ = id_

            return color

        if symbol is None:
            symbol = self._new_symbol()
            if symbol is None:
                raise ValueError('No available symbols left for color {!r}'.format(name))

        if id_ is None:
            id_ = self._new_id()

        self._check_id(id_)

        new_color = Color(name, rgb, symbol=symbol, id_=id_)
        self.push_color(new_color)
        return new_color

    def find_by_id(self, id_):
        """
        Find color by given color id
        """
        return self.by_id.get(id_)

    def find_by_name(self, name):
        """
        Find color by given color name
        """
        return self.get(name)

    def __setitem__(self, key, value):
        super(ColorMap, self).__setitem__(key, value)
        try:
            self.by_id[value.id_] = value
        except AttributeError:
            raise ValueError('Only colors can be set as values in {!r}'.format(self.__class__))


class ColorBlock(namedtuple('ColorBlock', 'size color')):
    """Represent one block of colored description"""


_COLOR_DESCRIPTION_RE = re.compile('([0-9]+)(.+)')


def normalize_description_colored(row, color_map):
    """Normalize a colored nonogram description"""
    from pynogram.core.common import normalize_description

    row = normalize_description(row, color=True)

    black_color = Color.black().name

    res = []
    for block in row:
        item = None
        if isinstance(block, integer_types):
            item = (block, black_color)
        elif isinstance(block, string_types):
            match = _COLOR_DESCRIPTION_RE.match(block)
            if match:
                item = (int(match.group(1)), match.group(2))
            else:
                item = (int(block), black_color)
        elif isinstance(block, (tuple, list)) and len(block) == 2:
            item = (int(block[0]), block[1])

        if item is None:
            raise ValueError('Bad description block: {}'.format(block))
        else:
            res.append(item)

    desc = []
    for size, color_name in res:
        if color_name in color_map.by_id:
            id_ = color_name
        else:
            id_ = color_map[color_name].id_
        desc.append(ColorBlock(size, id_))

    return tuple(desc)
