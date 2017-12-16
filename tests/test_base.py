# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

# noinspection PyProtectedMember
from pyngrm.base import (
    _solve_on_space_hints,
    invert,
    BOX, SPACE, UNSURE,
)
from pyngrm.board import BaseBoard


def test_space_hints_solving():
    columns = [3, 1, 3]
    rows = [
        3,
        '1 1',
        '1 1',
    ]
    board = BaseBoard(columns, rows)
    _solve_on_space_hints(board, [[0], [0, 1], [0, 1]])
    assert board.cells.tolist() == [
        [True, True, True],
        [True, False, True],
        [True, False, True],
    ]


def test_invert():
    assert invert(SPACE) is True
    assert invert(BOX) is False
    assert invert(UNSURE) is UNSURE
