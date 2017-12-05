# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

# noinspection PyProtectedMember
from pyngrm.base import _solve_on_space_hints
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
