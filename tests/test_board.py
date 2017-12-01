# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import pytest

from pyngrm.board import BaseBoard


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
