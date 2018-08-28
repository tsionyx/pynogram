# -*- coding: utf-8 -*-
"""
Defines methods to parse data file with the board defined
"""

from __future__ import unicode_literals, print_function

import json
import os
import re
from contextlib import closing
from xml.etree import ElementTree

from six import (
    string_types, binary_type,
    PY2,
)
from six.moves import range
# I don't want interpolation features, so RawConfigParser (not ConfigParser)
# noinspection PyUnresolvedReferences
from six.moves.configparser import RawConfigParser
from six.moves.urllib.error import HTTPError
from six.moves.urllib.request import urlopen

from pynogram.core.color import (
    Color,
    ColorMap,
    ColorBlock,
)
from pynogram.core.common import (
    clues,
    BLOTTED_BLOCK,
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

_INLINE_COMMENT_PREFIXES = '#;'


def parse_line(description, inline_comments=_INLINE_COMMENT_PREFIXES):
    """
    Parse a line and correctly add the description(s) to a collection
    """

    # manually strip out the comments
    # py2 cannot ignore comments on a continuation line
    # https://stackoverflow.com/q/9110428/1177288
    #
    # PY3 can do it for you with 'inline_comment_prefixes' = '#;'
    if PY2:
        for comment_prefix in inline_comments:
            pos = description.find(comment_prefix)
            if pos != -1:
                # comment line or inline comment (after a space)
                if pos == 0 or description[pos - 1].isspace():
                    description = description[:pos]

        if not description:
            return None

    # there can be trailing commas if you copy from source code
    descriptions = description.strip(',').split(',')

    # strip all the spaces and quotes
    descriptions = [desc.strip().strip("'").strip('"').strip() for desc in descriptions]
    return descriptions


def example_file(file_name=''):
    """
    Returns a path to the examples board in text files
    """
    examples_dir = os.path.join(CURRENT_DIR, 'examples')
    if not file_name:
        return examples_dir

    if os.path.isfile(file_name):
        return file_name

    file_name = os.path.join(examples_dir, file_name)
    if os.path.isfile(file_name):
        return file_name

    txt_file_name = file_name + '.txt'
    if os.path.isfile(txt_file_name):
        return txt_file_name

    # just return the original file name, don't know where is it
    return file_name


def read_example(board_file):
    """Return the board definition for given example name"""
    return read_ini(example_file(board_file))


def list_examples():
    """Return names of all the local examples"""
    for __, __, file_names in os.walk(example_file()):
        return [os.path.splitext(f)[0] for f in file_names]


def read_example_source(name):
    """Return the local example's source (do not parse)"""
    return open(example_file(name)).read()


class MultiLineConfigParser(RawConfigParser, object):
    """
    INI-file parser that allows multiple lines in a value
    to be treated like a list.
    Also adds the ';'-style inline comments (disabled in PY3)

    https://stackoverflow.com/a/11866695/1177288
    """

    def __init__(self, *args, **kwargs):
        # allow '#' or ';' as the start of a comment
        if not PY2 and 'inline_comment_prefixes' not in kwargs:
            kwargs['inline_comment_prefixes'] = _INLINE_COMMENT_PREFIXES

        # noinspection PyArgumentList
        super(MultiLineConfigParser, self).__init__(*args, **kwargs)

    def get_list(self, section, option):
        """Split the value into list, remove empty items"""
        value = self.get(section, option)
        return [x.strip() for x in value.splitlines() if x]


_COLOR_RE = re.compile(r'\((.+)\) (.+)')


def read_ini(content):
    """Return the board definition from an INI-file"""

    parser = MultiLineConfigParser()

    if isinstance(content, string_types):
        content = open(content)

    if PY2:
        # it's not deprecated for python2
        # noinspection PyDeprecation
        parser.readfp(content)  # pylint: disable=deprecated-method
    else:
        # readfp is deprecated in future versions
        parser.read_file(content)

    columns = []
    for col in parser.get_list('clues', 'columns'):
        col = parse_line(col)
        if col is not None:
            columns.extend(col)

    rows = []
    for row in parser.get_list('clues', 'rows'):
        row = parse_line(row)
        if row is not None:
            rows.extend(row)

    res = [columns, rows]

    if parser.has_section('colors'):
        colors = ColorMap()
        for color_name, color_desc in parser.items('colors'):
            match = _COLOR_RE.match(color_desc)
            # TODO: spit some info if not matched

            colors.make_color(color_name, *match.groups())

        if not colors.black_and_white:
            res.append(colors)

    return tuple(res)


class PbnNotFoundError(Exception):
    """Raised when trying to reach webpbn puzzle by non-existing id"""


class Pbn(object):
    """Grab the examples from http://webpbn.com/"""

    BASE_URL = 'http://webpbn.com'

    @classmethod
    def get_puzzle_xml(cls, _id):
        """Return the file-like object with puzzle definition in XML format"""

        # noinspection SpellCheckingInspection
        url = '{}/XMLpuz.cgi?id={}'.format(cls.BASE_URL, _id)
        return urlopen(url)

    @classmethod
    def _parse_clue(cls, clue, default_color=None):
        for block in clue.findall('count'):
            size = int(block.text)
            if size == 0:
                size = BLOTTED_BLOCK

            if default_color:
                yield size, block.attrib.get('color', default_color)
            else:
                yield size

    @classmethod
    def read(cls, _id):
        """Find and parse the columns and rows of a webpbn nonogram by id"""
        xml = cls.get_puzzle_xml(_id)
        try:
            tree = ElementTree.parse(xml)
        except ElementTree.ParseError as exc:
            str_e = str(exc)
            if str_e.startswith('syntax error'):
                raise PbnNotFoundError(_id)
            raise

        new_colors = 0
        colors = ColorMap()
        for color in tree.findall('.//color'):
            new_colors += 1
            colors.make_color(color.attrib['name'], color.text, color.attrib['char'])

        if new_colors < 3:
            default_color = None
        else:
            puzzle = tree.findall('.//puzzle[@type="grid"]')[0]
            default_color = puzzle.attrib['defaultcolor']

        columns = [tuple(cls._parse_clue(clue, default_color))
                   for clue in tree.findall('.//clues[@type="columns"]/line')]
        rows = [tuple(cls._parse_clue(clue, default_color))
                for clue in tree.findall('.//clues[@type="rows"]/line')]

        if new_colors < 3:
            return columns, rows

        return columns, rows, colors


class PbnLocal(Pbn):
    """Read locally saved puzzled from http://webpbn.com/"""

    @classmethod
    def get_puzzle_xml(cls, _id):
        return open(_id)


def _get_utf8(string):
    if isinstance(string, binary_type):
        return string.decode('utf-8', errors='ignore')

    return string


class NonogramsOrg(object):
    """
    Grab the puzzles from http://www.nonograms.org/
    or http://www.nonograms.ru/
    """

    URLS = [
        'http://www.nonograms.ru/',
        'http://www.nonograms.org/',
    ]

    def __init__(self, _id, colored=False, url=None):
        self._id = _id
        self.colored = colored
        self.url = url or self.URLS[0]

    def _puzzle_url(self):
        if self.colored:
            path = 'nonograms2'
        else:
            path = 'nonograms'

        return '{}{}/i/{}'.format(self.url, path, self._id)

    def _puzzle_html(self, colored=None, try_other=True):
        if colored is not None:
            self.colored = colored

        url = self._puzzle_url()
        try:
            with closing(urlopen(url)) as page:
                return page.read()  # pylint: disable=no-member
        except HTTPError as ex:
            if ex.code != 404:
                raise

            if try_other:
                return self._puzzle_html(colored=not colored, try_other=False)

            raise PbnNotFoundError(self._id)

    CYPHER_RE = re.compile(r'var[\s]+d\s*=\s*(\[[0-9,\[\]\s]+\]);')

    def _puzzle_cypher(self):
        html = _get_utf8(self._puzzle_html())
        match = self.CYPHER_RE.search(html)
        if not match:
            raise PbnNotFoundError(self._id, 'Not found puzzle in the HTML')

        return json.loads(match.group(1))

    # pylint: disable=invalid-name
    @classmethod
    def decipher(cls, cyphered):
        """
        Reverse engineered version of the part of the script
        http://www.nonograms.org/js/nonogram.min.059.js
        that produces a nonogram solution for given cyphered solution
        (it can be found in puzzle HTML in the form 'var d=[...]').
        """
        x = cyphered[1]
        width = x[0] % x[3] + x[1] % x[3] - x[2] % x[3]

        x = cyphered[2]
        height = x[0] % x[3] + x[1] % x[3] - x[2] % x[3]

        x = cyphered[3]
        colors_number = x[0] % x[3] + x[1] % x[3] - x[2] % x[3]

        colors = []
        x = cyphered[4]
        for i in range(colors_number):
            color_x = cyphered[i + 5]

            a = color_x[0] - x[1]
            b = color_x[1] - x[0]
            c = color_x[2] - x[3]
            # unknown_flag = color_x[3] - a - x[2]

            rgb = hex(a + 256)[3:] + hex((b + 256 << 8) + c)[3:]
            colors.append(rgb)

        solution = [[0] * width for _ in range(height)]

        a = colors_number + 5
        x = cyphered[a]
        solution_size = x[0] % x[3] * (x[0] % x[3]) + x[1] % x[3] * 2 + x[2] % x[3]

        x = cyphered[a + 1]
        for i in range(solution_size):
            y = cyphered[a + 2 + i]
            vv = y[0] - x[0] - 1

            for j in range(y[1] - x[1]):
                v = j + vv
                solution[y[3] - x[3] - 1][v] = y[2] - x[2]

        return [colors, solution]

    def definition(self):
        """
        Return the definition of the puzzle
        in form of final solution
        """
        cypher = self._puzzle_cypher()
        return self.decipher(cypher)

    def parse(self):
        """
        Find and parse the colors and solution of
        a 'nonograms.org' puzzle by id
        """
        colors, solution = self.definition()
        columns, rows = clues(solution, white_color_code=0)

        if len(colors) == 1:
            return columns, rows

        color_map = ColorMap()
        # reassign the IDs
        id_map = {}
        for old_id, color in enumerate(colors, 1):
            is_black = (color == '000000')
            if is_black:
                name = Color.black().name
            else:
                name = 'color-{}'.format(old_id)
                color_map.make_color(name, color)

            id_map[old_id] = name

        columns = [[ColorBlock(size, id_map[old_color])
                    for size, old_color in col] for col in columns]
        rows = [[ColorBlock(size, id_map[old_color])
                 for size, old_color in r] for r in rows]

        return columns, rows, color_map

    @classmethod
    def read(cls, _id, colored=False):
        """
        Search for puzzle on any of available http://www.nonograms.* sites
        """
        for index, base_url in enumerate(cls.URLS):
            try:
                return cls(_id, colored=colored, url=base_url).parse()
            except PbnNotFoundError:
                if index == len(cls.URLS) - 1:  # raise if no other choices
                    raise
