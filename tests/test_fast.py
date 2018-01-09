# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import pytest

from pyngrm.core.board import Board
from pyngrm.core.solve import (
    NonogramError,
    solve_line,
    line_solver,
)
from pyngrm.input.reader import examples_file, read

# TODO: more solved rows
CASES = [
    ([1, 1, 5], '---#--         -      # ', [
        False, False, False, True, False, False, None, None,
        None, None, None, None, None, None, None, False,
        None, None, None, True, True, True, True, None]),
    ([9, 1, 1, 1], '   --#########-------   #- - ', [
        False, False, False, False, False, True, True, True,
        True, True, True, True, True, True, False, False,
        False, False, False, False, False, None, None, None,
        True, False, None, False, None]),
    ([5, 6, 3, 1, 1], '               #- -----      ##-      ---   #-', [
        None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, True,
        False, None, False, False, False, False, False, None,
        None, None, None, None, None, True, True, False,
        None, None, None, None, None, None, False, False,
        False, None, None, False, True, False]),
    ([4, 2], ' #   .  ', [
        None, True, True, True, None, False, True, True]),
    ([4, 2], ' #  .   ', [
        True, True, True, True, False, None, True, None]),
    ((1, 1, 2, 1, 1, 3, 1), [
        True, False, False, None, None, False, None, True,
        None, False, False, True, None, None, None, None,
        None, True, None, None, None, None], [
         True, False, False, None, None, False, None, True,
         None, False, False, True, False, None, None, None,
         None, True, None, None, None, None]),
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
        assert solve_line(description, input_row, method='simpson') == expected

    @pytest.mark.parametrize('description,input_row,error', BAD_CASES)
    def test_solve_bad_row(self, description, input_row, error):
        with pytest.raises(NonogramError) as ie:
            solve_line(description, input_row, method='simpson')

        assert str(ie.value) == error

    def test_solve_board(self):
        with open(examples_file('w.txt')) as _file:
            columns, rows = read(_file)

        board = Board(columns, rows)

        line_solver.solve(board, methods='simpson')
        assert board.solution_rate == 1
