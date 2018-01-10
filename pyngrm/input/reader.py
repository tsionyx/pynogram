# -*- coding: utf-8 -*
"""
Defines methods to parse data file with the board defined
"""

from __future__ import unicode_literals, print_function

import os
import re

from six import string_types, PY2
# noinspection PyUnresolvedReferences
from six.moves.configparser import RawConfigParser  # I don't want interpolation features

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
    project_dir = os.path.dirname(os.path.dirname(CURRENT_DIR))
    examples_dir = os.path.join(project_dir, 'examples')
    if not file_name:
        return examples_dir

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


# pylint: disable=too-few-public-methods
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
        if os.path.isfile(content):
            parser.read(content)

    else:
        parser.readfp(content)

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
        colors = dict()
        for color_name, color_desc in parser.items('colors'):
            match = _COLOR_RE.match(color_desc)
            # TODO: spit some info if not matched
            colors[color_name] = match.groups()

        if colors:
            res.append(colors)

    return tuple(res)
