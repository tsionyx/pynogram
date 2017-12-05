# -*- coding: utf-8 -*
"""
Defines the basic terms and functions for nonogram game
"""

from __future__ import unicode_literals, print_function

from six import integer_types, string_types

UNSURE = None  # this cell have to be solved
BOX = True
SPACE = False


def normalize_clues(row):
    """
    Normalize a nonogram row to a standard tuple format:
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
