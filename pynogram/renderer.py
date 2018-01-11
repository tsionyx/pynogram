# -*- coding: utf-8 -*
"""
Defines various renderers for the game of nonogram
"""

from __future__ import unicode_literals, print_function, division

import logging
import os
import re
import sys

import svgwrite as svg
from six import integer_types, text_type, string_types

from pynogram.core.board import Renderer, Board, ColoredBoard
from pynogram.core.common import UNKNOWN, BOX, SPACE
from pynogram.utils.collections import pad, split_seq

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)

# cell states that matters for renderer
_NOT_SET = 'E'  # empty cell, e.g. in the headers
_THUMBNAIL = 'T'


# noinspection PyAbstractClass
# pylint: disable=abstract-method
class StreamRenderer(Renderer):
    """
    Simplify textual rendering of a board to a stream (stdout by default)
    """

    def __init__(self, board=None, stream=sys.stdout):
        self.stream = stream
        self.icons = {
            _NOT_SET: ' ',
            _THUMBNAIL: '-',
            UNKNOWN: '_',
            BOX: 'X',
            SPACE: '.',
        }
        super(StreamRenderer, self).__init__(board)

    def _print(self, *args):
        return print(*args, file=self.stream)

    def cell_icon(self, state):
        """
        Gets a symbolic representation of a cell given its state
        and predefined table `icons`
        """
        if isinstance(state, (list, tuple)):
            # colored clue cell
            state = state[0]

        types = tuple(map(type, self.icons))
        # why not just `isinstance(state, int)`?
        # because `isinstance(True, int) == True`
        if isinstance(state, integer_types) and not isinstance(state, types):
            return text_type(state)

        if isinstance(self.board, ColoredBoard):
            if state in self.board.color_map:
                return self.board.char_for_color(state)

        return self.icons[state]


class BaseAsciiRenderer(StreamRenderer):
    """
    Renders a board as a simple text table (without grid)
    """

    def board_init(self, board=None):
        super(BaseAsciiRenderer, self).board_init(board)
        LOG.info('init cells: %sx%s', self.full_width, self.full_width)
        self.cells = [[self.cell_icon(_NOT_SET)] * self.full_width
                      for _ in range(self.full_height)]

    def render(self):
        for row in self.cells:
            res = []
            for index, cell in enumerate(row):
                ico = self.cell_icon(cell)

                # do not pad the last symbol in a line
                if len(ico) == 1:
                    if index < len(row) - 1:
                        ico += ' '

                res.append(ico)

            self._print(''.join(res))

    def draw_header(self):
        for i in range(self.header_height):
            for j in range(self.side_width):
                self.cells[i][j] = _THUMBNAIL

        for j, col in enumerate(self.board.columns_descriptions):
            rend_j = j + self.side_width
            if not col:
                col = [0]
            rend_row = pad(col, self.header_height, _NOT_SET)
            # self.cells[:self.side_width][rend_j] = map(text_type, rend_row)
            for rend_i, cell in enumerate(rend_row):
                self.cells[rend_i][rend_j] = cell

    def draw_side(self):
        for i, row in enumerate(self.board.rows_descriptions):
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


class AsciiRenderer(BaseAsciiRenderer):
    """
    Renders the board as a full-blown ASCII table
    with headers, grid and borders
    """

    def __init__(self, board=None, stream=sys.stdout):
        super(AsciiRenderer, self).__init__(board, stream=stream)
        self.icons.update({
            _THUMBNAIL: '#',
            UNKNOWN: ' ',
        })

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
        Separates side descriptions from the main grid.
        Default values are '||' for the data rows or
        '++' for the 'grid' rows.
        """
        size = self.SIDE_DELIMITER_SIZE

        if grid:
            delimiter = self.GRID_CROSS_SYMBOL
        else:
            delimiter = self.VERTICAL_GRID_SYMBOL
        return delimiter * size

    def _horizontal_grid(self, size, header=False, bold=False, side=False):
        if side:
            # there should be no bold lines on a side
            # so it's a standard grid cross symbol
            bold_cross_symbol = self.GRID_CROSS_SYMBOL
        else:
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
            self._horizontal_grid(self.side_width, header=header, bold=bold, side=True),
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


class AsciiRendererWithBold(AsciiRenderer):
    """
    AsciiRenderer that also splits the whole board into
    5x5 squares using 'bold' grid lines
    """
    SIDE_DELIMITER_SIZE = 3
    BOLD_LINE_HORIZONTAL = AsciiRenderer.HEADER_DELIMITER
    BOLD_LINE_VERTICAL_SIZE = 2


class SvgRenderer(StreamRenderer):
    """
    Draws the board like an SVG image (best representation for web)
    """

    DEFAULT_CELL_SIZE_IN_PIXELS = 15
    BOLD_EVERY = 5

    GRID_STROKE_WIDTH = 1
    GRID_BOLD_STROKE_WIDTH = 2

    @property
    def clues_font_size(self):
        """The size of the descriptions text"""
        return self.cell_size * 0.6

    def __init__(self, board=None, stream=sys.stdout, size=DEFAULT_CELL_SIZE_IN_PIXELS):
        super(SvgRenderer, self).__init__(board, stream)

        self.cell_size = size
        self.drawing = svg.Drawing(size=(
            self.full_width + self.cell_size,
            self.full_height + self.cell_size))
        self._add_definitions()

    def _add_definitions(self):
        drawing = self.drawing

        # dynamic style rules
        drawing.defs.add(drawing.style(
            'g.grid-lines line {stroke-width: %i} '
            'g.grid-lines line.bold {stroke-width: %i} '
            'g.header-clues text, g.side-clues text {font-size: %f} ' % (
                self.GRID_STROKE_WIDTH,
                self.GRID_BOLD_STROKE_WIDTH,
                self.clues_font_size,
            )
        ))

        box_symbol = drawing.symbol(id_='box')
        box_symbol.add(drawing.rect(
            size=(self.cell_size, self.cell_size),
        ))

        space_symbol = drawing.symbol(id_='space')
        space_symbol.add(drawing.circle(
            r=self.cell_size / 20
        ))

        solved_symbol = drawing.symbol(id_='check', stroke='green', fill='none')
        solved_symbol.add(drawing.circle(
            r=40, stroke_width=10, center=(50, 50)
        ))
        solved_symbol.add(drawing.polyline(
            stroke_width=12,
            points=[(35, 35), (35, 55), (75, 55)],
            transform='rotate(-45 50 50)'
        ))

        self.check_icon_size = 100

        drawing.defs.add(box_symbol)
        drawing.defs.add(space_symbol)
        drawing.defs.add(solved_symbol)

    @property
    def pixel_side_width(self):
        """Horizontal clues side width in pixels"""
        return self.side_width * self.cell_size

    @property
    def pixel_header_height(self):
        """Vertical clues header height in pixels"""
        return self.header_height * self.cell_size

    @property
    def pixel_board_width(self):
        """The width of the main area in pixels"""
        return self.board.width * self.cell_size

    @property
    def pixel_board_height(self):
        """The height of the main area in pixels"""
        return self.board.height * self.cell_size

    @property
    def full_width(self):
        """Full width of the SVG board representation"""
        return self.pixel_side_width + self.pixel_board_width

    @property
    def full_height(self):
        """Full height of the SVG board representation"""
        return self.pixel_header_height + self.pixel_board_height

    RGB_TRIPLET_RE = re.compile(r'([0-9]+),[ \t]*([0-9]+),[ \t]*([0-9]+)')

    def _color_from_name(self, color_name):
        color = self.board.rgb_for_color(color_name)

        if len(color) == 6:
            return '#' + color

        elif isinstance(color, string_types) and self.RGB_TRIPLET_RE.match(color):
            return 'rgb({})'.format(color)

        elif isinstance(color, (list, tuple)) and len(color) == 3:
            return 'rgb({})'.format(','.join(map(str, color)))

        return color

    def block_svg(self, value, is_column, clue_number, block_number):
        """
        Return the SVG element for the clue number (colored case included)
        """
        # left to right, bottom to top
        block_number = -block_number

        shift = (0.85, -0.3) if is_column else (-0.3, 0.75)
        i, j = (clue_number, block_number) if is_column else (block_number, clue_number)

        if isinstance(value, (list, tuple)):
            # colored board
            value, color_name = value[:2]
            color = self._color_from_name(color_name)
        else:
            color = 'currentColor'

        return self.drawing.text(
            str(value),
            fill=color,
            insert=(
                self.pixel_side_width + (i + shift[0]) * self.cell_size,
                self.pixel_header_height + (j + shift[1]) * self.cell_size,
            )
        )

    def draw_header(self):
        drawing = self.drawing

        thumbnail_rect = drawing.rect(
            size=(self.pixel_side_width, self.pixel_header_height),
            class_='nonogram-thumbnail')

        header_rect = drawing.rect(
            insert=(self.pixel_side_width, 0),
            size=(self.pixel_board_width, self.pixel_header_height),
            class_='nonogram-header')

        drawing.add(thumbnail_rect)
        drawing.add(header_rect)

        header_group = drawing.g(class_='header-clues')
        for i, col_desc in enumerate(self.board.columns_descriptions):
            if Board.row_solution_rate(self.board.cells.T[i]) == 1:
                x_pos = self.pixel_side_width + (i * self.cell_size)
                header_group.add(drawing.rect(
                    insert=(x_pos, 0),
                    size=(self.cell_size, self.pixel_header_height),
                    class_='solved'
                ))

            for j, desc_item in enumerate(reversed(col_desc)):
                header_group.add(self.block_svg(desc_item, True, i, j))

        drawing.add(header_group)

    def draw_side(self):
        drawing = self.drawing

        side_rect = drawing.rect(
            insert=(0, self.pixel_header_height),
            size=(self.pixel_side_width, self.pixel_board_height),
            class_='nonogram-side')

        drawing.add(side_rect)

        side_group = drawing.g(class_='side-clues')
        for j, row_desc in enumerate(self.board.rows_descriptions):
            if Board.row_solution_rate(self.board.cells[j]) == 1:
                y_pos = self.pixel_header_height + (j * self.cell_size)
                side_group.add(drawing.rect(
                    insert=(0, y_pos),
                    size=(self.pixel_side_width, self.cell_size),
                    class_='solved'
                ))

            for i, desc_item in enumerate(reversed(row_desc)):
                side_group.add(self.block_svg(desc_item, False, j, i))

        drawing.add(side_group)

    def draw_grid(self):  # pylint: disable=too-many-locals
        drawing = self.drawing

        grid_rect = drawing.rect(
            insert=(self.pixel_side_width, self.pixel_header_height),
            size=(self.pixel_board_width, self.pixel_board_height),
            class_='nonogram-grid')

        drawing.add(grid_rect)

        grid_lines = drawing.g(class_='grid-lines')

        # draw horizontal lines
        for i in range(self.board.height + 1):
            extra = dict()

            if i % self.BOLD_EVERY == 0 or i == self.board.height:
                extra['class'] = 'bold'

            y_pos = self.pixel_header_height + (i * self.cell_size)
            grid_lines.add(drawing.line(
                start=(0, y_pos),
                end=(self.full_width, y_pos),
                **extra
            ))

        # draw vertical lines
        for i in range(self.board.width + 1):
            extra = dict()

            if i % self.BOLD_EVERY == 0 or i == self.board.width:
                extra['class'] = 'bold'

            x_pos = self.pixel_side_width + (i * self.cell_size)
            grid_lines.add(drawing.line(
                start=(x_pos, 0),
                end=(x_pos, self.full_height),
                **extra
            ))

        drawing.add(grid_lines)

        boxes = drawing.g(class_='box')
        spaces = drawing.g(class_='space')

        for i, column in enumerate(self.board.cells.T):
            for j, cell in enumerate(column):
                if cell == BOX:
                    icon = drawing.use(
                        href='#box',
                        insert=(
                            self.pixel_side_width + (i * self.cell_size),
                            self.pixel_header_height + (j * self.cell_size))
                    )
                    boxes.add(icon)
                elif cell == SPACE:
                    icon = drawing.use(
                        href='#space',
                        insert=(
                            self.pixel_side_width + (i + 0.5) * self.cell_size,
                            self.pixel_header_height + (j + 0.5) * self.cell_size)
                    )
                    spaces.add(icon)

        drawing.add(boxes)
        drawing.add(spaces)

        if self.board.solution_rate == 1:
            check_icon_size = self.check_icon_size
            left_padding = (self.pixel_side_width - check_icon_size) / 2
            top_padding = (self.pixel_header_height - check_icon_size) / 2
            left_padding = max(left_padding, 0)
            top_padding = max(top_padding, 0)

            drawing.add(drawing.use('#check', insert=(
                left_padding, top_padding
            )))

    def render(self):
        self.drawing.write(self.stream)
        # self._print(self.drawing.tostring())

    def draw(self):
        self.drawing.elements = []
        self.drawing.add(self.drawing.defs)

        super(SvgRenderer, self).draw()
