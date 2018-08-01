# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import pytest

from pynogram.core.board import Board, make_board
from pynogram.core.common import SPACE, ColorBlock
from pynogram.core.solver import line as line_solver
from pynogram.core.solver.base import solve_line
from pynogram.core.solver.common import NonogramError
from pynogram.core.solver.efficient import EfficientColorSolver
from pynogram.reader import read_example, Pbn
from pynogram.utils.other import is_close
from .test_bgu import CASES, BAD_CASES

CASES = CASES + [([], '???', [False, False, False]), ]
BAD_CASES = BAD_CASES + [([], '??#'), ]


class TestFastSolver(object):
    @pytest.mark.parametrize('description,input_row,expected', CASES)
    def test_solve(self, description, input_row, expected):
        assert solve_line(description, tuple(input_row), method='efficient') == tuple(expected)

    @pytest.mark.parametrize('description,input_row', BAD_CASES)
    def test_solve_bad_row(self, description, input_row):
        with pytest.raises(NonogramError):
            solve_line(description, input_row, method='efficient')

    def test_solve_board(self):
        columns, rows = read_example('p')

        board = Board(columns, rows)

        line_solver.solve(board, methods='efficient')
        assert board.is_solved_full


class TestEfficientColorSolver(object):
    # @pytest.mark.parametrize('description,input_row,expected', CASES)
    # def test_solve(self, description, input_row, expected):
    #     assert solve_line(description, input_row, method='eff_color') == tuple(expected)

    @pytest.fixture
    def colors(self):
        return 'r', 'b', SPACE

    def solve_as_color_sets(self, desc, line):
        res = EfficientColorSolver.solve(desc, line)
        for cell in res:
            yield set(cell)

    def test_empty(self, colors):
        desc = []
        line = [colors]
        assert tuple(self.solve_as_color_sets(desc, line)) == ({SPACE},)

    def test_simplest(self, colors):
        desc = [ColorBlock(1, 'b')]
        line = [colors]
        assert tuple(self.solve_as_color_sets(desc, line)) == ({'b'},)

    def test_undefined(self, colors):
        desc = [ColorBlock(1, 'b')]
        line = [colors] * 2
        assert tuple(self.solve_as_color_sets(desc, line)) == ({'b', SPACE}, {'b', SPACE})

    def test_same_color(self, colors):
        desc = [ColorBlock(1, 'b'), ColorBlock(1, 'b')]
        line = [colors] * 3
        assert tuple(self.solve_as_color_sets(desc, line)) == ({'b'}, {SPACE}, {'b'})

    def test_different_colors(self, colors):
        desc = [ColorBlock(1, 'b'), ColorBlock(1, 'r')]
        line = [colors] * 3
        assert tuple(self.solve_as_color_sets(desc, line)) == (
            {False, 'b'}, {False, 'b', 'r'}, {False, 'r'})

    def test_lengthy(self, colors):
        desc = [ColorBlock(2, 'b'), ColorBlock(1, 'b'), ColorBlock(1, 'r')]
        line = [colors] * 5
        assert tuple(self.solve_as_color_sets(desc, line)) == (
            {'b'}, {'b'}, {SPACE}, {'b'}, {'r'})

    def test_lengthy_undefined(self, colors):
        desc = [ColorBlock(2, 'b'), ColorBlock(1, 'b'), ColorBlock(1, 'r')]
        line = [colors] * 6
        assert tuple(self.solve_as_color_sets(desc, line)) == (
            {'b', SPACE}, {'b'}, {'b', SPACE}, {'b', SPACE}, {'b', 'r', SPACE}, {'r', SPACE})

    def test_bad(self, colors):
        desc = [ColorBlock(2, 'b'), ColorBlock(1, 'b'), ColorBlock(1, 'r')]
        line = [colors] * 4
        with pytest.raises(NonogramError):
            tuple(self.solve_as_color_sets(desc, line))

    def test_backtracking(self):
        board = make_board(*Pbn.read(4581))
        line_solver.solve(board, methods='efficient_color')

        assert is_close(board.solution_rate, 0.75416666667)
        assert len(board.solutions) == 0
