# -*- coding: utf-8 -*
"""
Defines a board of nonogram game
"""

from __future__ import unicode_literals, print_function

import logging
import os

import numpy as np

from pyngrm.base import UNSURE, normalize_clues
from pyngrm.renderer import (
    Renderer,
    StreamRenderer,
    AsciiRenderer,
)

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


class BaseBoard(object):
    """
    Basic nonogram board with columns and rows defined
    """

    def __init__(self, columns, rows, renderer=Renderer):
        """
        :type renderer: Renderer | type[Renderer]
        """
        self.columns = self.normalize(columns)
        self.rows = self.normalize(rows)

        self.renderer = renderer
        if isinstance(self.renderer, type):
            self.renderer = self.renderer(self)
        elif isinstance(self.renderer, Renderer):
            self.renderer.board_init(self)
        else:
            raise TypeError('Bad renderer: %s' % renderer)

        self.cells = np.array([[UNSURE] * self.width for _ in range(self.height)])
        self.validate()

    @classmethod
    def normalize(cls, rows):
        """
        Presents given rows in standard format
        """
        return tuple(map(normalize_clues, rows))

    @property
    def height(self):
        """The height of the playing area"""
        return len(self.rows)

    @property
    def width(self):
        """The width of the playing area"""
        return len(self.columns)

    def validate(self):
        """
        Validate that the board is valid:
        - all the clues in a row (a column) can fit into width (height) of the board
        - the vertical and horizontal clues defines the same number of boxes
        """
        self.validate_headers(self.columns, self.height)
        self.validate_headers(self.rows, self.width)

        boxes_in_rows = sum(sum(block) for block in self.rows)
        boxes_in_columns = sum(sum(block) for block in self.columns)
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
