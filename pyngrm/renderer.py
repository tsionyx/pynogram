# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import logging
import os
import sys

from six import integer_types, text_type

from pyngrm.utils import pad_list

_log_name = __name__
if _log_name == '__main__':  # pragma: no cover
    _log_name = os.path.basename(__file__)

log = logging.getLogger(_log_name)


class CellState(object):
    NOT_SET = None
    THUMBNAIL = 'T'
    UNSURE = 'U'
    BOX = 'B'
    SPACE = 'S'


class Renderer(object):
    def __init__(self, board=None):
        self.board = board

        self.cells = None
        self.board_width, self.board_height = None, None

        self.init()

    def init(self, board=None):
        board = board or self.board
        if board:
            log.info("Init '%s' renderer with board '%s'",
                     self.__class__.__name__, board)
            self.board = board
            self.board_width, self.board_height = board.full_size
            return True

    @property
    def side_width(self):
        return self.board.headers_width

    @property
    def header_height(self):
        return self.board.headers_height

    def render(self):
        raise NotImplementedError()

    def draw_header(self):
        return self

    def draw_side(self):
        return self

    def draw_grid(self):
        return self


class StreamRenderer(Renderer):
    def __init__(self, board=None, stream=sys.stdout):
        super(StreamRenderer, self).__init__(board)
        self.stream = stream

    def init(self, board=None):
        if super(StreamRenderer, self).init(board):
            log.info('init cells: %sx%s', self.board_width, self.board_height)
            self.cells = [[self.cell_icon(CellState.NOT_SET)] * self.board_width
                          for _ in range(self.board_height)]
            return True

    def _print(self, *args):
        return print(*args, file=self.stream)

    def render(self):
        for row in self.cells:
            self._print(' '.join(self.cell_icon(cell) for cell in row))

    def draw_header(self):
        for i in range(self.header_height):
            for j in range(self.side_width):
                self.cells[i][j] = CellState.THUMBNAIL

        for j, col in enumerate(self.board.columns):
            rend_j = j + self.side_width
            if not col:
                col = [0]
            rend_row = pad_list(col, self.header_height, CellState.NOT_SET)
            # self.cells[:self.side_width][rend_j] = map(text_type, rend_row)
            for rend_i, cell in enumerate(rend_row):
                self.cells[rend_i][rend_j] = cell

        return super(StreamRenderer, self).draw_header()

    def draw_side(self):
        for i, row in enumerate(self.board.rows):
            rend_i = i + self.header_height
            # row = list(row)
            if not row:
                row = [0]
            rend_row = pad_list(row, self.side_width, CellState.NOT_SET)
            self.cells[rend_i][:self.side_width] = rend_row

        return super(StreamRenderer, self).draw_side()

    def draw_grid(self):
        for i, row in enumerate(self.board.cells):
            rend_i = i + self.header_height
            for j, cell in enumerate(row):
                rend_j = j + self.side_width
                self.cells[rend_i][rend_j] = cell

        return super(StreamRenderer, self).draw_grid()

    ICONS = {
        CellState.NOT_SET: ' ',
        CellState.THUMBNAIL: 't',
        CellState.UNSURE: '_',
        CellState.BOX: 'X',
        CellState.SPACE: '.',
    }

    @classmethod
    def cell_icon(cls, state):
        try:
            return cls.ICONS[state]
        except KeyError:
            if isinstance(state, integer_types):
                return text_type(state)
            raise
