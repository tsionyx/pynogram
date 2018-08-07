# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import pytest

from pynogram.core import propagation
from pynogram.core.board import Board
from pynogram.core.common import NonogramError
from pynogram.core.line import solve_line
from pynogram.reader import read_example

# TODO: more solved rows
CASES = [
    ([], '???', [False, False, False]),
    ([1, 1, 5], '---#--         -      # ', [
        False, False, False, True, False, False, None, None,
        None, None, None, None, None, None, None, False,
        None, None, None, True, True, True, True, None]),
    ([9, 1, 1, 1], '   --#########-------   #- - ', [
        False, False, False, False, False, True, True, True,
        True, True, True, True, True, True, False, False,
        False, False, False, False, False, None, None, False,
        True, False, None, False, None]),
    ([5, 6, 3, 1, 1], '               #- -----      ##-      ---   #-', [
        None, None, None, None, None, None, None, None,
        None, False, None, True, True, True, True, True,
        False, False, False, False, False, False, False, False,
        False, None, None, None, True, True, True, False,
        None, None, None, None, None, None, False, False,
        False, None, None, False, True, False]),
    ([4, 2], ' #   .  ', [
        None, True, True, True, None, False, True, True]),
    ([4, 2], ' #  .   ', [
        True, True, True, True, False, None, True, None]),
    ((1, 1, 2, 1, 1, 3, 1),
     [
         True, False, False, None, None, False, None, True,
         None, False, False, True, None, None, None, None,
         None, True, None, None, None, None], [
         True, False, False, None, None, False, None, True,
         None, False, False, True, False, None, None, None,
         None, True, None, None, None, None]),
]

BAD_CASES = [
    ([4, 2], ' # .    '),
    ([4, 2], ' #   .# #'),
    ((5, 3, 2, 2, 4, 2, 2),
     '-#####----###-----------##-                          ###   '),
]


class TestBguSolver(object):
    @pytest.mark.parametrize('description,input_row,expected', CASES)
    def test_solve(self, description, input_row, expected):
        assert solve_line(description, input_row, method='bgu') == tuple(expected)

    @pytest.mark.parametrize('description,input_row', BAD_CASES)
    def test_solve_bad_row(self, description, input_row):
        with pytest.raises(NonogramError):
            solve_line(description, input_row, method='bgu')

    def test_solve_board(self):
        columns, rows = read_example('w')

        board = Board(columns, rows)

        propagation.solve(board, methods='bgu')
        assert board.is_solved_full
