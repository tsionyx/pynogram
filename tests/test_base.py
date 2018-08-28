# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

# noinspection PyProtectedMember
from pynogram.core.board import (
    BlackBoard,
    _solve_on_space_hints,
)
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
    board = BlackBoard(columns, rows)
    _solve_on_space_hints(board, [[0], [0, 1], [0, 1]])
    assert board.cells == [
        [BOX, BOX, BOX],
        [BOX, SPACE, BOX],
        [BOX, SPACE, BOX],
    ]


def test_invert():
    assert invert(SPACE) is BOX
    assert invert(BOX) is SPACE
    assert invert(UNKNOWN) is UNKNOWN
