# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from io import StringIO

import pytest

from pyngrm.base import BOX, SPACE
from pyngrm.board import ConsoleBoard, AsciiBoard
from pyngrm.renderer import Renderer
from .test_board import tested_board


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
        renderer.board_init(ConsoleBoard([], []))
        assert prev_board != id(renderer.board)


class TestConsoleBoard(object):
    @pytest.fixture
    def stream(self):
        # return open(os.devnull, 'w')
        return StringIO()

    @pytest.fixture
    def board(self, stream):
        return tested_board(ConsoleBoard, stream=stream)

    def test_draw_empty(self, board, stream):
        board.draw()
        assert stream.getvalue().rstrip() == '\n'.join([
            't t       2 2      ',
            't t 0 9 9 2 2 4 4 0',
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
            't t       2 2      ',
            't t 0 9 9 2 2 4 4 0',
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


def clear_stream(s):
    """
    Clears the io stream

    https://stackoverflow.com/a/4330829
    """
    s.truncate(0)
    s.seek(0)
    return s


class TestAsciiBoard(TestConsoleBoard):
    @pytest.fixture
    def board(self, stream):
        return tested_board(AsciiBoard, stream=stream)

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
        return AsciiBoard(cols, rows, stream=stream)

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
