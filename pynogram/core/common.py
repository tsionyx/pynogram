# -*- coding: utf-8 -*-
"""
Defines the basic terms and functions for nonogram game
"""

from __future__ import unicode_literals, print_function

import logging
import os
import re

from six import integer_types, string_types, iteritems

from pynogram.utils.collections import list_replace

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)

UNKNOWN = None  # this cell have to be solved
BOX = True
SPACE = False

DEFAULT_COLOR_NAME = 'black'
# RGB black
DEFAULT_COLOR = ((0, 0, 0), 'X')


def invert(cell_state):
    """
    Invert the given cell state:
    BOX --> SPACE
    SPACE --> BOX

    For other values return unchanged.
    """
    if cell_state == BOX:
        return SPACE
    elif cell_state == SPACE:
        return BOX

    return cell_state


def normalize_description(row, color=False):
    """
    Normalize a nonogram description for a row to the standard tuple format:
    - empty value (None, 0, '', [], ()) becomes an empty tuple
    - tuple or list becomes simply the same tuple
    - single number becomes a tuple with one item
    - a string of space-separated numbers becomes a tuple of that numbers
    """
    if not row:  # None, 0, '', [], ()
        return ()
    elif isinstance(row, (tuple, list)):
        return tuple(row)
    elif isinstance(row, integer_types):
        return row,  # it's a tuple!
    elif isinstance(row, string_types):
        blocks = row.split(' ')
        if color:
            return tuple(blocks)
        return tuple(map(int, blocks))
    else:
        raise ValueError('Bad row: %s' % row)


_COLOR_DESCRIPTION_RE = re.compile('([0-9]+)(.+)')


def normalize_description_colored(row, name_to_id_map):
    """Normalize a colored nonogram description"""
    row = normalize_description(row, color=True)

    res = []
    for block in row:
        item = None
        if isinstance(block, integer_types):
            item = (block, DEFAULT_COLOR_NAME)
        elif isinstance(block, string_types):
            match = _COLOR_DESCRIPTION_RE.match(block)
            if match:
                item = (int(match.group(1)), match.group(2))
            else:
                item = (int(block), DEFAULT_COLOR_NAME)
        elif isinstance(block, (tuple, list)) and len(block) == 2:
            item = (int(block[0]), block[1])

        if item is None:
            raise ValueError('Bad description block: {}'.format(block))
        else:
            res.append(item)

    return tuple((size, name_to_id_map[color]) for size, color in res)


INFORMAL_REPRESENTATIONS = {
    UNKNOWN: ('_', ' ', '?', '*'),
    SPACE: ('.', '0', 'O', '-'),
    BOX: ('X', '+', '#'),
}

FORMAL_ALPHABET = set(INFORMAL_REPRESENTATIONS)


def normalize_row(row):
    """
    Normalize an easy-to write row representation with a formal one
    """
    if is_color_list(row):
        return tuple(map(tuple, row))

    alphabet = set(row)
    if alphabet.issubset(FORMAL_ALPHABET):
        return row

    LOG.debug('All row symbols: %s', alphabet)
    # save original for logs and debug
    original, row = row, list(row)

    for formal, informal in iteritems(INFORMAL_REPRESENTATIONS):
        informal = set(informal) & alphabet
        if not informal:
            LOG.debug("Not found '%s' in a row", formal)
            continue

        if len(informal) > 1:
            raise ValueError(
                "Cannot contain different representations '{}' "
                "of the same state '{}' in a single row '{}'".format(
                    ', '.join(sorted(informal)), formal, original))

        informal = informal.pop()
        LOG.debug("Replace '%s' with a '%s'", informal, formal)
        list_replace(row, informal, formal)

    assert set(row).issubset(FORMAL_ALPHABET)
    return tuple(row)


def is_list_like(value):
    """Whether value is tuple or list"""
    return isinstance(value, (tuple, list))


def is_color_list(value):
    """Whether value is a list-like of list-likes"""
    # if is_list_like(value):

    # to handle both standard types and numpy arrays
    # pylint: disable=len-as-condition
    if len(value) and isinstance(value[0], (tuple, list)):
        return True

    return False
