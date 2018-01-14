# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

# noinspection PyProtectedMember
from pynogram.core.board import Board, _solve_on_space_hints
from pynogram.core.common import (
    UNKNOWN, BOX, SPACE,
    invert,
)


def test_space_hints_solving():
    columns = [3, 1, 3]
    rows = [
        3,
        '1 1',
        '1 1',
    ]
    board = Board(columns, rows)
    _solve_on_space_hints(board, [[0], [0, 1], [0, 1]])
    assert board.cells == [
        [True, True, True],
        [True, False, True],
        [True, False, True],
    ]


def test_invert():
    assert invert(SPACE) is True
    assert invert(BOX) is False
    assert invert(UNKNOWN) is UNKNOWN
