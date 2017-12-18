# -*- coding: utf-8 -*
"""
Defines a board of nonogram game
"""

from __future__ import unicode_literals, print_function, division

import logging
import os
import time

import numpy as np
from six.moves import zip

from pyngrm.base import UNSURE, normalize_clues, BOX, invert, SPACE
from pyngrm.fsm import solve_row, NonogramError
from pyngrm.renderer import (
    Renderer,
    StreamRenderer,
    AsciiRenderer,
)
from pyngrm.utils import avg, terminating_mp_pool

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


class BaseBoard(object):
    """
    Basic nonogram board with columns and rows defined
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, columns, rows, renderer=Renderer):
        """
        :type renderer: Renderer | type[Renderer]
        """
        self.vertical_clues = self.normalize(columns)
        self.horizontal_clues = self.normalize(rows)

        self.renderer = renderer
        if isinstance(self.renderer, type):
            self.renderer = self.renderer(self)
        elif isinstance(self.renderer, Renderer):
            self.renderer.board_init(self)
        else:
            raise TypeError('Bad renderer: %s' % renderer)

        self.cells = np.array([[UNSURE] * self.width for _ in range(self.height)])
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
        return tuple(map(normalize_clues, rows))

    @property
    def height(self):
        """The height of the playing area"""
        return len(self.horizontal_clues)

    @property
    def width(self):
        """The width of the playing area"""
        return len(self.vertical_clues)

    def validate(self):
        """
        Validate that the board is valid:
        - all the clues in a row (a column) can fit into width (height) of the board
        - the vertical and horizontal clues defines the same number of boxes
        """
        self.validate_headers(self.vertical_clues, self.height)
        self.validate_headers(self.horizontal_clues, self.width)

        boxes_in_rows = sum(sum(block) for block in self.horizontal_clues)
        boxes_in_columns = sum(sum(block) for block in self.vertical_clues)
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
        return sum(1 for cell in row if cell != UNSURE) / len(row)

    def solve_rows(self, horizontal=True, parallel=False):
        """Solve every row (or column) with FSM"""
        start = time.time()

        if horizontal:
            clue_cells_mapping = zip(self.horizontal_clues, self.cells)
            desc = 'row'
        else:
            clue_cells_mapping = zip(self.vertical_clues, self.cells.T)
            desc = 'column'

        rows_scores = []
        rows_to_solve = []

        for i, (clue, row) in enumerate(clue_cells_mapping):
            pre_solution_rate = self.row_solution_rate(row)
            if pre_solution_rate == 1:
                continue  # already solved

            rows_scores.append((i, pre_solution_rate))
            LOG.debug('Solving %s %s: %s. Partial: %s',
                      i, desc, clue, row)

            rows_to_solve.append((clue, row))

        if parallel:
            with terminating_mp_pool() as pool:
                solved_rows = pool.map(solve_row, rows_to_solve)
        else:
            solved_rows = map(solve_row, rows_to_solve)

        for (i, pre_solution_rate), updated in zip(rows_scores, solved_rows):
            if self.row_solution_rate(updated) > pre_solution_rate:
                LOG.debug('New info on %s %s', desc, i)

                if horizontal:
                    self.cells[i] = updated
                    self.row_updated(i)
                else:
                    self.cells[:, i] = updated
                    self.column_updated(i)

        LOG.info('%ss solution: %ss', desc.title(), time.time() - start)

    def solve_round(self, rows_first=True, parallel=False):
        """Solve every column and every row using FSM exactly one time"""
        if rows_first:
            order = [True, False]
        else:
            order = [False, True]

        for horizontal in order:
            self.solve_rows(horizontal=horizontal, parallel=parallel)

    @property
    def solved(self):
        """Return whether the nonogram is completely solved"""
        return self._solved

    def solve(self, rows_first=True, parallel=False):
        """Solve the nonogram to the most with FSM using multiple rounds"""
        solved = self.solution_rate
        counter = 0

        if parallel:
            LOG.info("Using several processes to solve")

        start = time.time()
        while True:
            counter += 1
            LOG.info('Round %s', counter)

            self.solve_round(rows_first=rows_first, parallel=parallel)

            if self.solution_rate > solved:
                self.solution_round_completed()

            if self.solution_rate == 1 or solved == self.solution_rate:
                self._solved = True
                break

            solved = self.solution_rate

        if self.solution_rate != 1:
            LOG.warning('The nonogram is not solved full. The rate is %s', self.solution_rate)
        LOG.info('Full solution: %ss', time.time() - start)

    def try_contradiction(self, row_index, column_index,
                          assumption=BOX, propagate=True):
        """
        Try to find if the given cell can be in an assumed state.
        If the contradiction is found, set the cell
        in an inverted state and propagate the changes if needed.
        """
        # already solved
        if self.cells[row_index][column_index] != UNSURE:
            return

        save = self.cells.copy()
        contradiction = False

        try:
            try:
                self.cells[row_index][column_index] = assumption
                self.solve()
            except NonogramError:
                contradiction = True
            else:
                if self.solution_rate == 1:
                    LOG.warning("Found one of the solutions!")
        finally:
            # rollback solved cells
            self.cells = save
            if contradiction:
                LOG.info("Found contradiction at (%s, %s)",
                         row_index, column_index)
                self.cells[row_index][column_index] = invert(assumption)

                # try to solve with additional info
                if propagate:
                    self.solve()

    def _solve_with_contradictions_round(self, row_index, column_index,
                                         assumption=BOX, propagate=True):
        if assumption in (BOX, SPACE):
            self.try_contradiction(row_index, column_index,
                                   assumption=assumption, propagate=propagate)
        else:
            self.try_contradiction(row_index, column_index,
                                   assumption=BOX, propagate=propagate)
            self.try_contradiction(row_index, column_index,
                                   assumption=SPACE, propagate=propagate)

    def solve_with_contradictions(self, propagate_on_row=False,
                                  assumption=BOX, by_rows=True):
        """
        Solve the nonogram to the most with contradictions
        and the basic `solve` method.

        :param propagate_on_row: how to propagate changes:
        in the end of the row or after each solved cell
        :param assumption: which states to try: BOX, SPACE, or both (None)
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

        if by_rows:
            for solved_row in range(self.height):
                LOG.info('Trying row %s', solved_row)
                for solved_column in range(self.width):
                    self._solve_with_contradictions_round(
                        solved_row, solved_column, assumption, propagate_on_cell)

                if propagate_on_row:
                    self.solve()
        else:
            for solved_column in range(self.width):
                LOG.info('Trying column %s', solved_column)
                for solved_row in range(self.height):
                    self._solve_with_contradictions_round(
                        solved_row, solved_column, assumption, propagate_on_cell)

                if propagate_on_row:
                    self.solve()

        self._solved = True
        if self.solution_rate != 1:
            LOG.warning('The nonogram is not solved full. The rate is %s', self.solution_rate)
        LOG.info('Full solution: %ss', time.time() - start)


class ConsoleBoard(BaseBoard):
    """A board that renders on stdout"""

    def __init__(self, columns, rows, **renderer_params):
        super(ConsoleBoard, self).__init__(
            columns, rows, renderer=StreamRenderer(**renderer_params))


class AsciiBoard(BaseBoard):
    """A board that renders on stdout with ASCII graphic"""

    def __init__(self, columns, rows, **renderer_params):
        super(AsciiBoard, self).__init__(
            columns, rows, renderer=AsciiRenderer(**renderer_params))
