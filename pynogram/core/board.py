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

from memoized import memoized
from six.moves import zip, range, map

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
    NonogramError,
)
from pynogram.core.color import (
    normalize_description_colored,
    ColorBlock,
)
from pynogram.core.renderer import Renderer
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
        # save original descriptions to support reducing
        self.descriptions = (self.columns_descriptions, self.rows_descriptions)

        init_state = self.init_cell_state
        self.cells = [[init_state] * self.width for _ in range(self.height)]
        self.validate()

        self.renderer = None
        self.set_renderer(**renderer_params)

        # custom callbacks
        self.on_row_update = None
        self.on_column_update = None
        self.on_solution_round_complete = None
        self.on_solution_found = None
        self.on_restored = None

        self._finished = False

        self.solutions = []

        # True =_column; False = row
        self.densities = {
            True: [self.line_density(True, index) for index in range(self.width)],
            False: [self.line_density(False, index) for index in range(self.height)],
        }

        self.solved_columns = None
        self.solved_rows = None

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

    def restored(self, snapshot):
        """
        Run each time a board cells restored
        """
        if self.on_restored and callable(self.on_restored):
            self.on_restored(snapshot)

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

    @property
    def is_solved_full(self):
        """Whether no unsolved cells in a board left"""
        for row in self.cells:
            for cell in row:
                if cell == UNKNOWN:
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
        self.restored(snapshot)

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

    @classmethod
    def _space_value(cls):
        return SPACE

    @classmethod
    def _reduce_orthogonal_description(cls, col_desc, cell_value, first_rows=False):
        assert cell_value == BOX
        if first_rows:
            first_block = col_desc[0]
            if first_block == 1:
                col_desc.pop(0)
            else:
                col_desc[0] = first_block - 1
        else:
            last_block = col_desc[-1]
            if last_block == 1:
                col_desc.pop()
            else:
                col_desc[-1] = last_block - 1

    @classmethod
    def _reduce_edge(cls, cells, straight_desc, orthogonal_desc,
                     line_solution_rate_func, first_rows=True):
        # top, bottom
        solved_rows = []

        if first_rows:
            rows_enum = list(enumerate(zip(cells, straight_desc)))
        else:
            rows_enum = reversed(list(enumerate(zip(cells, straight_desc))))

        for row_index, (row, row_desc) in rows_enum:
            if line_solution_rate_func(row_index) != 1:
                break

            LOG.info('Reducing solved row (column) %i: %r', row_index, row_desc)

            if first_rows:
                # remove from the board description
                removed_desc = straight_desc.pop(0)

                # remove the cells itself
                cells = cells[1:]

                # save solved
                solved_rows.append(row)
            else:
                removed_desc = straight_desc.pop()
                cells = cells[:-1]
                solved_rows.insert(0, row)

            LOG.info('Removed description %r', removed_desc)

            for col_index, (cell, col_desc) in enumerate(
                    zip(row, orthogonal_desc)):
                if not col_desc:  # skip empty description
                    continue

                if cell == cls._space_value():
                    continue

                LOG.info('Reducing orthogonal description %i: %r', col_index, col_desc)
                cls._reduce_orthogonal_description(col_desc, cell, first_rows=first_rows)

        return solved_rows, cells

    def reduce(self):
        """
        Cut out fully solved lines from the edges of the board, e.g.

           1 1 1
           1 1 1 1            1 1 1
        4  X X X X
        1  ? 0 ? 0   -->    1 ? 0 ?
        1  ? X ? 0          1 ? X ?
        """

        columns_descriptions = [list(col_desc) for col_desc in self.columns_descriptions]
        rows_descriptions = [list(row_desc) for row_desc in self.rows_descriptions]

        original_size = self.height, self.width

        # ====== ROWS ====== #
        cells = self.make_snapshot()
        first_solved_rows, cells = self._reduce_edge(
            cells, rows_descriptions, columns_descriptions,
            self.row_solution_rate, first_rows=True)
        self.restore(cells)  # to correctly check line_solution_rate further

        last_solved_rows, cells = self._reduce_edge(
            cells, rows_descriptions, columns_descriptions,
            self.row_solution_rate, first_rows=False)
        self.restore(cells)  # to correctly check line_solution_rate further

        self.columns_descriptions = self.normalize(columns_descriptions)
        self.rows_descriptions = self.normalize(rows_descriptions)

        # ====== COLS ====== #
        # transpose the matrix
        width = len(cells[0])
        cells = [list(self.get_column(col_index)) for col_index in range(width)]
        first_solved_columns, cells = self._reduce_edge(
            cells, columns_descriptions, rows_descriptions,
            self.column_solution_rate, first_rows=True)

        # transpose it back
        height = len(cells[0])
        # to correctly check line_solution_rate further
        self.restore([[col[row_index] for col in cells] for row_index in range(height)])

        last_solved_columns, cells = self._reduce_edge(
            cells, columns_descriptions, rows_descriptions,
            self.column_solution_rate, first_rows=False)

        # transpose it back
        height = len(cells[0])
        # to correctly check line_solution_rate further
        self.restore([[col[row_index] for col in cells] for row_index in range(height)])

        self.columns_descriptions = self.normalize(columns_descriptions)
        self.rows_descriptions = self.normalize(rows_descriptions)

        # ================== #
        self.solved_columns = (first_solved_columns, last_solved_columns)
        self.solved_rows = (first_solved_rows, last_solved_rows)

        for sol_index, solution in enumerate(self.solutions):
            first, last = self.solved_rows
            if first:
                solution = solution[len(first):]
            if last:
                solution = solution[:-len(last)]

            first, last = self.solved_columns
            if first:
                solution = [row[len(first):] for row in solution]
            if last:
                solution = [row[:-len(last)] for row in solution]

            assert len(solution) == self.height
            assert len(solution[0]) == self.width

            self.solutions[sol_index] = solution

        reduced_size = self.height, self.width

        if original_size == reduced_size:
            LOG.warning('The board size: %r', original_size)
        else:
            LOG.warning('Reduced the board: %r --> %r', original_size, reduced_size)

        return self.solved_columns, self.solved_rows

    @classmethod
    def restore_cells(cls, cells, edge_rows, edge_columns):
        """
        Return matrix by given center and the edges.
        Current implementation restores the columns first then the rows.
        """
        restore_rows = False
        if edge_rows:
            if edge_rows[0] or edge_rows[1]:
                restore_rows = True

        restore_cols = False
        if edge_columns:
            if edge_columns[0] or edge_columns[1]:
                restore_cols = True

        if not restore_rows and not restore_cols:
            return cells

        # do not touch original
        cells = [list(row) for row in cells]

        if edge_columns:
            first, last = edge_columns
            # insert one column at a time
            for col in reversed(first):
                assert len(col) == len(cells)
                cells = [[col_cell] + row for col_cell, row in zip(col, cells)]

            # append one column at a time
            for col in last:
                assert len(col) == len(cells)
                cells = [row + [col_cell] for col_cell, row in zip(col, cells)]

        if edge_rows:
            first, last = edge_rows
            # insert one row at a time
            for row in reversed(first):
                assert len(row) == len(cells[-1])
                cells.insert(0, row)

            # append one column at a time
            for row in last:
                assert len(row) == len(cells[0])
                cells.append(row)

        return cells

    def restore_reduced(self):
        """
        Restore the original size of the board if it was reduced before.
        Do it before rendering or yielding the final result.
        """

        current = self.cells
        reduced_size = self.height, self.width
        assert reduced_size == (len(current), len(current[0]))

        for sol_index, solution in enumerate(self.solutions):
            cells = self.restore_cells(solution, self.solved_rows, self.solved_columns)
            self.restore(cells)
            self.solutions[sol_index] = self.cells

        cells = self.restore_cells(current, self.solved_rows, self.solved_columns)
        self.restore(cells)

        self.columns_descriptions, self.rows_descriptions = self.descriptions

        original_size = self.height, self.width
        assert original_size == (len(self.cells), len(self.cells[0]))

        if original_size != reduced_size:
            LOG.warning('Restored the board: %r --> %r', reduced_size, original_size)


class NumpyBoard(Board):
    """
    The board that stores its state in a numpy array
    """

    def __init__(self, columns, rows, **renderer_params):
        super(NumpyBoard, self).__init__(columns, rows, **renderer_params)
        self.restore(self.cells)

    def get_column(self, index):
        # self.cells.transpose([1, 0, 2])[index]
        return self.cells.T[index]

    def set_column(self, index, value):
        """Set the board's column at given index with given value"""

        self.cells[:, index] = value
        self.column_updated(index)

    def make_snapshot(self):
        return copy(self.cells)

    def restore(self, snapshot):
        self.cells = np.array(snapshot)

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

        self._cell_rate_memo = {}
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

    # ATTENTION: be aware not to change the result of memoized function
    # as it can affect all the future invocations

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

    def cell_solution_rate(self, cell):
        """
        How the cell's color set is close
        to the full solution (one color).
        """

        try:
            return self._cell_rate_memo[cell]
        except KeyError:
            full_colors = self._all_colors_as_single_number()
            self._cell_rate_memo[cell] = value = _color_cell_solution_rate(cell, full_colors)
            return value

    @property
    def is_solved_full(self):
        """Whether no unsolved cells in a board left"""

        cell_solution_rate_func = self.cell_solution_rate

        for row in self.cells:
            for cell in row:
                if cell_solution_rate_func(cell) != 1:
                    return False
        return True

    def line_solution_rate(self, row, size=None):
        """
        How many cells in a row are known to be of particular color
        """

        if size is None:
            size = len(row)

        cell_solution_rate_func = self.cell_solution_rate

        solved = sum(cell_solution_rate_func(cell) for cell in row)
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

    @classmethod
    def _space_value(cls):
        return SPACE_COLORED

    @classmethod
    def _reduce_orthogonal_description(cls, col_desc, cell_value, first_rows=False):
        if first_rows:
            block = col_desc[0]  # type: ColorBlock
        else:
            block = col_desc[-1]  # type: ColorBlock

        assert block.color == cell_value

        if block.size == 1:
            if first_rows:
                col_desc.pop(0)
            else:
                col_desc.pop()
        else:
            new_block = ColorBlock(block.size - 1, cell_value)
            if first_rows:
                col_desc[0] = new_block
            else:
                col_desc[-1] = new_block

    def _create_single_colored_board(self, box_color):
        columns_descriptions = []
        for col_desc in self.columns_descriptions:
            # filter out any other colors
            new_desc = [block.size for block in col_desc if block.color == box_color]
            columns_descriptions.append(new_desc)

        rows_descriptions = []
        for row_desc in self.rows_descriptions:
            # filter out any other colors
            new_desc = [block.size for block in row_desc if block.color == box_color]
            rows_descriptions.append(new_desc)

        color_mapping = {
            box_color: BOX,
            SPACE_COLORED: SPACE,

            # both BOX and SPACE
            from_two_powers((box_color, SPACE_COLORED)): UNKNOWN,
        }

        cells = []
        for row in self.cells:
            # for colors other than box_color, just replace to SPACE
            new_row = [
                color_mapping.get(cell, SPACE)
                for cell in row
            ]
            cells.append(new_row)

        new_board = Board(columns_descriptions, rows_descriptions)
        new_board.restore(cells)

        self._assign_callbacks_to_single_colored_board(new_board, color_mapping)
        return new_board

    def _assign_callbacks_to_single_colored_board(self, new_board, color_to_single_mapping):
        from pynogram.core import propagation

        updatable_colors = tuple(color_to_single_mapping.keys())
        single_to_color = dict((v, k) for k, v in color_to_single_mapping.items())

        def on_column_update(column_index, board):
            column = board.get_column(column_index)

            updated = []
            for index, updated_cell in enumerate(column):
                current_color = self.cells[index][column_index]
                if current_color not in updatable_colors:
                    continue

                new_color = single_to_color[updated_cell]

                if new_color != current_color:
                    updated.append(index)
                    self.cells[index][column_index] = new_color

            if updated:
                # can be false positives if the solved line
                # has bad translations from SPACE to specific colors
                propagation.solve(self, column_indexes=(column_index,),
                                  row_indexes=updated,
                                  contradiction_mode=True)
                self.column_updated(column_index)

        def on_row_update(row_index, board):
            row = board.get_row(row_index)

            updated = []
            for index, updated_cell in enumerate(row):
                current_color = self.cells[row_index][index]
                if current_color not in updatable_colors:
                    continue

                new_color = single_to_color[updated_cell]

                if new_color != current_color:
                    updated.append(index)
                    self.cells[row_index][index] = new_color

            if updated:
                # can be false positives if the solved line
                # has bad translations from SPACE to specific colors
                propagation.solve(self, row_indexes=(row_index,),
                                  column_indexes=updated,
                                  contradiction_mode=True)
                self.row_updated(row_index)

        # noinspection PyUnusedLocal
        def on_solution_found(solution):
            try:
                LOG.info('Checking the solution (found on single-colored)...')
                propagation.solve(self, contradiction_mode=True)
            except NonogramError as ex:
                # self.draw()
                LOG.error('Single colored solution is bad: %r', ex)
                raise

            self.add_solution()

        def on_restored(snapshot):
            for row_index, (row, colored_row) in enumerate(zip(snapshot, self.cells)):
                for column_index, (cell, current_color) in enumerate(zip(row, colored_row)):
                    if current_color not in updatable_colors:
                        continue

                    new_color = single_to_color[cell]

                    if new_color != current_color:
                        self.cells[row_index][column_index] = new_color

        new_board.on_column_update = on_column_update
        new_board.on_row_update = on_row_update
        new_board.on_solution_found = on_solution_found
        new_board.on_restored = on_restored

    def reduce_to_single_color(self):
        """
        Try to represent the unsolved cells
        as another black-and-white board.

        :return pair (black and white board, mapping from old to new colors)
        """

        all_colors = set()
        for row in self.cells:
            all_colors |= set(row)

        all_colors = [set(self.cell_as_color_set(color)) for color in all_colors]
        unsolved_colors = [color for color in all_colors if len(color) > 1]

        if not unsolved_colors or len(unsolved_colors) > 1:
            return None, None

        box_color = unsolved_colors[0]
        assert len(box_color) == 2
        assert SPACE_COLORED in box_color

        box_color.discard(SPACE_COLORED)
        box_color, = box_color

        mapping = {box_color: BOX, SPACE_COLORED: SPACE}

        return self._create_single_colored_board(box_color), mapping


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
