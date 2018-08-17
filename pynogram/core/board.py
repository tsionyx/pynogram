# -*- coding: utf-8 -*-
"""
Defines a board of nonogram game
"""

from __future__ import unicode_literals, print_function, division

import logging
import os
from collections import (
    defaultdict,
    namedtuple,
)
from copy import copy

from six.moves import zip, range

try:
    # noinspection PyPackageRequirements
    import numpy as np
except ImportError:
    np = None

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE, SPACE_COLORED,
    invert,
    normalize_description,
    is_color_cell,
)
from pynogram.core.color import normalize_description_colored
from pynogram.core.renderer import Renderer
from pynogram.utils.cache import (
    memoized,
    memoized_two_args,
)
from pynogram.utils.iter import avg
from pynogram.utils.other import (
    two_powers, from_two_powers,
)
from pynogram.utils.uniq import init_once

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


class CellPosition(namedtuple('Cell', 'row_index column_index')):
    """2-D coordinates of a board cell"""


class CellState(namedtuple('CellState', 'row_index column_index color')):
    """2-D coordinates of a board cell with fixed color"""

    @property
    def position(self):
        """Get only coordinates (ignore the color)"""
        return CellPosition(self[0], self[1])

    @classmethod
    def from_position(cls, position, color):
        """Create a colored state from the CellPosition and color"""
        return cls(position[0], position[1], color)


class Board(object):
    """
    Nonogram board with columns and rows defined
    """

    def __init__(self, columns, rows, **renderer_params):
        self.columns_descriptions = self.normalize(columns)
        self.rows_descriptions = self.normalize(rows)

        init_state = self.init_cell_state
        self.cells = [[init_state] * self.width for _ in range(self.height)]
        self.validate()

        self.renderer = None
        self.set_renderer(**renderer_params)
        # you can provide custom callbacks here
        self.on_row_update = None
        self.on_column_update = None
        self.on_solution_round_complete = None
        self.on_solution_found = None
        self._finished = False

        self.solutions = []

        self.densities = {
            True: [self.line_density(True, index) for index in range(self.width)],
            False: [self.line_density(False, index) for index in range(self.height)],
        }

    def line_density(self, is_column, index):
        """
        The value in range [0..1] that shows how dense will be the solved line.
        The minimum density (0) is for the empty description.
        The maximum density is for the description that does not allow extra spaces between blocks.

        In general, the more this value the easier this line has to be solved.
        """
        if is_column:
            desc = self.columns_descriptions[index]
            full = self.height
        else:
            desc = self.rows_descriptions[index]
            full = self.width

        density = self.desc_sum(desc) / full

        assert 0 <= density <= 1
        return density

    @classmethod
    def desc_sum(cls, desc):
        """Minimal length that will be sufficient to store the given description"""
        if not desc:
            return 0

        return sum(desc) + (len(desc) - 1)

    @property
    def init_cell_state(self):
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

    def cell_solved(self, position):
        """
        Return whether the cell is completely solved
        :type position: CellPosition
        """

        i, j = position
        cell = self.cells[i][j]
        return cell != UNKNOWN

    @classmethod
    def cell_value_solved(cls, cell):
        """Whether the given value is a complete solution for a cell"""
        return cell != UNKNOWN

    @classmethod
    def colors(cls):
        """All the possible states that a cell can be in"""
        return {BOX, SPACE}

    @property
    def is_colored(self):
        """
        Whether the board has an ability
        to store more than black-and-white puzzles.

        That is simpler than do `isinstance(board, ColoredBoard)` every time.
        """
        return False

    def cell_colors(self, position):
        """
        All the possible states that the cell can be in.

        :type position: CellPosition
        :returns set
        """
        if not self.cell_solved(position):
            return self.colors()

        i, j = position
        return {self.cells[i][j]}

    def unset_state(self, cell_state):
        """
        Drop the state from the list of possible states
        for a given cell
        :type cell_state: CellState
        """
        row_index, column_index, bad_state = cell_state
        if self.cells[row_index][column_index] != UNKNOWN:
            raise ValueError('Cannot unset already set cell %s' % ([row_index, column_index]))
        self.cells[row_index][column_index] = invert(bad_state)

    def set_state(self, cell_state):
        """
        Set the color of a cell with given coordinates
        :type cell_state: CellState
        """
        row_index, column_index, color = cell_state
        self.cells[row_index][column_index] = color

    def get_row(self, index):
        """Get the board's row at given index"""
        return self.cells[index]

    def get_column(self, index):
        """Get the board's column at given index"""
        return (row[index] for row in self.cells)

    def set_row(self, index, value):
        """Set the board's row at given index with given value"""
        self.cells[index] = list(value)

        self.row_updated(index)

    def set_column(self, index, value):
        """Set the board's column at given index with given value"""
        for row_index, item in enumerate(value):
            self.cells[row_index][index] = item

        self.column_updated(index)

    def row_updated(self, row_index):
        """Runs each time the row of the board gets partially solved"""
        if self.on_row_update and callable(self.on_row_update):
            self.on_row_update(row_index=row_index, board=self)

    def column_updated(self, column_index):
        """Runs each time the column of the board gets partially solved"""
        if self.on_column_update and callable(self.on_column_update):
            self.on_column_update(column_index=column_index, board=self)

    def solution_round_completed(self):
        """
        Runs each time all the rows and the columns
        of the board gets partially solved (one solution round is complete)
        """
        if self.on_solution_round_complete and callable(self.on_solution_round_complete):
            self.on_solution_round_complete(board=self)

    def solution_found(self, solution):
        """
        Runs each time a new unique solution gets found
        """
        if self.on_solution_found and callable(self.on_solution_found):
            self.on_solution_found(solution)

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

    def draw(self, cells=None):
        """Draws a current state of a board with the renderer"""
        self.renderer.draw(cells=cells)

    def __str__(self):
        return '{}({}x{})'.format(self.__class__.__name__, self.height, self.width)

    def is_line_solved(self, row):
        """Is the given row fully solved"""

        for cell in row:
            if not self.cell_value_solved(cell):
                return False
        return True

    @property
    def is_solved_full(self):
        """Whether no unsolved cells in a board left"""
        for row in self.cells:
            if not self.is_line_solved(row):
                return False

        return True

    @property
    def solution_rate(self):
        """How much the board's cells are close to the full solution"""
        # if self.is_solved_full:
        #     return 1

        size = self.width
        return avg(self.line_solution_rate(row, size=size) for row in self.cells)

    @classmethod
    def line_solution_rate(cls, row, size=None):
        """How many cells in a given line are known to be box or space"""
        if size is None:
            size = len(row)

        return sum(1 for cell in row if cell != UNKNOWN) / size

    def row_solution_rate(self, index):
        """How many cells in a horizontal row are known to be box or space"""
        return self.line_solution_rate(self.get_row(index), size=self.width)

    def column_solution_rate(self, index):
        """How many cells in a vertical column are known to be box or space"""
        return self.line_solution_rate(self.get_column(index), size=self.height)

    @classmethod
    def cell_solution_rate(cls, cell):
        """Whether the cell solved or not"""

        if cell == UNKNOWN:
            return 0
        return 1

    @property
    def is_finished(self):
        """Return whether the solving is finished"""
        return self._finished

    def set_finished(self, finished=True):
        """Set the solving status (used by renderers)"""
        self._finished = finished

    def neighbours(self, position):
        """
        For the given cell yield
        the four possible neighbour cells.
        When the given cell is on a border,
        that number can reduce to three or two.
        :type position: CellPosition
        """
        row_index, column_index = position
        if row_index > 0:
            yield row_index - 1, column_index

        if row_index < self.height - 1:
            yield row_index + 1, column_index

        if column_index > 0:
            yield row_index, column_index - 1

        if column_index < self.width - 1:
            yield row_index, column_index + 1

    def unsolved_neighbours(self, position):
        """
        For the given cell yield the neighbour cells
        that are not completely solved yet.
        :type position: CellPosition
        """
        for pos in self.neighbours(position):
            pos = CellPosition(*pos)
            if not self.cell_solved(pos):
                yield pos

    @classmethod
    def diff(cls, old_cells, new_cells, have_deletions=False):
        """
        Yield the coordinates of cells that was changed
        in the second set of cells compared to the first one.
        """
        assert len(old_cells) == len(new_cells)
        assert len(old_cells[0]) == len(new_cells[0])

        for i, row in enumerate(new_cells):
            for j, new_cell in enumerate(row):
                old_cell = old_cells[i][j]

                if have_deletions:
                    if new_cell != old_cell:
                        yield i, j

                else:
                    if is_color_cell(old_cell):
                        if new_cell < old_cell:
                            yield i, j
                        else:
                            assert new_cell == old_cell

                    elif new_cell != old_cell:
                        assert old_cell == UNKNOWN  # '%s: %s --> %s' % ((i, j), old_cell, new_cell)
                        yield i, j

    def changed(self, old_cells):
        """
        Yield the coordinates of cells that was changed
        compared to the given set of cells.
        """
        return self.diff(old_cells, self.cells)

    def make_snapshot(self):
        """Safely save the current state of a board"""
        # the values of the cells just shallow copied here
        # do not do deepcopy to prevent too heavy tuple's `deepcopy`
        return [list(row) for row in self.cells]

    def restore(self, snapshot):
        """Restore the previously saved state of a board"""
        self.cells = snapshot

    def _current_state_in_solutions(self):
        for i, sol in enumerate(self.solutions):
            diff = next(self.diff(sol, self.cells, have_deletions=True), None)
            if diff is None:
                LOG.info('The solution is the same as the %d-th', i)
                if i > 2:
                    # faster to find repeated solutions that appear lately
                    LOG.debug('Move found solution to the beginning of the list')
                    self.solutions.insert(0, self.solutions.pop(i))
                return True

            LOG.info('The solution differs from %d-th one: first differ cell: %s', i, diff)

        return False

    def add_solution(self, copy_=True):
        """Save full solution found with contradictions"""

        LOG.info('Found one of the solutions!')

        if self._current_state_in_solutions():
            LOG.info('Solution already exists')
            return

        if copy_:
            cells = self.make_snapshot()
        else:
            cells = self.cells

        self.solution_found(cells)
        self.solutions.append(cells)

    def draw_solutions(self, only_logs=False):
        """Render the solutions"""
        if not self.solutions:
            return

        LOG.info('Number of full unique solutions: %s', len(self.solutions))

        if not only_logs:
            for solution in self.solutions:
                self.draw(cells=solution)

        if len(self.solutions) == 1:
            return

        LOG.info('Diff')
        for i, sol1 in enumerate(self.solutions):
            for j, sol2 in enumerate(self.solutions[i + 1:]):
                j = j + (i + 1)
                diff = list(self.diff(sol1, sol2, have_deletions=True))
                LOG.info('%d vs %d: %d', i, j, len(diff))


class NumpyBoard(Board):
    """
    The board that stores its state in a numpy array
    """

    def __init__(self, columns, rows, **renderer_params):
        super(NumpyBoard, self).__init__(columns, rows, **renderer_params)
        self.cells = np.array(self.cells)

    def get_column(self, index):
        # self.cells.transpose([1, 0, 2])[index]
        return self.cells.T[index]

    def set_column(self, index, value):
        """Set the board's column at given index with given value"""

        self.cells[:, index] = value
        self.column_updated(index)

    def make_snapshot(self):
        return copy(self.cells)

    def _current_state_in_solutions(self):
        for solution in self.solutions:
            if np.array_equal(self.cells, solution):
                return True

        return False


class ColoredBoard(Board):
    """
    The board with three or more colors (not simple black and white)
    """

    def __init__(self, columns, rows, color_map, **renderer_params):
        """
        :param columns: iterable of vertical clues
        :param rows: iterable of horizontal clues
        :type color_map: ColorMap
        """
        self.color_map = color_map
        super(ColoredBoard, self).__init__(columns, rows, **renderer_params)
        self._reduce_colors()

    @classmethod
    def _desc_colors(cls, description):
        return from_two_powers(block.color for block in description)

    def _reduce_colors(self):
        """
        For every cell reduce the possible colors to only those
        appeared on the corresponding row and column.
        """
        for row_index, (row, row_desc) in enumerate(zip(self.cells, self.rows_descriptions)):
            for column_index, (cell, column_desc) in enumerate(zip(row, self.columns_descriptions)):
                new_color = self._desc_colors(row_desc) & self._desc_colors(column_desc)
                new_color |= SPACE_COLORED
                if new_color != cell:
                    LOG.info('Update cell (%i, %i): %i --> %i',
                             row_index, column_index, cell, new_color)
                    row[column_index] = new_color

    @property
    def _color_map_ids(self):
        return tuple(self.color_map.by_id)

    @classmethod
    def desc_sum(cls, desc):
        res = 0
        prev_color = None
        for size, color in desc:
            res += size
            if color == prev_color:
                res += 1

            prev_color = color

        return res

    @property
    def init_cell_state(self):
        return from_two_powers(self._color_map_ids)

    def cell_solved(self, position):
        i, j = position
        cell = self.cells[i][j]
        return cell in self.colors()

    @init_once
    def colors(self):
        """
        Clue colors described the board more precisely than the color_map
        (ast it can contains excess colors like 'white').
        """
        return self._clue_colors(True) | {SPACE_COLORED}

    @init_once
    def _all_colors_as_single_number(self):
        """
        To use in the memoized functions
        """
        return from_two_powers(self.colors())

    @property
    def is_colored(self):
        return True

    @staticmethod  # much more efficient memoization
    @memoized
    def cell_as_color_set(cell_value):
        """Represent a numbered color as a set of individual colors"""
        return set(two_powers(cell_value))

    def cell_colors(self, position):
        i, j = position
        cell = self.cells[i][j]
        return self.cell_as_color_set(cell)

    def unset_state(self, cell_state):
        row_index, column_index, bad_state = cell_state
        colors = set(self.cell_colors(cell_state.position))

        bad_state = self.cell_as_color_set(bad_state)

        LOG.debug('(%d, %d) previous state: %s',
                  row_index, column_index, colors)
        LOG.debug('Bad states: %s', bad_state)

        new_value = colors - bad_state

        if set() < new_value < colors:
            LOG.debug('(%d, %d) new state: %s',
                      row_index, column_index, new_value)
            new_value = from_two_powers(new_value)
            self.cells[row_index][column_index] = new_value
        else:
            raise ValueError("Cannot unset the colors '%s' from cell %s (%s)" %
                             (bad_state, (row_index, column_index), colors))

    def set_state(self, cell_state):
        """
        Set the color of a cell with given coordinates
        :type cell_state: CellState
        """

        row_index, column_index, color = cell_state
        self.cells[row_index][column_index] = color

    def cell_value_solved(self, cell, full_colors=None):
        if full_colors is None:
            full_colors = self._all_colors_as_single_number()

        return _color_cell_solution_rate(cell, full_colors) == 1

    def cell_solution_rate(self, cell, full_colors=None):
        """
        How the cell's color set is close
        to the full solution (one color).
        """

        if full_colors is None:
            full_colors = self._all_colors_as_single_number()

        # separate out to enable memoization
        return _color_cell_solution_rate(cell, full_colors)

    def is_line_solved(self, row):
        full_colors = self._all_colors_as_single_number()
        for cell in row:
            if not self.cell_value_solved(cell, full_colors=full_colors):
                return False
        return True

    def line_solution_rate(self, row, size=None):
        """
        How many cells in a row are known to be of particular color
        """
        full_colors = self._all_colors_as_single_number()
        if size is None:
            size = len(row)

        solved = sum(self.cell_solution_rate(cell, full_colors=full_colors) for cell in row)
        return solved / size

    def _clue_colors(self, horizontal):
        """
        All the different colors appeared
        in the descriptions (rows or columns)
        """
        if horizontal:
            descriptions = self.rows_descriptions
        else:
            descriptions = self.columns_descriptions

        colors = set()
        for desc in descriptions:
            colors.update(color for size, color in desc)
        return colors

    def normalize(self, rows):
        """
        Presents given rows in standard format
        """
        return tuple(normalize_description_colored(row, self.color_map)
                     for row in rows)

    def validate(self):
        self.validate_headers(self.columns_descriptions, self.height)
        self.validate_headers(self.rows_descriptions, self.width)

        horizontal_colors = self._clue_colors(True)
        vertical_colors = self._clue_colors(False)

        if horizontal_colors != vertical_colors:
            raise ValueError('Colors differ: {} (rows) and {} (columns)'.format(
                horizontal_colors, vertical_colors))

        not_defined_colors = horizontal_colors - set(self._color_map_ids)
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

    def symbol_for_color_id(self, color_id):
        """
        Get the ASCII character to draw
        for given color based on color map
        """
        color = self.color_map.find_by_id(color_id)
        if not color:
            color = self.color_map.find_by_name(color_id)

        if color:
            return color.symbol

        return None

    def rgb_for_color_name(self, color_name):
        """
        Get the RGB triplet for given color based on color map
        """
        color = self.color_map.find_by_name(color_name)
        if not color:
            color = self.color_map.find_by_id(color_name)

        if color:
            return color.svg_name

        return None

    def color_id_by_name(self, color_name):
        """Return the color ID for given string name"""

        if color_name in self.color_map:
            return self.color_map[color_name].id_

        return None


@memoized_two_args
def _color_cell_solution_rate(cell, all_colors):
    """
    Calculate the rate of the given cell.

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
    all_colors = ColoredBoard.cell_as_color_set(all_colors)
    cell_colors = ColoredBoard.cell_as_color_set(cell) & all_colors
    current_size = len(cell_colors)

    if current_size == 1:
        # _all_colors_specific_cache[cell] = 1
        return 1

    assert current_size > 1

    full_size = len(all_colors)
    rate = full_size - current_size
    normalized_rate = rate / (full_size - 1)

    assert 0 <= normalized_rate <= 1, 'Full: {}, Cell: {}'.format(all_colors, cell_colors)

    # _all_colors_specific_cache[cell] = normalized_rate
    return normalized_rate


class ColoredNumpyBoard(ColoredBoard, NumpyBoard):
    """Colored board that uses numpy matrix to store the cells"""


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
        try:
            return NumpyBoard(*args, **kwargs)
        except AttributeError:
            return Board(*args, **kwargs)

    elif len(args) == 3:

        try:
            return ColoredNumpyBoard(*args, **kwargs)
        except AttributeError:
            return ColoredBoard(*args, **kwargs)

    raise ValueError('Bad number of *args')
