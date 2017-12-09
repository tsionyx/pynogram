# -*- coding: utf-8 -*
"""
Defines various renderers for the game of nonogram
"""

from __future__ import unicode_literals, print_function

import logging
import os
import sys

from six import integer_types, text_type

from pyngrm.base import BOX, SPACE, UNSURE
from pyngrm.utils import pad, merge_dicts, max_safe, split_seq

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)

# cell states that matters for renderer
_NOT_SET = 'E'  # empty cell, e.g. in the headers
_THUMBNAIL = 'T'


class _DummyBoard(object):  # pylint: disable=too-few-public-methods
    horizontal_clues = vertical_clues = ()
    width = height = 0


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
        """The size of the header block with vertical clues"""
        return self.header_height + self.board.height

    @property
    def full_width(self):
        """The full size of """
        return self.side_width + self.board.width

    @property
    def header_height(self):
        """The size of the header block with vertical clues"""
        return max_safe(map(len, self.board.vertical_clues), default=0)

    @property
    def side_width(self):
        """The width of the side block with horizontal clues"""
        return max_safe(map(len, self.board.horizontal_clues), default=0)

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
        Changes the internal state to be able to draw vertical clues
        """
        raise NotImplementedError()

    def draw_side(self):
        """
        Changes the internal state to be able to draw horizontal clues
        """
        raise NotImplementedError()

    def draw_grid(self):
        """
        Changes the internal state to be able to draw a main grid
        """
        raise NotImplementedError()


class StreamRenderer(Renderer):
    """
    Renders a board as a simple text table to a stream (stdout by default)
    """

    def __init__(self, board=None, stream=sys.stdout):
        super(StreamRenderer, self).__init__(board)
        self.stream = stream

    def board_init(self, board=None):
        super(StreamRenderer, self).board_init(board)
        LOG.info('init cells: %sx%s', self.full_width, self.full_width)
        self.cells = [[self.cell_icon(_NOT_SET)] * self.full_width
                      for _ in range(self.full_height)]

    def _print(self, *args):
        return print(*args, file=self.stream)

    def render(self):
        for row in self.cells:
            self._print(' '.join(self.cell_icon(cell) for cell in row))

    def draw_header(self):
        for i in range(self.header_height):
            for j in range(self.side_width):
                self.cells[i][j] = _THUMBNAIL

        for j, col in enumerate(self.board.vertical_clues):
            rend_j = j + self.side_width
            if not col:
                col = [0]
            rend_row = pad(col, self.header_height, _NOT_SET)
            # self.cells[:self.side_width][rend_j] = map(text_type, rend_row)
            for rend_i, cell in enumerate(rend_row):
                self.cells[rend_i][rend_j] = cell

    def draw_side(self):
        for i, row in enumerate(self.board.horizontal_clues):
            rend_i = i + self.header_height
            # row = list(row)
            if not row:
                row = [0]
            rend_row = pad(row, self.side_width, _NOT_SET)
            self.cells[rend_i][:self.side_width] = rend_row

    def draw_grid(self):
        for i, row in enumerate(self.board.cells):
            rend_i = i + self.header_height
            for j, cell in enumerate(row):
                rend_j = j + self.side_width
                self.cells[rend_i][rend_j] = cell

    ICONS = {
        _NOT_SET: ' ',
        _THUMBNAIL: 't',
        UNSURE: '_',
        BOX: 'X',
        SPACE: '.',
    }

    def cell_icon(self, state):
        """
        Gets a symbolic representation of a cell given its state
        and predefined table `ICONS`
        """
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

    BOLD_LINE_HORIZONTAL = HORIZONTAL_LINE_PAD
    BOLD_LINE_VERTICAL_SIZE = 1
    BOLD_LINE_EVERY = 5

    def _cell_horizontal_border(self, header=False, bold=False):
        if header:
            padding = self.HEADER_DELIMITER
        elif bold:
            padding = self.BOLD_LINE_HORIZONTAL
        else:
            padding = self.HORIZONTAL_LINE_PAD

        return padding * self.CELL_WIDTH

    def _side_delimiter(self, grid=False):
        """
        Separates side clues list from the main grid.
        Default values are '||' for the data rows or
        '++' for the 'grid' rows.
        """
        size = self.SIDE_DELIMITER_SIZE

        if grid:
            delimiter = self.GRID_CROSS_SYMBOL
        else:
            delimiter = self.VERTICAL_GRID_SYMBOL
        return delimiter * size

    def _horizontal_grid(self, size, header=False, bold=False):
        bold_cross_symbol = self.BOLD_LINE_VERTICAL_SIZE * self.GRID_CROSS_SYMBOL

        return bold_cross_symbol.join(
            self.GRID_CROSS_SYMBOL.join(block)
            for block in
            split_seq(
                [self._cell_horizontal_border(header=header, bold=bold)] * size,
                self.BOLD_LINE_EVERY))

    def _grid_row(self, border=False, header=False, data_row_index=None):
        """
        The whole string representing a grid row.
        When `border` is True it's the most upper or lower row.
        When `data_row_index` provided, draw a bold line if it's divisible by 5
        """
        if border:
            if header:
                raise ValueError(
                    'Cannot print a row that separates headers as a border row')
            end = self.CORNER_SYMBOL
        else:
            end = self.VERTICAL_GRID_SYMBOL

        bold = False
        if data_row_index:
            if data_row_index > 0 and (data_row_index % self.BOLD_LINE_EVERY == 0):
                bold = True

        return ''.join([
            end,
            self._horizontal_grid(self.side_width, header=header, bold=bold),
            self._side_delimiter(grid=True),
            self._horizontal_grid(self.board.width, header=header, bold=bold),
            end,
        ])

    def cell_icon(self, state):
        ico = super(AsciiRenderer, self).cell_icon(state)
        max_width = self.CELL_WIDTH
        padded = max_width - len(ico)
        if padded < 0:
            raise ValueError('Cannot fit the value {} into cell width {}'.format(
                ico, max_width))

        # pre-formatted to pad later
        res = '{}%s{}' % ico

        space_padding = ' ' * int(padded / 2)

        # e.g. 3 --> ' 3 '
        # but 13 --> ' 13'
        if padded % 2 == 0:
            return res.format(space_padding, space_padding)

        return res.format(space_padding + ' ', space_padding)

    def _value_row(self, values):
        sep = self.VERTICAL_GRID_SYMBOL
        bold_sep = self.BOLD_LINE_VERTICAL_SIZE * sep

        for i, cell in enumerate(values):
            if i == self.side_width:
                yield self._side_delimiter()
            else:
                # only on a data area, every 5 column
                if i > self.side_width and \
                        (i - self.side_width) % self.BOLD_LINE_EVERY == 0:
                    yield bold_sep
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
                grid_row = self._grid_row(data_row_index=i - self.header_height)
            self._print(grid_row)
            self._print(''.join(self._value_row(row)))

        self._print(self._grid_row(border=True))

    ICONS = merge_dicts(StreamRenderer.ICONS, {
        _THUMBNAIL: '#',
        UNSURE: ' ',
    })


class AsciiRendererWithBold(AsciiRenderer):
    """
    AsciiRenderer that also splits the whole board into
    5x5 squares using 'bold' grid lines
    """
    SIDE_DELIMITER_SIZE = 3
    BOLD_LINE_HORIZONTAL = AsciiRenderer.HEADER_DELIMITER
    BOLD_LINE_VERTICAL_SIZE = 2
