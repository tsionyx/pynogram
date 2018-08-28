# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import pytest

from pynogram.core import propagation
from pynogram.core.board import BlackBoard
from pynogram.core.common import (
    BOX, SPACE,
    NonogramError,
)
from pynogram.core.line import solve_line
from pynogram.reader import read_example

# TODO: more solved rows
CASES = [
    ([1, 1, 5], '---#--         -      # ', [
        SPACE, SPACE, SPACE, BOX, SPACE, SPACE, None, None,
        None, None, None, None, None, None, None, SPACE,
        None, None, None, BOX, BOX, BOX, BOX, None]),
    ([9, 1, 1, 1], '   --#########-------   #- - ', [
        SPACE, SPACE, SPACE, SPACE, SPACE, BOX, BOX, BOX,
        BOX, BOX, BOX, BOX, BOX, BOX, SPACE, SPACE,
        SPACE, SPACE, SPACE, SPACE, SPACE, None, None, None,
        BOX, SPACE, None, SPACE, None]),
    ([5, 6, 3, 1, 1], '               #- -----      ##-      ---   #-', [
        None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, BOX,
        SPACE, None, SPACE, SPACE, SPACE, SPACE, SPACE, None,
        None, None, None, None, None, BOX, BOX, SPACE,
        None, None, None, None, None, None, SPACE, SPACE,
        SPACE, None, None, SPACE, BOX, SPACE]),
    ([4, 2], ' #   .  ', [
        None, BOX, BOX, BOX, None, SPACE, BOX, BOX]),
    ([4, 2], ' #  .   ', [
        BOX, BOX, BOX, BOX, SPACE, None, BOX, None]),
    ((1, 1, 2, 1, 1, 3, 1),
     [
         BOX, SPACE, SPACE, None, None, SPACE, None, BOX,
         None, SPACE, SPACE, BOX, None, None, None, None,
         None, BOX, None, None, None, None], [
         BOX, SPACE, SPACE, None, None, SPACE, None, BOX,
         None, SPACE, SPACE, BOX, SPACE, None, None, None,
         None, BOX, None, None, None, None]),
]

BAD_CASES = [
    ([4, 2], ' # .    ',
     'All previous blocks cover solids'),
    ([4, 2], ' #   .# #',
     'The 1-th block cannot be stretched'),
    ((5, 3, 2, 2, 4, 2, 2),
     '-#####----###-----------##-                          ###   ',
     'No room left: cannot fit 6-th block'),
]


class TestFastSolver(object):
    @pytest.mark.parametrize('description,input_row,expected', CASES)
    def test_solve(self, description, input_row, expected):
        assert solve_line(description, tuple(input_row), method='simpson') == tuple(expected)

    @pytest.mark.parametrize('description,input_row,error', BAD_CASES)
    def test_solve_bad_row(self, description, input_row, error):
        with pytest.raises(NonogramError) as ie:
            solve_line(description, input_row, method='simpson')

        str_ex = str(ie.value)
        assert str_ex.startswith('FastSolver: Failed to solve line')
        assert str_ex.endswith(': ' + error)

    def test_solve_board(self):
        columns, rows = read_example('w')

        board = BlackBoard(columns, rows)

        propagation.solve(board, methods='simpson')
        assert board.is_solved_full
