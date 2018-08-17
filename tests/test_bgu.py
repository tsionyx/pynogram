# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import pytest

from pynogram.core import propagation
from pynogram.core.board import Board
from pynogram.core.common import NonogramError
from pynogram.core.line import solve_line
from pynogram.core.line.bgu import BguColoredSolver
from pynogram.reader import read_example
from .cases import CASES, BAD_CASES
# skip the 'Test' prefix to prevent from running this suite twice
from .test_efficient import TestEfficientColorSolver as ColorTest


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


class TestBguColoredSolver(ColorTest):
    @classmethod
    def solve_as_color_sets(cls, desc, line):
        return BguColoredSolver.solve(desc, line)

    @classmethod
    def method_name(cls):
        return 'bgu_color'
