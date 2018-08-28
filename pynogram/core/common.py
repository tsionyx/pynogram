# -*- coding: utf-8 -*-
"""
Defines the basic terms and functions for nonogram game
"""

from __future__ import unicode_literals, print_function

try:
    # available since 3.4
    from enum import Enum
except ImportError:
    Enum = object

from six import (
    integer_types, string_types,
    iteritems,
)
from six.moves import range

from pynogram.core.color import (
    Color, ColorBlock,
)
from pynogram.utils.iter import list_replace
from pynogram.utils.other import get_named_logger

LOG = get_named_logger(__name__, __file__)


class NonogramError(ValueError):
    """
    Represents an error occurred when trying
    to solve a nonogram which has an internal contradiction.
    """


UNKNOWN = None  # this cell has to be solved

# The size of the block is unknown
# (try to solve by hand https://webpbn.com/19407 to grasp the concept)
# Intentionally made not an integer to prevent treating it like a number.
BLOTTED_BLOCK = object()


class BlackAndWhite(Enum):
    """
    Enums are faster than simple integers
    """
    WHITE = Color.white().id_
    BLACK = Color.black().id_


# but boolean constants are even faster than Enums
BOX = True  # BlackAndWhite.BLACK
SPACE = False  # BlackAndWhite.WHITE

# for colored puzzles only integer is allowed
SPACE_COLORED = Color.white().id_


def invert(cell_state):
    """
    Invert the given cell state:
    BOX --> SPACE
    SPACE --> BOX

    For other values return unchanged.
    """
    if cell_state == BOX:
        return SPACE

    if cell_state == SPACE:
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

    if isinstance(row, (tuple, list)):
        return tuple(row)

    if isinstance(row, integer_types):
        return row,  # it's a tuple!

    if isinstance(row, string_types):
        blocks = row.split()
        if color:
            return tuple(blocks)
        return tuple(map(int, blocks))

    raise ValueError('Bad row: %s' % row)


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
    alphabet = set(row)
    if alphabet.issubset(FORMAL_ALPHABET):
        return row

    if is_color_list(row):
        return row

    LOG.debug('All row symbols: %s', alphabet)
    # save original for logs and debug
    original, row = row, list(row)

    for formal, informal in iteritems(INFORMAL_REPRESENTATIONS):
        informal = set(informal) & alphabet
        if not informal:
            LOG.debug('Not found %r in a row', formal)
            continue

        if len(informal) > 1:
            raise ValueError(
                "Cannot contain different representations '{}' "
                "of the same state '{}' in a single row '{}'".format(
                    ', '.join(sorted(informal)), formal, original))

        informal = informal.pop()
        LOG.debug('Replace %r with a %r', informal, formal)
        list_replace(row, informal, formal)

    assert set(row).issubset(FORMAL_ALPHABET)
    return tuple(row)


def is_list_like(value):
    """Whether value is tuple or list"""
    return isinstance(value, (tuple, list))


BLACK_AND_WHITE_COLORS = (UNKNOWN, SPACE, BOX)


def is_color_cell(value):
    """
    Whether the value is a combination of several colors
    """
    try:
        value + 1
    except TypeError:
        return False  # color is always integer

    return value not in BLACK_AND_WHITE_COLORS


def is_color_list(value):
    """
    Whether value is a list of black and white or colored puzzle

    If it's a colored row, the value will have values other than
    (UNKNOWN, SPACE=1, BOX=2)
    """

    # check `len` to handle both standard types and numpy arrays
    if len(value):
        return any(is_color_cell(item) for item in value)

    return False


def clues(solution_matrix, white_color_code=SPACE):
    """
    Generate nonogram description (columns and rows)
    from a solution matrix.
    """
    height = len(solution_matrix)
    if height == 0:
        return (), ()

    width = len(solution_matrix[0])
    if width == 0:
        return (), ()

    colors = set()

    columns = []
    for col_index in range(width):
        column = []

        row_index = 0
        while row_index < height:
            block_begin = row_index
            color_number = solution_matrix[row_index][col_index]

            while (row_index < height) and (solution_matrix[row_index][col_index] == color_number):
                row_index += 1

            block_size = row_index - block_begin
            if (block_size > 0) and (color_number != white_color_code):
                colors.add(color_number)
                column.append(ColorBlock(block_size, color_number))

        columns.append(column)

    rows = []
    for row_index in range(height):
        row = []

        col_index = 0
        while col_index < width:
            block_begin = col_index
            color_number = solution_matrix[row_index][col_index]

            while (col_index < width) and (solution_matrix[row_index][col_index] == color_number):
                col_index += 1

            block_size = col_index - block_begin
            if (block_size > 0) and (color_number != white_color_code):
                colors.add(color_number)
                row.append(ColorBlock(block_size, color_number))

        rows.append(row)

    # black and white, ignore colors
    if len(colors) == 1:
        columns = [[block.size for block in col] for col in columns]
        rows = [[block.size for block in r] for r in rows]

    return columns, rows
