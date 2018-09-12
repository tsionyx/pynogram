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
    with_metaclass,
)
from six.moves import range

from pynogram.core.color import (
    Color, ColorBlock,
)
from pynogram.utils.iter import (
    list_replace,
    expand_generator,
)
from pynogram.utils.other import get_named_logger

LOG = get_named_logger(__name__, __file__)


class NonogramError(ValueError):
    """
    Represents an error occurred when trying
    to solve a nonogram which has an internal contradiction.
    """


UNKNOWN = None  # this cell has to be solved


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


def _line_clues(line, white_color_code):
    size = len(line)

    description = []
    colors = set()

    index = 0
    while index < size:
        block_begin = index
        color_number = line[index]

        while (index < size) and (line[index] == color_number):
            index += 1

        block_size = index - block_begin
        if (block_size > 0) and (color_number != white_color_code):
            colors.add(color_number)
            description.append(ColorBlock(block_size, color_number))

    return description, colors


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

    all_colors = set()

    columns = []
    for col_index in range(width):
        column = [solution_matrix[row_index][col_index] for row_index in range(height)]
        description, colors = _line_clues(column, white_color_code)
        all_colors |= colors
        columns.append(description)

    rows = []
    for row_index in range(height):
        row = solution_matrix[row_index]
        description, colors = _line_clues(row, white_color_code)
        all_colors |= colors
        rows.append(description)

    # black and white, ignore colors
    if len(all_colors) == 1:
        columns = [[block.size for block in col] for col in columns]
        rows = [[block.size for block in r] for r in rows]

    return columns, rows


class _BlottedMeta(type):
    """Redefine __repr__ to reduce noise in logs"""

    def __repr__(cls):
        return 'BLOTTED'


class BlottedBlock(with_metaclass(_BlottedMeta, object)):
    """
    The size of the block is unknown
    (try to solve by hand https://webpbn.com/19407 to grasp the concept)
    Intentionally made not an integer to prevent treating it like a number.
    """

    @classmethod
    def how_many(cls, description):
        """The number of blotted blocks in the description row"""
        counter = 0

        if not is_list_like(description):
            return 0

        for block in description:
            if block == cls:
                counter += 1

            if is_list_like(block):
                if block[0] == cls:
                    counter += 1

        return counter

    @classmethod
    @expand_generator
    def replace_with_1(cls, description):
        """
        Every blotted block spans a minimum of 1 cell
        """
        for block in description:
            if is_list_like(block):
                if block.size == cls:
                    block = ColorBlock(1, block.color)

            elif block == cls:
                block = 1

            yield block

    @classmethod
    def matches(cls, description, line):
        """
        Whether the given solved line
        matches the blotted description
        """

        colored = is_color_list(line)

        white_color = SPACE_COLORED if colored else SPACE
        line_clues, __ = _line_clues(line, white_color_code=white_color)

        if len(description) != len(line_clues):
            return False

        for actual, from_line in zip(description, line_clues):
            if not colored:
                from_line = from_line[0]

            if actual == from_line:
                continue

            if actual == cls:
                if from_line > 0:
                    continue

            return False

        return True


@expand_generator
def partial_sums(blocks, colored=None):
    """
    Calculate the partial sum of the blocks
    """

    if not blocks:
        return

    if colored is None:
        colored = isinstance(blocks[0], ColorBlock)

    if colored:
        sum_so_far = blocks[0].size
        yield sum_so_far

        for i, block in enumerate(blocks[1:], 1):
            size, color = block
            sum_so_far += size

            if blocks[i - 1].color == color:
                # plus at least one space
                sum_so_far += 1

            yield sum_so_far
    else:
        sum_so_far = blocks[0]
        yield sum_so_far

        for block in blocks[1:]:
            sum_so_far += block + 1
            yield sum_so_far


def slack_space(line_size, desc):
    """How much space left when the line fully shifted to one edge"""
    if not desc:
        return line_size

    desc = BlottedBlock.replace_with_1(desc)
    sums = partial_sums(desc)
    min_line_size = sums[-1]
    return line_size - min_line_size
