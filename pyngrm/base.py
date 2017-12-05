# -*- coding: utf-8 -*
"""
Defines the basic terms and functions for nonogram game
"""

from __future__ import unicode_literals, print_function

import logging
import os

from six import integer_types, string_types, iteritems

from pyngrm.utils import list_replace

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)

UNSURE = None  # this cell have to be solved
BOX = True
SPACE = False


def normalize_clues(row):
    """
    Normalize a nonogram clues row to a standard tuple format:
    - empty value (None, 0, '', [], ()) as an empty tuple
    - tuple or list becomes simply as a tuple
    - single number as a tuple with one item
    - a string of space-separated numbers as a tuple of that numbers
    """
    if not row:  # None, 0, '', [], ()
        return ()
    elif isinstance(row, (tuple, list)):
        return tuple(row)
    elif isinstance(row, integer_types):
        return row,  # it's a tuple!
    elif isinstance(row, string_types):
        return tuple(map(int, row.split(' ')))
    else:
        raise ValueError('Bad row: %s' % row)


INFORMAL_REPRESENTATIONS = {
    UNSURE: ('_', ' ', '?', '*'),
    SPACE: ('.', '0', 'O', '-'),
    BOX: ('X', '+'),
}


def normalize_row(row):
    """
    Normalize an easy-to write row representation with a formal one
    """
    original = row
    alphabet = set(row)
    row = list(row)
    LOG.debug('All row symbols: %s', alphabet)

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

    assert set(row) <= {BOX, SPACE, UNSURE}
    return row
