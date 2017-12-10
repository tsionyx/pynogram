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

from pyngrm.base import UNSURE, normalize_clues
from pyngrm.fsm import NonogramFSM
from pyngrm.renderer import (
    Renderer,
    StreamRenderer,
    AsciiRenderer,
)
from pyngrm.utils import avg

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

    def solve_rows(self, horizontal=True):
        """Solve every row (or column) with FSM"""
        start = time.time()

        if horizontal:
            clue_cells_mapping = zip(self.horizontal_clues, self.cells)
            desc = 'row'
        else:
            clue_cells_mapping = zip(self.vertical_clues, self.cells.T)
            desc = 'column'

        for i, (clue, row) in enumerate(clue_cells_mapping):
            pre_solution_rate = self.row_solution_rate(row)
            if pre_solution_rate == 1:
                continue  # already solved

            LOG.debug('Solving %s %s: %s. Partial: %s',
                      i, desc, clue, row)

            nfsm = NonogramFSM.from_clues(clue)
            updated = nfsm.solve(row)
            if self.row_solution_rate(updated) > pre_solution_rate:
                LOG.debug('New info on %s %s', desc, i)

                if horizontal:
                    self.cells[i] = updated
                    self.row_updated(i)
                else:
                    self.cells[:, i] = updated
                    self.column_updated(i)

        LOG.info('%ss solution: %ss', desc.title(), time.time() - start)

    def solve_round(self, rows_first=True):
        """Solve every column and every row using FSM exactly one time"""
        if rows_first:
            order = [True, False]
        else:
            order = [False, True]

        for horizontal in order:
            self.solve_rows(horizontal=horizontal)

        self.solution_round_completed()

    @property
    def solved(self):
        """Return whether the nonogram is completely solved"""
        return self._solved

    def solve(self, rows_first=True):
        """Solve the nonogram to the most with FSM using multiple rounds"""
        solved = self.solution_rate
        counter = 0

        start = time.time()
        while True:
            counter += 1
            LOG.info('Round %s', counter)

            self.solve_round(rows_first=rows_first)

            if self.solution_rate == 1 or solved == self.solution_rate:
                self._solved = True
                break

            solved = self.solution_rate

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


class GameBoard(BaseBoard):
    """
    A board that renders using pygame or similar library with easy 2D drawing.

    Not implemented yet.
    """
    # TODO: http://programarcadegames.com/index.php?chapter=introduction_to_graphics
    pass
