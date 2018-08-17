# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import pytest

from pynogram.core import propagation
from pynogram.core.board import Board
from pynogram.core.common import NonogramError
from pynogram.core.line import solve_line
from pynogram.reader import read_example
from .cases import CASES, BAD_CASES


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
