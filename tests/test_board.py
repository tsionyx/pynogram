# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from io import StringIO

import pytest

from pyngrm.board import BaseBoard, ConsoleBoard
from pyngrm.renderer import (
    CellState,
    StreamRenderer,
    AsciiRenderer,
)


@pytest.fixture
def tested_board(board_cls=BaseBoard, **kwargs):
    """
    Simple example with 'P' letter

    https://en.wikipedia.org/wiki/Nonogram#Example
    """
    return board_cls(
        [[], 9, [9], [2, 2], (2, 2), 4, '4', ''],
        [
            None,
            4,
            6,
            '2 2',
            [2, 2],
            6,
            4,
            2,
            [2],
            2,
            0,
        ], **kwargs)


class TestBoard(object):
    @pytest.fixture
    def board(self):
        return tested_board()

    def test_rows(self, board):
        assert board.rows == tuple([
            (),
            (4,),
            (6,),
            (2, 2),
            (2, 2),
            (6,),
            (4,),
            (2,),
            (2,),
            (2,),
            (),
        ])

    def test_columns(self, board):
        assert board.columns == tuple([
            (),
            (9,),
            (9,),
            (2, 2),
            (2, 2),
            (4,),
            (4,),
            (),
        ])

    def test_bad_renderer(self):
        with pytest.raises(TypeError) as ei:
            tested_board(renderer=True)

        assert str(ei.value) == 'Bad renderer: True'

    def test_bad_row_value(self):
        with pytest.raises(ValueError) as ei:
            BaseBoard(columns=[2.0, 1], rows=[1, 2])

        assert str(ei.value), 'Bad row: 2.0'

    def test_columns_and_rows_does_not_match(self):
        with pytest.raises(ValueError) as ei:
            BaseBoard(columns=[1, 1], rows=[1, 2])

        assert str(ei.value), \
            'Number of boxes differs: 3 (rows) and 2 (columns)'

    def test_row_does_not_fit(self):
        with pytest.raises(ValueError) as ei:
            BaseBoard(columns=[1, 1], rows=[1, [1, 1]])

        assert str(ei.value), \
            'Cannot allocate row [1, 1] in just 2 cells'


class TestConsoleBoard(object):
    @pytest.fixture
    def stream(self):
        # return open(os.devnull, 'w')
        return StringIO()

    @pytest.fixture
    def board(self, stream):
        return tested_board(ConsoleBoard,
                            renderer=StreamRenderer(stream=stream))

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
        board.cells[2][0] = CellState.SPACE
        board.cells[2][1:-1] = [CellState.BOX] * 6
        board.cells[2][-1] = CellState.SPACE
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


class TestAscciiBoard(TestConsoleBoard):
    @pytest.fixture
    def board(self, stream):
        return tested_board(ConsoleBoard,
                            renderer=AsciiRenderer(stream=stream))

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
        board.cells[2][0] = CellState.SPACE
        board.cells[2][1:-1] = [CellState.BOX] * 6
        board.cells[2][-1] = CellState.SPACE
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
        return ConsoleBoard(cols, rows, renderer=AsciiRenderer(stream=stream))

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
        assert r._grid_row(border=True, header=False) == '+---++---+'
        assert r._grid_row(border=False, header=False) == '|---++---|'
        assert r._grid_row(border=False, header=True) == '|===++===|'
        with pytest.raises(ValueError) as ei:
            r._grid_row(border=True, header=True)

        assert str(ei.value) == 'Cannot print a row that separates headers as a border row'
