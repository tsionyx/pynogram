# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import logging
import os
import sys

from six import integer_types, text_type

from pyngrm.utils import pad_list, merge_dicts

_log_name = __name__
if _log_name == '__main__':  # pragma: no cover
    _log_name = os.path.basename(__file__)

log = logging.getLogger(_log_name)


class CellState(object):
    UNSURE = None
    BOX = True
    SPACE = False

    # only matters for renderer
    NOT_SET = 'E'
    THUMBNAIL = 'T'


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
    def header_height(self):
        return self.board.headers_height

    @property
    def side_width(self):
        return self.board.headers_width

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

    def cell_icon(self, state):
        types = tuple(map(type, self.ICONS))
        # why not just `isinstance(state, int)`?
        # because `isinstance(True, int) == True`
        if isinstance(state, integer_types) and not isinstance(state, types):
            return text_type(state)
        return self.ICONS[state]


class AsciiRenderer(StreamRenderer):
    """
    Renders the board as a full-blown ASCII table
    with headers, grid and borders
    """

    # cannot fit the value more than '999'
    CELL_WIDTH = 3
    HORIZONTAL_LINE_PAD = '-'
    VERTICAL_GRID_SYMBOL = '|'
    HEADER_DELIMITER = '='
    SIDE_DELIMITER_SIZE = 2
    GRID_CROSS_SYMBOL = '+'
    CORNER_SYMBOL = GRID_CROSS_SYMBOL

    def _cell_horizontal_border(self, header=False):
        if header:
            pad = self.HEADER_DELIMITER
        else:
            pad = self.HORIZONTAL_LINE_PAD
        return pad * self.CELL_WIDTH

    def _side_delimiter(self, grid=False):
        """
        Separates side clues list from the main grid.
        Default values are '||' for the data rows or
        '++' for the 'grid' rows.
        """
        if grid:
            ch = self.GRID_CROSS_SYMBOL
        else:
            ch = self.VERTICAL_GRID_SYMBOL
        return ch * self.SIDE_DELIMITER_SIZE

    def _horizontal_grid(self, size, header=False):
        return self.GRID_CROSS_SYMBOL.join(
            [self._cell_horizontal_border(header=header)] * size)

    def _grid_row(self, border=False, header=False):
        """
        The whole string representing a grid row.
        When `border` is True it's the most upper or lower row.
        """
        if border:
            if header:
                raise ValueError(
                    'Cannot print a row that separates headers as a border row')
            end = self.CORNER_SYMBOL
        else:
            end = self.VERTICAL_GRID_SYMBOL

        return ''.join([
            end,
            self._horizontal_grid(self.side_width, header=header),
            self._side_delimiter(grid=True),
            self._horizontal_grid(self.board.width, header=header),
            end,
        ])

    def cell_icon(self, state):
        ico = super(AsciiRenderer, self).cell_icon(state)
        max_width = self.CELL_WIDTH
        padded = max_width - len(ico)
        if padded < 0:
            raise ValueError('Cannot fit the value {} into cell width {}'.format(
                ico, max_width))

        # pre-formatted to insert paddings later
        res = '{}%s{}' % ico

        pad = ' ' * int(padded / 2)
        # e.g. 3 --> ' 3 '
        # but 13 --> ' 13'
        if padded % 2 == 0:
            return res.format(pad, pad)
        else:
            return res.format(pad + ' ', pad)

    def _value_row(self, values):
        sep = self.VERTICAL_GRID_SYMBOL

        for i, cell in enumerate(values):
            if i == self.side_width:
                yield self._side_delimiter()
            else:
                yield sep

            yield self.cell_icon(cell)

        yield sep

    def render(self):
        for i, row in enumerate(self.cells):
            if i == 0:
                grid_row = self._grid_row(border=True)
            elif i == self.header_height:
                grid_row = self._grid_row(header=True)
            else:
                grid_row = self._grid_row()
            self._print(grid_row)
            self._print(''.join(self._value_row(row)))

        self._print(self._grid_row(border=True))

    ICONS = merge_dicts(StreamRenderer.ICONS, {
        CellState.THUMBNAIL: '#',
        CellState.UNSURE: ' ',
    })
