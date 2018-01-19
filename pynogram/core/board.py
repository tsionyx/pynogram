# -*- coding: utf-8 -*
"""
Defines a board of nonogram game
"""

from __future__ import unicode_literals, print_function, division

import logging
import os
from collections import defaultdict

from six.moves import zip, range

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE, invert,
    normalize_description,
    normalize_description_colored,
    DEFAULT_COLOR, DEFAULT_COLOR_NAME,
    is_list_like,
)
from pynogram.utils.collections import avg, max_safe

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


class Renderer(object):
    """Defines the abstract renderer for a nonogram board"""

    def __init__(self, board=None):
        self.cells = None
        self.board = None
        self.board_init(board)

    def board_init(self, board=None):
        """Initialize renderer's properties dependent on board it draws"""
        if board:
            LOG.info("Init '%s' renderer with board '%s'",
                     self.__class__.__name__, board)
        else:
            if self.board:
                return  # already initialized, do nothing
            board = _DummyBoard()
        self.board = board

    @property
    def full_height(self):
        """The full visual height of a board"""
        return self.header_height + self.board.height

    @property
    def full_width(self):
        """The full visual width of a board"""
        return self.side_width + self.board.width

    @property
    def header_height(self):
        """The size of the header block with columns descriptions"""
        return max_safe(map(len, self.board.columns_descriptions), default=0)

    @property
    def side_width(self):
        """The width of the side block with rows descriptions"""
        return max_safe(map(len, self.board.rows_descriptions), default=0)

    def render(self):
        """Actually print out the board"""
        raise NotImplementedError()

    def draw(self):
        """Calculate all the cells and draw an image of the board"""
        self.draw_header()
        self.draw_side()
        self.draw_grid()
        self.render()

    def draw_header(self):
        """
        Changes the internal state to be able to draw columns descriptions
        """
        raise NotImplementedError()

    def draw_side(self):
        """
        Changes the internal state to be able to draw rows descriptions
        """
        raise NotImplementedError()

    def draw_grid(self):
        """
        Changes the internal state to be able to draw a main grid
        """
        raise NotImplementedError()


class Board(object):  # pylint: disable=too-many-public-methods
    """
    Nonogram board with columns and rows defined
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, columns, rows, **renderer_params):
        self.columns_descriptions = self.normalize(columns)
        self.rows_descriptions = self.normalize(rows)

        init_state = self.init_cell_state()
        self.cells = [[init_state] * self.width for _ in range(self.height)]
        self.validate()

        self.renderer = None
        self.set_renderer(**renderer_params)
        # you can provide custom callbacks here
        self.on_row_update = None
        self.on_column_update = None
        self.on_solution_round_complete = None
        self._solved = False

    @classmethod
    def init_cell_state(cls):
        """Initial value of a board cell"""
        return UNKNOWN

    def set_renderer(self, renderer=Renderer, **renderer_params):
        """
        Allow to specify renderer even in the middle of the solving

        :type renderer: Renderer | type[Renderer]
        """

        if isinstance(renderer, type):
            self.renderer = renderer(self, **renderer_params)
        elif isinstance(renderer, Renderer):
            self.renderer = renderer
            self.renderer.board_init(self)
        else:
            raise TypeError('Bad renderer: %s' % renderer)

    @classmethod
    def cell_solved(cls, cell):
        """Return whether the cell is completely solved"""
        return cell != UNKNOWN

    @classmethod
    def colors(cls):
        """All the possible states that the cell can be in"""
        return {BOX, SPACE}

    def unset_state(self, bad_state, row_index, column_index):
        """
        Drop the state from the list of possible states
        for a given cell
        """
        self.cells[row_index][column_index] = invert(bad_state)

    def get_row(self, index):
        """Get the board's row at given index"""
        return self.cells[index]

    def get_column(self, index):
        """Get the board's column at given index"""
        return tuple(row[index] for row in self.cells)

    def set_row(self, index, value):
        """Set the board's row at given index with given value"""
        self.cells[index] = list(value)

        self.row_updated(index)

    def set_column(self, index, value):
        """Set the board's column at given index with given value"""
        for row_index, item in enumerate(value):
            self.cells[row_index][index] = item

        self.column_updated(index)

    # pylint: disable=not-callable
    def row_updated(self, row_index):
        """Runs each time the row of the board gets partially solved"""
        if self.on_row_update and callable(self.on_row_update):
            self.on_row_update(row_index=row_index, board=self)

    # pylint: disable=not-callable
    def column_updated(self, column_index):
        """Runs each time the column of the board gets partially solved"""
        if self.on_column_update and callable(self.on_column_update):
            self.on_column_update(column_index=column_index, board=self)

    # pylint: disable=not-callable
    def solution_round_completed(self):
        """
        Runs each time all the rows and the columns
        of the board gets partially solved (one solution round is complete)
        """
        if self.on_solution_round_complete and callable(self.on_solution_round_complete):
            self.on_solution_round_complete(board=self)

    @classmethod
    def normalize(cls, rows):
        """
        Presents given rows in standard format
        """
        return tuple(map(normalize_description, rows))

    @property
    def height(self):
        """The height of the playing area"""
        return len(self.rows_descriptions)

    @property
    def width(self):
        """The width of the playing area"""
        return len(self.columns_descriptions)

    def validate(self):
        """
        Validate that the board is valid:
        - all the descriptions of a row (column) can fit into width (height) of the board
        - the vertical and horizontal descriptions define the same number of boxes
        """
        self.validate_headers(self.columns_descriptions, self.height)
        self.validate_headers(self.rows_descriptions, self.width)

        boxes_in_rows = sum(sum(block) for block in self.rows_descriptions)
        boxes_in_columns = sum(sum(block) for block in self.columns_descriptions)
        if boxes_in_rows != boxes_in_columns:
            raise ValueError('Number of boxes differs: {} (rows) and {} (columns)'.format(
                boxes_in_rows, boxes_in_columns))

    @classmethod
    def validate_headers(cls, rows, max_size):
        """
        Validate that the all the rows can fit into the given size
        """
        for row in rows:
            need_cells = sum(row)
            if row:
                # also need at least one space between every two blocks
                need_cells += len(row) - 1

            LOG.debug('Row: %s; Need: %s; Available: %s.',
                      row, need_cells, max_size)
            if need_cells > max_size:
                raise ValueError('Cannot allocate row {} in just {} cells'.format(
                    list(row), max_size))

    def draw(self):
        """Draws a current state of a board with the renderer"""
        self.renderer.draw()

    def __str__(self):
        return '{}({}x{})'.format(self.__class__.__name__, self.height, self.width)

    @property
    def solution_rate(self):
        """How many cells in the whole board are known to be box or space"""
        return avg(self.line_solution_rate(row) for row in self.cells)

    @classmethod
    def line_solution_rate(cls, row):
        """How many cells in a given line are known to be box or space"""
        return sum(1 for cell in row if cell != UNKNOWN) / len(row)

    def row_solution_rate(self, index):
        """How many cells in a horizontal row are known to be box or space"""
        return self.line_solution_rate(self.get_row(index))

    def column_solution_rate(self, index):
        """How many cells in a vertical column are known to be box or space"""
        return self.line_solution_rate(self.get_column(index))

    @property
    def solved(self):
        """Return whether the nonogram is completely solved"""
        return self._solved

    def set_solved(self, solved=True):
        """Set the solving status (used by renderers)"""
        self._solved = solved


class ColoredBoard(Board):
    """
    The board with three or more colors (not simple black and white)
    """

    def __init__(self, columns, rows, color_map, **renderer_params):
        self.color_map = color_map
        self.color_map[DEFAULT_COLOR_NAME] = DEFAULT_COLOR
        super(ColoredBoard, self).__init__(columns, rows, **renderer_params)

    def init_cell_state(self):
        return tuple(self.color_map) + (SPACE,)

    @classmethod
    def cell_solved(cls, cell):
        if is_list_like(cell):
            colors = tuple(set(cell))
            assert colors
            return len(colors) == 1

        return True

    def colors(self):
        return set(self.color_map) | {SPACE}

    def unset_state(self, bad_state, row_index, column_index):
        colors = self.cells[row_index][column_index]
        if not is_list_like(bad_state):
            bad_state = [bad_state]
        LOG.debug('(%d, %d) previous state: %s',
                  row_index, column_index, colors)
        LOG.debug('Bad states: %s', bad_state)

        if set(bad_state).intersection(set(colors)):
            new_value = [color for color in colors if color not in bad_state]

            LOG.debug('(%d, %d) new state: %s',
                      row_index, column_index, new_value)
            self.cells[row_index][column_index] = new_value

    def cell_solution_rate(self, cell):
        """
        How the cell's color set is close
        to the full solution (one color).

        The formula is like that:
        `rate = (N - n) / (N - 1)`, where
        N = full puzzle color set
        n = current color set for given cell,

        in particular:
        a) when the cell is completely unsolved
           rate = (N - N) / (N - 1) = 0
        b) when the cell is solved
           rate = (N - 1) / (N - 1) = 1
        """

        if is_list_like(cell):
            cell_colors = set(cell)
        else:
            cell_colors = {cell}

        full_colors = self.colors()
        rate = len(full_colors) - len(cell_colors & full_colors)
        normalized_rate = rate / (len(full_colors) - 1)

        assert 0 <= normalized_rate <= 1, 'Full: {}, Cell: {}'.format(full_colors, cell_colors)
        return normalized_rate

    def line_solution_rate(self, row):
        """
        How many cells in a row are known to be of particular color
        """
        solved = sum(self.cell_solution_rate(cell) for cell in row)
        return solved / len(row)

    def _colors(self, horizontal):
        """
        All the different colors appeared
        in the descriptions (rows or columns)
        """
        if horizontal:
            descriptions = self.rows_descriptions
        else:
            descriptions = self.columns_descriptions

        colors = set()
        for block in descriptions:
            for __, block_color in block:
                colors.add(block_color)
        return colors

    @classmethod
    def normalize(cls, rows):
        """
        Presents given rows in standard format
        """
        return tuple(map(normalize_description_colored, rows))

    def validate(self):
        self.validate_headers(self.columns_descriptions, self.height)
        self.validate_headers(self.rows_descriptions, self.width)

        horizontal_colors = self._colors(True)
        vertical_colors = self._colors(False)

        if horizontal_colors != vertical_colors:
            raise ValueError('Colors differ: {} (rows) and {} (columns)'.format(
                horizontal_colors, vertical_colors))

        not_defined_colors = horizontal_colors - set(self.color_map)
        if not_defined_colors:
            raise ValueError('Some colors not defined: {}'.format(
                tuple(not_defined_colors)))

        horizontal_colors = defaultdict(int)
        for block in self.rows_descriptions:
            for block_len, block_color in block:
                horizontal_colors[block_color] += block_len

        vertical_colors = defaultdict(int)
        for block in self.columns_descriptions:
            for block_len, block_color in block:
                vertical_colors[block_color] += block_len

        if horizontal_colors != vertical_colors:
            horizontal_colors = set(horizontal_colors.items())
            vertical_colors = set(vertical_colors.items())

            raise ValueError('Color boxes differ: {} (rows) and {} (columns)'.format(
                horizontal_colors, vertical_colors))

    @classmethod
    def validate_headers(cls, rows, max_size):
        for row in rows:
            need_cells = 0

            prev_color = None
            for number, color in row:
                if prev_color == color:
                    need_cells += 1
                need_cells += number
                prev_color = color

            LOG.debug('Row: %s; Need: %s; Available: %s.',
                      row, need_cells, max_size)
            if need_cells > max_size:
                raise ValueError('Cannot allocate row {} in just {} cells'.format(
                    list(row), max_size))

    def char_for_color(self, color_name):
        """
        Return the ASCII character to draw
        for given color based on color map
        """
        return self.color_map[color_name][1]

    def rgb_for_color(self, color_name):
        """Return the RGB triplet for given color based on color map"""
        return self.color_map[color_name][0]


class _DummyBoard(object):  # pylint: disable=too-few-public-methods
    """
    Stub for renderer init in case of it created before the board.
    """
    rows_descriptions = columns_descriptions = ()
    width = height = 0


def _solve_on_space_hints(board, hints):
    """
    Pseudo solving with spaces given
    """
    # assert len(hints) == len(board.rows_descriptions)
    for i, (spaces_hint, row) in enumerate(zip(hints, board.rows_descriptions)):
        assert len(spaces_hint) == len(row)
        cells = []
        for space_size, box_size in zip(spaces_hint, row):
            cells.extend([SPACE] * space_size)
            cells.extend([BOX] * box_size)

        # pad with spaces
        solution = cells + ([SPACE] * (board.width - len(cells)))
        board.cells[i] = solution


def make_board(*args, **kwargs):
    """Produce the black-and-white or colored nonogram"""
    if len(args) == 2:
        return Board(*args, **kwargs)

    elif len(args) == 3:
        return ColoredBoard(*args, **kwargs)

    raise ValueError('Bad number of *args')
