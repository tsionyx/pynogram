# -*- coding: utf-8 -*-
"""
Define a board of nonogram game
"""

from __future__ import unicode_literals, print_function, division

try:
    from abc import ABC
except ImportError:
    from abc import ABCMeta

    # https://stackoverflow.com/a/38668373
    ABC = ABCMeta(str('ABC'), (object,), {'__slots__': ()})

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
from pynogram.utils.cache import init_once
from pynogram.utils.iter import avg
from pynogram.utils.other import (
    two_powers, from_two_powers,
    get_named_logger,
)

LOG = get_named_logger(__name__, __file__)


class CellPosition(namedtuple('Cell', 'row_index column_index')):
    """2-D coordinates of a grid cell"""


class CellState(namedtuple('CellState', 'row_index column_index color')):
    """2-D coordinates of a grid cell with fixed color"""

    @property
    def position(self):
        """Get only coordinates (ignore the color)"""
        return CellPosition(self[0], self[1])

    @classmethod
    def from_position(cls, position, color):
        """Create a colored state from the CellPosition and color"""
        return cls(position[0], position[1], color)


def call_if_callable(func, *args, **kwargs):
    """Call the function with given parameters if it is callable"""

    if func and callable(func):
        return func(*args, **kwargs)

    return None


class RenderedMixin(object):
    """
    This mixin adds an ability to render the grid, i.e. a rectangular table of cells
    """

    def __init__(self, **kwargs):
        self.renderer = None
        self.set_renderer(**kwargs)

    def set_renderer(self, renderer=Renderer, **kwargs):
        """
        Allow to specify renderer even in the middle of the solving

        :type renderer: Renderer | type[Renderer]
        """

        if isinstance(renderer, type):
            self.renderer = renderer(self, **kwargs)
        elif isinstance(renderer, Renderer):
            self.renderer = renderer
            self.renderer.board_init(self)
        else:
            raise TypeError('Bad renderer: {!r}'.format(renderer))

    def draw(self, cells=None):
        """Draw a grid with the renderer"""
        self.renderer.draw(cells=cells)


class NonogramGrid(RenderedMixin):
    """
    Abstract nonogram grid with descriptions and cells
    """

    def __init__(self, columns, rows, cells=None, **renderer_params):
        """
        :param columns: iterable of vertical clues
        :param rows: iterable of horizontal clues
        """

        self.columns_descriptions = self.normalize(columns)
        self.rows_descriptions = self.normalize(rows)
        self.cells = cells or self.make_cells()
        self.validate()

        # setup the renderer after all the validations
        super(NonogramGrid, self).__init__(**renderer_params)

        # callbacks
        self.on_row_update = None
        self.on_column_update = None

    @property
    def init_cell_state(self):
        """Initial value of a single cell"""
        raise NotImplementedError()

    @property
    def height(self):
        """The height of the playing area"""
        return len(self.rows_descriptions)

    @property
    def width(self):
        """The width of the playing area"""
        return len(self.columns_descriptions)

    def make_cells(self):
        """Construct default cells set"""
        init_state = self.init_cell_state
        return [[init_state] * self.width for _ in range(self.height)]

    def normalize(self, clues):
        """
        Present clues in standard format
        """
        raise NotImplementedError()

    def validate(self):
        """
        Validate that the grid is valid:
        - all the descriptions of a row (column) can fit into width (height) of the grid
        - the vertical and horizontal descriptions define the same colors
        """
        self.validate_descriptions_size(self.columns_descriptions, self.height)
        self.validate_descriptions_size(self.rows_descriptions, self.width)
        self.validate_colors(self.columns_descriptions, self.rows_descriptions)

    @classmethod
    def validate_descriptions_size(cls, descriptions, max_size):
        """
        Validate that all the clues can fit into the grid
        """
        raise NotImplementedError()

    def validate_colors(self, vertical, horizontal):
        """
        Validate that the colors defined in vertical
        and horizontal descriptions are the same.
        """
        raise NotImplementedError()

    @classmethod
    def colors(cls):
        """
        All the colors that can appear on a grid

        :rtype: set
        """
        raise NotImplementedError()

    def unset_color(self, cell_state):
        """
        Drop the state from the list of possible states
        for a given cell
        :type cell_state: CellState
        """
        raise NotImplementedError()

    def set_color(self, cell_state):
        """
        Set the color of a cell with given coordinates
        :type cell_state: CellState
        """
        row_index, column_index, color = cell_state
        self.cells[row_index][column_index] = color

    @property
    def is_colored(self):
        """
        Whether the grid has an ability
        to store more than 2 colors (black and white only?)

        That is simpler than do `isinstance(board, ColoredBoard)` every time.
        """
        raise NotImplementedError()

    def get_row(self, index):
        """Get the grid's row at given index"""
        return self.cells[index]

    def get_column(self, index):
        """Get the grid's column at given index"""
        return (row[index] for row in self.cells)

    # noinspection PyUnusedLocal
    def set_row(self, index, value):
        """Set the grid's row at given index"""
        self.cells[index] = list(value)

        self.row_updated(index)

    # noinspection PyUnusedLocal
    def set_column(self, index, value):
        """Set the grid's column at given index"""
        for row_index, item in enumerate(value):
            self.cells[row_index][index] = item

        self.column_updated(index)

    def __str__(self):
        return '{}({}x{})'.format(self.__class__.__name__, self.height, self.width)

    def row_updated(self, row_index):
        """Run each time the row gets partially solved"""
        call_if_callable(self.on_row_update, row_index, board=self)

    def column_updated(self, column_index):
        """Run each time the column gets partially solved"""
        call_if_callable(self.on_column_update, column_index, board=self)


class SolvableGrid(NonogramGrid, ABC):
    """
    Nonogram grid with various solution metrics defined
    """

    def __init__(self, columns, rows, cells=None, **kwargs):
        super(SolvableGrid, self).__init__(columns, rows, cells=cells, **kwargs)

        self._finished = False

        # custom callbacks
        self.on_solution_round_complete = None

    @property
    def solution_rate(self):
        """How much the board's cells are close to the full solution"""
        # if self.is_solved_full:
        #     return 1

        size = self.width
        return avg(self.line_solution_rate(row, size=size) for row in self.cells)

    @property
    def is_solved_full(self):
        """Whether no unsolved cells left"""
        raise NotImplementedError()

    @classmethod
    def line_solution_rate(cls, row, size=None):
        """How many cells in a given line are known to be solved"""
        raise NotImplementedError()

    def row_solution_rate(self, index):
        """How many cells in a horizontal row are known to be box or space"""
        return self.line_solution_rate(self.get_row(index), size=self.width)

    def column_solution_rate(self, index):
        """How many cells in a vertical column are known to be box or space"""
        return self.line_solution_rate(self.get_column(index), size=self.height)

    @classmethod
    def cell_solution_rate(cls, cell):
        """How much the cell's value is close to solved"""
        raise NotImplementedError()

    def is_cell_solved(self, position):
        """
        Decide whether the cell is completely solved
        :type position: CellPosition
        :rtype: bool
        """
        raise NotImplementedError()

    def cell_colors(self, position):
        """
        All the possible states that the cell at given position can be in.

        :type position: CellPosition
        :rtype: set
        """
        if not self.is_cell_solved(position):
            return self.colors()

        i, j = position
        return {self.cells[i][j]}

    def solution_round_completed(self):
        """
        Runs each time all the rows and the columns
        of the board gets partially solved (one solution round is complete)
        """
        call_if_callable(self.on_solution_round_complete, board=self)

    @property
    def is_finished(self):
        """Return whether the solving is finished"""
        return self._finished

    def set_finished(self, finished=True):
        """Set the solving status (used by renderers)"""
        self._finished = finished


class MultipleSolutionGrid(NonogramGrid, ABC):
    """
    Nonogram grid with additional support to store multiple states of a grid.
    Also substituting for the current cells is supported.
    """

    def __init__(self, columns, rows, cells=None, **renderer_params):
        super(MultipleSolutionGrid, self).__init__(columns, rows, cells=cells, **renderer_params)

        self.solutions = []

        # custom callbacks
        self.on_solution_found = None
        self.on_restored = None

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

    def restored(self, snapshot):
        """
        Run each time a grid's cells restored
        """
        call_if_callable(self.on_restored, snapshot)

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
        """Save one of the full solutions"""

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

    def solution_found(self, solution):
        """
        Run each time a new unique solution found
        """
        call_if_callable(self.on_solution_found, solution)

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


class ReducibleGrid(SolvableGrid, MultipleSolutionGrid, ABC):
    """
    A nonogram grid which supports reducing,
    i.e. temporary trimming the solved rows and columns
    with appropriate descriptions changes.
    """

    def __init__(self, columns, rows, cells=None, **renderer_params):
        super(ReducibleGrid, self).__init__(columns, rows, cells=cells, **renderer_params)

        # save original descriptions to support reducing
        self.descriptions = (self.columns_descriptions, self.rows_descriptions)

        self.solved_columns = None
        self.solved_rows = None

    @classmethod
    def _space_value(cls):
        raise NotImplementedError()

    @classmethod
    def _reduce_orthogonal_description(cls, col_desc, cell_value, first_rows=False):
        raise NotImplementedError()

    @classmethod
    def _reduce_edge(cls, cells, straight_desc, orthogonal_desc,
                     line_solution_rate_func, first=True):
        # top, bottom
        solved_rows = []

        if first:
            rows_enum = list(enumerate(zip(cells, straight_desc)))
        else:
            rows_enum = reversed(list(enumerate(zip(cells, straight_desc))))

        for row_index, (row, row_desc) in rows_enum:
            if line_solution_rate_func(row_index) != 1:
                break

            LOG.info('Reducing solved row (column) %i: %r', row_index, row_desc)

            if first:
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
                cls._reduce_orthogonal_description(col_desc, cell, first_rows=first)

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
            self.row_solution_rate, first=True)
        self.restore(cells)  # to correctly check line_solution_rate further

        last_solved_rows, cells = self._reduce_edge(
            cells, rows_descriptions, columns_descriptions,
            self.row_solution_rate, first=False)
        self.restore(cells)  # to correctly check line_solution_rate further

        self.columns_descriptions = self.normalize(columns_descriptions)
        self.rows_descriptions = self.normalize(rows_descriptions)

        # ====== COLS ====== #
        # transpose the matrix
        width = len(cells[0])
        cells = [list(self.get_column(col_index)) for col_index in range(width)]
        first_solved_columns, cells = self._reduce_edge(
            cells, columns_descriptions, rows_descriptions,
            self.column_solution_rate, first=True)

        # transpose it back
        height = len(cells[0])
        # to correctly check line_solution_rate further
        self.restore([[col[row_index] for col in cells] for row_index in range(height)])

        last_solved_columns, cells = self._reduce_edge(
            cells, columns_descriptions, rows_descriptions,
            self.column_solution_rate, first=False)

        # transpose it back
        height = len(cells[0])
        # to correctly check line_solution_rate further
        self.restore([[col[row_index] for col in cells] for row_index in range(height)])

        self.columns_descriptions = self.normalize(columns_descriptions)
        self.rows_descriptions = self.normalize(rows_descriptions)

        for sol_index, solution in enumerate(self.solutions):
            if first_solved_columns:
                solution = [row[len(first_solved_columns):] for row in solution]
            if last_solved_columns:
                solution = [row[:-len(last_solved_columns)] for row in solution]

            if first_solved_rows:
                solution = solution[len(first_solved_rows):]
            if last_solved_rows:
                solution = solution[:-len(last_solved_rows)]

            assert len(solution) == self.height
            assert len(solution[0]) == self.width

            self.solutions[sol_index] = solution

        reduced_size = self.height, self.width

        if original_size == reduced_size:
            LOG.warning('The board size: %r', original_size)
        else:
            LOG.warning('Reduced the board: %r --> %r', original_size, reduced_size)

        self.solved_columns = (first_solved_columns, last_solved_columns)
        self.solved_rows = (first_solved_rows, last_solved_rows)
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


class BaseBoard(ReducibleGrid, ABC):
    """
    Base nonogram board with support of the following:
    - solving metrics
    - storing multiple solutions
    - reducing the solved lines
    """

    def __init__(self, columns, rows, cells=None, **renderer_params):
        super(BaseBoard, self).__init__(columns, rows, cells=cells, **renderer_params)

        # True =_column; False = row
        self.densities = {
            True: [self.line_density(True, index) for index in range(self.width)],
            False: [self.line_density(False, index) for index in range(self.height)],
        }

    @classmethod
    def desc_sum(cls, desc):
        """Minimal length that will be sufficient to store the given description"""
        raise NotImplementedError()

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
            if not self.is_cell_solved(pos):
                yield pos


class NumpyBoard(BaseBoard, ABC):
    """
    The board that stores its state in a numpy array
    """

    def __init__(self, columns, rows, cells=None, **renderer_params):
        super(NumpyBoard, self).__init__(columns, rows, cells=cells, **renderer_params)
        self.restore(self.cells)

    def get_column(self, index):
        # self.cells.transpose([1, 0, 2])[index]
        return self.cells.T[index]

    def set_column(self, index, value):
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


class BlackBoard(BaseBoard):
    """
    Black-and-white nonogram board
    """

    @property
    def init_cell_state(self):
        return UNKNOWN

    def normalize(self, clues):
        return tuple(map(normalize_description, clues))

    @classmethod
    def validate_descriptions_size(cls, descriptions, max_size):
        for clue in descriptions:
            need_cells = sum(clue)
            if clue:
                # also need at least one space between every two blocks
                need_cells += len(clue) - 1

            LOG.debug('Clue: %s; Need: %s; Available: %s.',
                      clue, need_cells, max_size)
            if need_cells > max_size:
                raise ValueError('Cannot allocate clue {} in just {} cells'.format(
                    list(clue), max_size))

    def validate_colors(self, vertical, horizontal):
        boxes_in_columns = sum(sum(block) for block in vertical)
        boxes_in_rows = sum(sum(block) for block in horizontal)
        if boxes_in_rows != boxes_in_columns:
            raise ValueError('Number of boxes differs: {} (rows) and {} (columns)'.format(
                boxes_in_rows, boxes_in_columns))

    def is_cell_solved(self, position):
        i, j = position
        cell = self.cells[i][j]
        return cell != UNKNOWN

    @classmethod
    def colors(cls):
        return {BOX, SPACE}

    @property
    def is_colored(self):
        return False

    def unset_color(self, cell_state):
        row_index, column_index, bad_state = cell_state
        if self.cells[row_index][column_index] != UNKNOWN:
            raise ValueError('Cannot unset already set cell %s' % ([row_index, column_index]))
        self.cells[row_index][column_index] = invert(bad_state)

    @property
    def is_solved_full(self):
        for row in self.cells:
            for cell in row:
                if cell == UNKNOWN:
                    return False
        return True

    @classmethod
    def line_solution_rate(cls, row, size=None):
        """How many cells in a given line are known to be box or space"""

        if size is None:
            size = len(row)

        return sum(1 for cell in row if cell != UNKNOWN) / size

    @classmethod
    def cell_solution_rate(cls, cell):
        """Whether the cell solved or not"""

        if cell == UNKNOWN:
            return 0
        return 1

    @classmethod
    def desc_sum(cls, desc):
        if not desc:
            return 0

        return sum(desc) + (len(desc) - 1)

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


class ReduceColorToBlackMixin(MultipleSolutionGrid, ABC):
    """
    Allow to represent color board as a black-and white board
    by creating additional underlying board with the colors replaced to BOX and SPACE.
    """

    def create_single_colored_board(self, box_color):
        """
        Create an equivalent BlackBoard from the current board
        """
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

        new_board = BlackBoard(columns_descriptions, rows_descriptions)
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


class ColorBoard(BaseBoard, ReduceColorToBlackMixin):
    """
    The board with three or more colors (not simple black and white)
    """

    def __init__(self, columns, rows, color_map, cells=None, **renderer_params):
        """
        :type color_map: ColorMap
        """
        self.color_map = color_map
        super(ColorBoard, self).__init__(columns, rows, cells=cells, **renderer_params)

        self._cell_rate_memo = {}
        self._reduce_colors()

    @property
    def init_cell_state(self):
        return from_two_powers(self._color_map_ids)

    def normalize(self, clues):
        return tuple(normalize_description_colored(row, self.color_map)
                     for row in clues)

    @classmethod
    def validate_descriptions_size(cls, descriptions, max_size):
        """
        Validate that all the clues can fit into the grid
        """

        for clue in descriptions:
            need_cells = 0

            prev_color = None
            for number, color in clue:
                if prev_color == color:
                    need_cells += 1
                need_cells += number
                prev_color = color

            LOG.debug('Clue: %s; Need: %s; Available: %s.',
                      clue, need_cells, max_size)
            if need_cells > max_size:
                raise ValueError('Cannot allocate clue {} in just {} cells'.format(
                    list(clue), max_size))

    def validate_colors(self, vertical, horizontal):
        horizontal_colors = self._clue_colors(True)
        vertical_colors = self._clue_colors(False)

        if horizontal_colors != vertical_colors:
            raise ValueError('Colors differ: {} (rows) and {} (columns)'.format(
                horizontal_colors, vertical_colors))

        not_defined_colors = horizontal_colors - set(self._color_map_ids)
        if not_defined_colors:
            raise ValueError('Some colors not defined: {}'.format(
                tuple(not_defined_colors)))

        vertical_colors = defaultdict(int)
        for block in vertical:
            for block_len, block_color in block:
                vertical_colors[block_color] += block_len

        horizontal_colors = defaultdict(int)
        for block in horizontal:
            for block_len, block_color in block:
                horizontal_colors[block_color] += block_len

        if horizontal_colors != vertical_colors:
            horizontal_colors = set(horizontal_colors.items())
            vertical_colors = set(vertical_colors.items())

            raise ValueError('Color boxes differ: {} (rows) and {} (columns)'.format(
                horizontal_colors, vertical_colors))

    @init_once
    def colors(self):
        """
        Clue colors described the board more precisely than the color_map
        (as it can contain excess colors like 'white').
        """
        return self._clue_colors(True) | {SPACE_COLORED}

    def unset_color(self, cell_state):
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
            raise ValueError("Cannot unset the colors {!r} from cell {} ({})".format(
                bad_state, (row_index, column_index), colors))

    @property
    def is_colored(self):
        return True

    @property
    def is_solved_full(self):
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

    def is_cell_solved(self, position):
        i, j = position
        cell = self.cells[i][j]
        return cell in self.colors()

    def cell_colors(self, position):
        i, j = position
        cell = self.cells[i][j]
        return self.cell_as_color_set(cell)

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

    # ATTENTION: be aware not to change the result of memoized function
    # as it can affect all the future invocations
    @staticmethod  # much more efficient memoization (compared to @classmethod)
    @memoized
    def cell_as_color_set(cell_value):
        """Represent a numbered color as a set of individual colors"""
        return set(two_powers(cell_value))

    @init_once
    def _all_colors_as_single_number(self):
        """
        To use in the memoized functions
        """
        return from_two_powers(self.colors())

    @classmethod
    def _desc_colors(cls, description):
        return from_two_powers(block.color for block in description)

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

        return self.create_single_colored_board(box_color), mapping


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
    all_colors = ColorBoard.cell_as_color_set(all_colors)
    cell_colors = ColorBoard.cell_as_color_set(cell) & all_colors
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


class NumpyBlackBoard(BlackBoard, NumpyBoard):
    """Black-and-white board that uses numpy matrix to store the cells"""


class NumpyColorBoard(ColorBoard, NumpyBoard):
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
            return NumpyBlackBoard(*args, **kwargs)
        except AttributeError:
            return BlackBoard(*args, **kwargs)

    elif len(args) == 3:

        try:
            return NumpyColorBoard(*args, **kwargs)
        except AttributeError:
            return ColorBoard(*args, **kwargs)

    raise ValueError('Bad number of *args')
