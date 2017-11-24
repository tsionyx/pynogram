# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import logging
import os
import sys

from six import string_types, integer_types, text_type

if __name__ == '__main__':
    log = logging.getLogger(os.path.basename(__file__))
else:
    log = logging.getLogger(__name__)


class CellState(object):
    NOT_SET = None
    BOX = True
    SPACE = False


class Renderer(object):
    def __init__(self, board_width=None, board_height=None):
        self.cells = None
        self.board_width = None
        self.board_height = None
        if board_width and board_height:
            self.init_cells(board_width, board_height)

    def render(self):
        return NotImplemented

    def init_cells(self, board_width, board_height):
        self.board_width = board_width
        self.board_height = board_height


class BaseBoard(object):
    def __init__(self, rows, columns, renderer=Renderer):
        self.rows = self._normalize(rows)
        self.columns = self._normalize(columns)

        self.renderer = renderer
        if isinstance(renderer, type):
            self.renderer = renderer(*self.full_size)
        else:
            self.renderer.init_cells(*self.full_size)

        self.cells = [[CellState.NOT_SET] * self.width for _ in range(self.height)]
        self.validate_headers(self.rows, self.width)
        self.validate_headers(self.columns, self.height)

    @classmethod
    def _normalize(cls, rows):
        res = []
        for r in rows:
            if not r:  # None, 0, '', [], ()
                r = ()
            elif isinstance(r, (tuple, list)):
                r = tuple(r)
            elif isinstance(r, integer_types):
                r = (r,)
            elif isinstance(r, string_types):
                r = tuple(map(int, r.split(' ')))
            res.append(r)
        return tuple(res)

    @property
    def width(self):
        return len(self.columns)

    @property
    def height(self):
        return len(self.rows)

    @classmethod
    def validate_headers(cls, rows, max_size):
        for row in rows:
            need_cells = sum(row)
            if row:
                # also need at least one space between every two blocks
                need_cells += len(row) - 1

            log.debug("Row: %s; Need: %s; Available: %s.",
                      row, need_cells, max_size)
            if need_cells > max_size:
                raise ValueError("Cannot allocate row {} in {} cells".format(
                    list(row), max_size))

    @property
    def full_size(self):
        return (
            self._headers_width + self.width,
            self._headers_height + self.height)

    def render(self):
        return self.renderer.render()

    def draw(self):
        self.draw_thumbnail_area() \
            .draw_clues() \
            .draw_grid() \
            .render()

    def draw_thumbnail_area(self):
        return self

    def draw_clues(self, horizontal=None):
        if horizontal is None:
            self.draw_clues(True)
            self.draw_clues(False)
        elif horizontal is True:
            self.draw_horizontal_clues()
        else:
            self.draw_vertical_clues()
        return self

    def draw_grid(self):
        return self

    def draw_horizontal_clues(self):
        return NotImplemented

    def draw_vertical_clues(self):
        return NotImplemented

    @property
    def _headers_height(self):
        return max(map(len, self.columns))

    @property
    def _headers_width(self):
        return max(map(len, self.rows))


class StreamRenderer(Renderer):
    def __init__(self, board_width=None, board_height=None, stream=sys.stdout):
        super(StreamRenderer, self).__init__(board_width, board_height)
        self.stream = stream

    def init_cells(self, board_width, board_height):
        super(StreamRenderer, self).init_cells(board_width, board_height)
        self.cells = [[' '] * self.board_width for _ in range(self.board_height)]

    def render(self):
        for row in self.cells:
            print(' '.join(row), file=self.stream)


def pad_list(l, n, x, left=True):
    """
    >>> pad_list([1, 2, 3], 2, 5)
    [1, 2, 3]
    >>> pad_list([1, 2, 3], 5, 5)
    [5, 5, 1, 2, 3]
    >>> pad_list([1, 2, 3], 5, 5, left=False)
    [1, 2, 3, 5, 5]
    """
    if len(l) >= n:
        return l

    padding = [x] * (n - len(l))
    return padding + list(l) if left else list(l) + padding


class ConsoleBoard(BaseBoard):
    def __init__(self, rows, columns, renderer=StreamRenderer):
        super(ConsoleBoard, self).__init__(
            rows, columns, renderer=renderer)

    def draw_thumbnail_area(self):
        for i in range(self._headers_height):
            for j in range(self._headers_width):
                self.renderer.cells[i][j] = 't'
        return super(ConsoleBoard, self).draw_thumbnail_area()

    def draw_horizontal_clues(self):
        for i, row in enumerate(self.rows):
            rend_i = i + self._headers_height
            # row = list(row)
            if not row:
                row = [0]
            rend_row = pad_list(row, self._headers_width, ' ')
            self.renderer.cells[rend_i][:self._headers_width] = map(text_type, rend_row)

        return super(ConsoleBoard, self).draw_horizontal_clues()

    def draw_vertical_clues(self):
        for j, col in enumerate(self.columns):
            rend_j = j + self._headers_width
            if not col:
                col = [0]
            rend_row = pad_list(col, self._headers_height, ' ')
            # self.renderer.cells[:self._headers_width][rend_j] = map(text_type, rend_row)
            for rend_i, cell in enumerate(map(text_type, rend_row)):
                self.renderer.cells[rend_i][rend_j] = cell

        return super(ConsoleBoard, self).draw_vertical_clues()

    CELL_ICON = {
        CellState.NOT_SET: '_',
        CellState.BOX: 'X',
        CellState.SPACE: '.',
    }

    def draw_grid(self):
        for i, row in enumerate(self.cells):
            rend_i = i + self._headers_height
            for j, cell in enumerate(row):
                rend_j = j + self._headers_width
                self.renderer.cells[rend_i][rend_j] = self.CELL_ICON[cell]

        return super(ConsoleBoard, self).draw_grid()


class TkBoard(BaseBoard):
    pass
