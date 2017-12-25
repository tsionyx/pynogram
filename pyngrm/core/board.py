# -*- coding: utf-8 -*
"""
Defines a board of nonogram game
"""

from __future__ import unicode_literals, print_function, division

import logging
import os
import time

import numpy as np
from six.moves import zip, range

import pyngrm
from pyngrm.core import (
    UNKNOWN, BOX, SPACE,
    normalize_description,
    invert,
)
from pyngrm.core.fsm import (
    solve_row,
    NonogramError,
    NonogramFSM,
)
from pyngrm.utils.collections import avg, max_safe
from pyngrm.utils.priority_dict import PriorityDict

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)

pyngrm.core.fsm.LOG.setLevel(logging.WARNING)


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


class Board(object):
    """
    Nonogram board with columns and rows defined
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, columns, rows, renderer=Renderer, **renderer_params):
        """
        :type renderer: Renderer | type[Renderer]
        """
        self.columns_descriptions = self.normalize(columns)
        self.rows_descriptions = self.normalize(rows)

        self.renderer = renderer
        if isinstance(self.renderer, type):
            self.renderer = self.renderer(self, **renderer_params)
        elif isinstance(self.renderer, Renderer):
            self.renderer.board_init(self)
        else:
            raise TypeError('Bad renderer: %s' % renderer)

        self.cells = np.array([[UNKNOWN] * self.width for _ in range(self.height)])
        self.validate()

        # you can provide custom callbacks here
        self.on_row_update = None
        self.on_column_update = None
        self.on_solution_round_complete = None
        self._solved = False

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
        return avg(self.row_solution_rate(row) for row in self.cells)

    @classmethod
    def row_solution_rate(cls, row):
        """How many cells in a row are known to be box or space"""
        return sum(1 for cell in row if cell != UNKNOWN) / len(row)

    # pylint: disable=too-many-arguments, too-many-locals
    def solve_row(self, index, is_column, priority, jobs_queue,
                  contradiction_mode=False):
        """
        Solve one line with FSM.
        If line gets partially solved,
        put the crossed lines into queue
        """

        start = time.time()

        if is_column:
            row_desc, row = self.columns_descriptions[index], self.cells.T[index]
            desc = 'column'
        else:
            row_desc, row = self.rows_descriptions[index], self.cells[index]
            desc = 'row'

        pre_solution_rate = self.row_solution_rate(row)

        # do not check solved lines in trusted mode
        if not contradiction_mode and pre_solution_rate == 1:
            return

        LOG.debug('Solving %s %s: %s. Partial: %s. Priority: %s',
                  index, desc, row_desc, row, priority)

        updated = solve_row(row_desc, row)

        if self.row_solution_rate(updated) > pre_solution_rate:
            LOG.debug('New info on %s %s: %s', desc, index, updated)
            LOG.debug('Queue: %s', jobs_queue)

            for i, (pre, post) in enumerate(zip(row, updated)):
                if pre != post:
                    assert pre == UNKNOWN
                    assert post in (BOX, SPACE)

                    jobs_queue[(not is_column, i)] = priority - 1
            LOG.debug('Queue: %s', jobs_queue)

            if is_column:
                self.cells[:, index] = updated
                self.column_updated(index)
            else:
                self.cells[index] = updated
                self.row_updated(index)

        LOG.debug('%ss solution: %.6f sec', desc.title(), time.time() - start)

    @property
    def solved(self):
        """Return whether the nonogram is completely solved"""
        return self._solved

    def solve(self, parallel=False, contradiction_mode=False):
        """Solve the nonogram to the most with FSM using priority queue"""
        if self.solution_rate == 1:
            return

        lines_solved = 0

        if parallel:
            # TODO: add parallel logic here
            LOG.info("Using several processes to solve")

        start = time.time()

        # every job is a tuple (is_column, index)
        #
        # Why `is_column`, not `is_row`?
        # To assign more priority to the rows:
        # when adding row, `is_column = False = 0`
        # when adding column, `is_column = True = 1`
        # heap always pops the lowest item, so the rows will go first

        line_jobs = PriorityDict()

        for row_index in range(self.height):
            line_jobs[(False, row_index)] = 0

        for column_index in range(self.width):
            line_jobs[(True, column_index)] = 0

        while line_jobs:
            (is_column, index), priority = line_jobs.pop_smallest()
            self.solve_row(index, is_column, priority, line_jobs,
                           contradiction_mode=contradiction_mode)
            lines_solved += 1

        # all the following actions applied only to verified solving
        if contradiction_mode:
            return

        self.solution_round_completed()

        self._solved = True
        if self.solution_rate != 1:
            LOG.warning('The nonogram is not solved full. The rate is %.4f', self.solution_rate)
        LOG.info('Full solution: %.6f sec', time.time() - start)
        LOG.info('Lines solved: %i', lines_solved)

    def try_contradiction(self, row_index, column_index,
                          assumption=BOX, propagate=True):
        """
        Try to find if the given cell can be in an assumed state.
        If the contradiction is found, set the cell
        in an inverted state and propagate the changes if needed.
        """
        # already solved
        if self.cells[row_index][column_index] != UNKNOWN:
            return

        save = self.cells.copy()
        contradiction = False

        try:
            try:
                LOG.debug('Pretend that (%i, %i) is %s',
                          row_index, column_index, assumption)
                self.cells[row_index][column_index] = assumption
                self.solve(contradiction_mode=True)
            except NonogramError:
                contradiction = True
            else:
                if self.solution_rate == 1:
                    LOG.warning("Found one of the solutions!")
        finally:
            # rollback solved cells
            self.cells = save
            if contradiction:
                LOG.info("Found contradiction at (%i, %i)",
                         row_index, column_index)
                self.cells[row_index][column_index] = invert(assumption)

                # try to solve with additional info
                if propagate:
                    self.solve()

    def _contradictions_round(
            self, assumption,
            propagate_on_cell=True, by_rows=True):
        """
        Solve the nonogram with contradictions
        by trying every cell and the basic `solve` method.

        :param assumption: which state to try: BOX or SPACE
        :param propagate_on_cell: how to propagate changes:
        after each solved cell or in the end of the row
        :param by_rows: iterate by rows (left-to-right) or by columns (top-to-bottom)
        """

        if by_rows:
            for solved_row in range(self.height):
                if self.row_solution_rate(self.cells[solved_row]) == 1:
                    continue

                LOG.info('Trying to assume on row %i', solved_row)
                for solved_column in range(self.width):
                    self.try_contradiction(
                        solved_row, solved_column,
                        assumption=assumption,
                        propagate=propagate_on_cell
                    )

                if not propagate_on_cell:
                    self.solve()
        else:
            for solved_column in range(self.width):
                if self.row_solution_rate(self.cells.T[solved_column]) == 1:
                    continue

                LOG.info('Trying to assume on column %i', solved_column)
                for solved_row in range(self.height):
                    self.try_contradiction(
                        solved_row, solved_column,
                        assumption=assumption,
                        propagate=propagate_on_cell
                    )

                if propagate_on_cell:
                    self.solve()

    def solve_with_contradictions(
            self, propagate_on_row=False, by_rows=True):
        """
        Solve the nonogram to the most with contradictions
        and the basic `solve` method.

        :param propagate_on_row: how to propagate changes:
        in the end of the row or after each solved cell
        :param by_rows: iterate by rows (left-to-right) or by columns (top-to-bottom)
        """

        self.solve()
        if self.solution_rate == 1:
            LOG.info('No need to solve with contradictions')
            return

        LOG.warning('Trying to solve using contradictions method')
        propagate_on_cell = not propagate_on_row
        self._solved = False
        start = time.time()

        solved = self.solution_rate
        counter = 0

        assumption = BOX  # try the different assumptions every time

        while True:
            counter += 1
            LOG.warning('Contradiction round %i (assumption %s)', counter, assumption)

            self._contradictions_round(
                assumption,
                propagate_on_cell=propagate_on_cell,
                by_rows=by_rows)

            if self.solution_rate > solved:
                self.solution_round_completed()

            if self.solution_rate == 1 or solved == self.solution_rate:
                break

            solved = self.solution_rate
            assumption = invert(assumption)

        self._solved = True
        if self.solution_rate != 1:
            LOG.warning('The nonogram is not solved full (with contradictions). '
                        'The rate is %.4f', self.solution_rate)
        LOG.info('Full solution: %.6f sec', time.time() - start)
        LOG.info('Cache hit rate: %.4f%%', NonogramFSM.solutions_cache().hit_rate * 100.0)


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
