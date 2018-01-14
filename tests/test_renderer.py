# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from io import StringIO

import pytest

from pynogram.core.board import Board
from pynogram.core.common import BOX, SPACE
from pynogram.renderer import (
    Renderer,
    BaseAsciiRenderer,
    AsciiRenderer,
    SvgRenderer,
)
from .test_board import tested_board


@pytest.fixture
def stream():
    # return open(os.devnull, 'w')
    return StringIO()


class TestRenderer(object):
    @pytest.fixture
    def renderer(self):
        return Renderer()

    def test_no_board(self, renderer):
        assert renderer.board is not None

    def test_board_not_changed(self, renderer):
        prev_board = id(renderer.board)
        renderer.board_init()
        assert prev_board == id(renderer.board)

    def test_board_changed(self, renderer):
        prev_board = id(renderer.board)
        renderer.board_init(Board([], []))
        assert prev_board != id(renderer.board)


# noinspection PyShadowingNames
class TestConsoleBoard(object):
    @pytest.fixture
    def board(self, stream):
        return tested_board(stream=stream)

    def test_draw_empty(self, board, stream):
        board.draw()
        assert stream.getvalue().rstrip() == '\n'.join([
            '# #       2 2      ',
            '# # 0 9 9 2 2 4 4 0',
            '  0 _ _ _ _ _ _ _ _',
            '  4 _ _ _ _ _ _ _ _',
            '  6 _ _ _ _ _ _ _ _',
            '2 2 _ _ _ _ _ _ _ _',
            '2 2 _ _ _ _ _ _ _ _',
            '  6 _ _ _ _ _ _ _ _',
            '  4 _ _ _ _ _ _ _ _',
            '  2 _ _ _ _ _ _ _ _',
            '  2 _ _ _ _ _ _ _ _',
            '  2 _ _ _ _ _ _ _ _',
            '  0 _ _ _ _ _ _ _ _',
        ])

    def test_draw_filled_line(self, board, stream):
        board.cells[2][0] = SPACE
        board.cells[2][1:-1] = [BOX] * 6
        board.cells[2][-1] = SPACE
        board.draw()
        assert stream.getvalue().rstrip() == '\n'.join([
            '# #       2 2      ',
            '# # 0 9 9 2 2 4 4 0',
            '  0 _ _ _ _ _ _ _ _',
            '  4 _ _ _ _ _ _ _ _',
            '  6 . X X X X X X .',
            '2 2 _ _ _ _ _ _ _ _',
            '2 2 _ _ _ _ _ _ _ _',
            '  6 _ _ _ _ _ _ _ _',
            '  4 _ _ _ _ _ _ _ _',
            '  2 _ _ _ _ _ _ _ _',
            '  2 _ _ _ _ _ _ _ _',
            '  2 _ _ _ _ _ _ _ _',
            '  0 _ _ _ _ _ _ _ _',
        ])

    def test_bad_cell_value(self, board):
        board.cells[2][0] = str('space')

        with pytest.raises(KeyError) as ei:
            board.draw()

        assert str(ei.value), "'space'"

    def test_two_digits_bad_drawing(self, stream):
        width = 10
        cols = [1] * width + [0, 1]
        rows = [[width, 1]]

        b = Board(cols, rows, renderer=BaseAsciiRenderer, stream=stream)
        b.draw()

        assert stream.getvalue().rstrip() == '\n'.join([
            '# # 1 1 1 1 1 1 1 1 1 1 0 1',
            '101 _ _ _ _ _ _ _ _ _ _ _ _',
        ])


def clear_stream(s):
    """
    Clears the io stream

    https://stackoverflow.com/a/4330829
    """
    s.truncate(0)
    s.seek(0)
    return s


# noinspection PyShadowingNames
class TestAsciiBoard(object):
    @pytest.fixture
    def board(self, stream):
        return tested_board(renderer=AsciiRenderer, stream=stream)

    def test_draw_empty(self, board, stream):
        board.draw()
        assert stream.getvalue().rstrip() == '\n'.join([
            '+---+---++---+---+---+---+---+---+---+---+',
            '| # | # ||   |   |   | 2 | 2 |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| # | # || 0 | 9 | 9 | 2 | 2 | 4 | 4 | 0 |',
            '|===+===++===+===+===+===+===+===+===+===|',
            '|   | 0 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 4 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 6 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| 2 | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| 2 | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 6 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 4 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 0 ||   |   |   |   |   |   |   |   |',
            '+---+---++---+---+---+---+---+---+---+---+',
        ])

    def test_draw_filled_line(self, board, stream):
        board.cells[2][0] = SPACE
        board.cells[2][1:-1] = [BOX] * 6
        board.cells[2][-1] = SPACE
        board.draw()
        assert stream.getvalue().rstrip() == '\n'.join([
            '+---+---++---+---+---+---+---+---+---+---+',
            '| # | # ||   |   |   | 2 | 2 |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| # | # || 0 | 9 | 9 | 2 | 2 | 4 | 4 | 0 |',
            '|===+===++===+===+===+===+===+===+===+===|',
            '|   | 0 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 4 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 6 || . | X | X | X | X | X | X | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| 2 | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| 2 | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 6 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 4 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 ||   |   |   |   |   |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 0 ||   |   |   |   |   |   |   |   |',
            '+---+---++---+---+---+---+---+---+---+---+',
        ])

    @classmethod
    def one_row_table(cls, width, stream):
        cols = [1] * width
        rows = [width]
        return Board(cols, rows, renderer=AsciiRenderer, stream=stream)

    def test_draw_two_digits(self, stream):
        b = self.one_row_table(13, stream)
        b.draw()

        assert stream.getvalue().rstrip() == '\n'.join([
            '+---++---+---+---+---+---+---+---+---+---+---+---+---+---+',
            '| # || 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |',
            '|===++===+===+===+===+===+===+===+===+===+===+===+===+===|',
            '| 13||   |   |   |   |   |   |   |   |   |   |   |   |   |',
            '+---++---+---+---+---+---+---+---+---+---+---+---+---+---+',
        ])

    def test_draw_three_digits(self, stream):
        the_width = 512
        b = self.one_row_table(the_width, stream)
        b.draw()

        table = stream.getvalue().rstrip().split('\n')
        assert len(table) == 5
        assert table[3] == '|{}||{}|'.format(
            the_width, '|'.join(['   '] * the_width))

    def test_draw_four_digits(self, stream):
        the_width = 1001
        b = self.one_row_table(the_width, stream)
        with pytest.raises(ValueError) as ei:
            b.draw()

        assert str(ei.value) == 'Cannot fit the value 1001 into cell width 3'

    def test_exotic_table_view(self, stream):
        b = self.one_row_table(2, stream)
        b.draw()
        table = stream.getvalue().rstrip()
        assert table == '\n'.join([
            '+---++---+---+',
            '| # || 1 | 1 |',
            '|===++===+===|',
            '| 2 ||   |   |',
            '+---++---+---+',
        ])

        b.renderer.CELL_WIDTH = 5
        b.renderer.HORIZONTAL_LINE_PAD = '*'
        b.renderer.VERTICAL_GRID_SYMBOL = '!'
        b.renderer.HEADER_DELIMITER = '$'
        b.renderer.SIDE_DELIMITER_SIZE = 4
        b.renderer.GRID_CROSS_SYMBOL = 'x'
        b.renderer.CORNER_SYMBOL = '>'
        clear_stream(stream)
        b.draw()

        table = stream.getvalue().rstrip()
        # noinspection SpellCheckingInspection
        assert table == '\n'.join([
            '>*****xxxx*****x*****>',
            '!  #  !!!!  1  !  1  !',
            '!$$$$$xxxx$$$$$x$$$$$!',
            '!  2  !!!!     !     !',
            '>*****xxxx*****x*****>',
        ])

    def test_grid_row(self, stream):
        b = self.one_row_table(1, stream)
        r = b.renderer
        # noinspection PyProtectedMember
        f = r._grid_row

        assert f(border=True, header=False) == '+---++---+'
        assert f(border=False, header=False) == '|---++---|'
        assert f(border=False, header=True) == '|===++===|'
        with pytest.raises(ValueError) as ei:
            f(border=True, header=True)

        assert str(ei.value) == 'Cannot print a row that separates headers as a border row'


# noinspection PyShadowingNames
class TestSvg(object):
    @classmethod
    def one_row_table(cls, width, stream):
        cols = [1] * width
        rows = [width]
        return Board(cols, rows, renderer=SvgRenderer, stream=stream)

    def test_small_table(self, stream):
        b = self.one_row_table(2, stream)
        b.draw()
        table = [line.strip() for line in stream.getvalue().split('\n')]

        svg_def = """
            <svg baseProfile="full" height="45" version="1.1" width="60" xmlns="
            http://www.w3.org/2000/svg" xmlns:ev=
            "http://www.w3.org/2001/xml-events" xmlns:xlink="http://www.w3.org/1999/xlink">
                <defs>
                    <style type="text/css">
                        <![CDATA[
                            g.grid-lines line {
                            stroke-width: 1} g.grid-lines line.bold {
                            stroke-width: 2} g.header-clues text, g.side-clues text {
                            font-size: 9.000000} ]]>
                    </style>
                    <symbol id="box"><rect height="15" width="15" x="0" y="0" /></symbol>
                    <symbol id="space"><circle cx="0" cy="0" r="0.75" /></symbol>
                    <symbol fill="none" id="check" stroke="green">
                        <circle cx="50" cy="50" r="40" stroke-width="10" />
                        <polyline points="35,35 35,55 75,55" stroke-width="
                        12" transform="rotate(-45 50 50)" />
                    </symbol>
                </defs>

                <rect class="nonogram-thumbnail" height="15" width="15" x="0" y="0" />

                <rect class="nonogram-header" height="15" width="30" x="15" y="0" />
                <g class="header-clues">
                    <text fill="currentColor" x="27.75" y="10.5">1</text>
                    <text fill="currentColor" x="42.75" y="10.5">1</text>
                </g>

                <rect class="nonogram-side" height="15" width="15" x="0" y="15" />
                <g class="side-clues">
                    <text fill="currentColor" x="10.5" y="26.25">2</text>
                </g>

                <rect class="nonogram-grid" height="15" width="30" x="15" y="15" />
                <g class="grid-lines">
                    <line class="bold" x1="0" x2="45" y1="15" y2="15" />
                    <line class="bold" x1="0" x2="45" y1="30" y2="30" />
                    <line class="bold" x1="15" x2="15" y1="0" y2="30" />
                    <line x1="30" x2="30" y1="0" y2="30" />
                    <line class="bold" x1="45" x2="45" y1="0" y2="30" />
                </g>
                <g class="box" />
                <g class="space" />
            </svg>"""

        assert table[0] == '<?xml version="1.0" encoding="utf-8" ?>'
        assert table[1] == ''.join([
            line for line in [line.strip() for line in svg_def.split('\n')] if line])
