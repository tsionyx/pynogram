# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from io import StringIO

import pytest

from pyngrm.board import BaseBoard, ConsoleBoard
from pyngrm.renderer import (
    CellState,
    StreamRenderer,
)


@pytest.fixture
def tested_board(board_cls=BaseBoard, **kwargs):
    """
    Simple example with 'P' letter

    https://en.wikipedia.org/wiki/Nonogram#Example
    """
    c = [[], 9, [9], [2, 2], (2, 2), 4, '4', '']
    r = [
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
    ]
    return board_cls(r, c, **kwargs)


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
            BaseBoard(rows=[1, 2], columns=[2.0, 1])

        assert str(ei.value), 'Bad row: 2.0'

    def test_columns_and_rows_does_not_match(self):
        with pytest.raises(ValueError) as ei:
            BaseBoard(rows=[1, 2], columns=[1, 1])

        assert str(ei.value), \
            'Number of boxes differs: 3 (rows) and 2 (columns)'

    def test_row_does_not_fit(self):
        with pytest.raises(ValueError) as ei:
            BaseBoard(rows=[1, [1, 1]], columns=[1, 1])

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
