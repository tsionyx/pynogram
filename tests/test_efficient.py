# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import pytest

from pynogram.core import propagation
from pynogram.core.board import (
    BlackBoard, make_board,
)
from pynogram.core.color import ColorBlock
from pynogram.core.common import (
    SPACE, SPACE_COLORED as SPACE_C,
    NonogramError,
)
from pynogram.core.line import solve_line
from pynogram.core.line.efficient import EfficientColorSolver
from pynogram.reader import (
    read_example,
    Pbn,
)
from pynogram.utils.other import is_close
from .cases import CASES, BAD_CASES

CASES = CASES + [([], '???', [SPACE, SPACE, SPACE]), ]
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

        board = BlackBoard(columns, rows)

        propagation.solve(board, methods='efficient')
        assert board.is_solved_full


class TestEfficientColorSolver(object):
    # @pytest.mark.parametrize('description,input_row,expected', CASES)
    # def test_solve(self, description, input_row, expected):
    #     assert solve_line(description, input_row, method='eff_color') == tuple(expected)

    @pytest.fixture
    def colors(self):
        return 127

    @classmethod
    def solve_as_color_sets(cls, desc, line):
        return EfficientColorSolver.solve(desc, line)

    @classmethod
    def method_name(cls):
        return 'efficient_color'

    def test_empty(self, colors):
        desc = []
        line = [colors]
        assert tuple(self.solve_as_color_sets(desc, line)) == (SPACE_C,)

    def test_empty2(self, colors):
        desc = []
        line = [colors] * 3
        assert tuple(self.solve_as_color_sets(desc, line)) == (SPACE_C, SPACE_C, SPACE_C)

    def test_simplest(self, colors):
        desc = [ColorBlock(1, 4)]
        line = [colors]
        assert tuple(self.solve_as_color_sets(desc, line)) == (4,)

    def test_undefined(self, colors):
        desc = [ColorBlock(1, 4)]
        line = [colors] * 2
        assert tuple(self.solve_as_color_sets(desc, line)) == (4 | SPACE_C, 4 | SPACE_C)

    def test_same_color(self, colors):
        desc = [ColorBlock(1, 4), ColorBlock(1, 4)]
        line = [colors] * 3
        assert tuple(self.solve_as_color_sets(desc, line)) == (4, SPACE_C, 4)

    def test_different_colors(self, colors):
        desc = [ColorBlock(1, 4), ColorBlock(1, 8)]
        line = [colors] * 3
        assert tuple(self.solve_as_color_sets(desc, line)) == (
            4 | SPACE_C, 4 | 8 | SPACE_C, 8 | SPACE_C)

    def test_lengthy(self, colors):
        desc = [ColorBlock(2, 4), ColorBlock(1, 4), ColorBlock(1, 8)]
        line = [colors] * 5
        assert tuple(self.solve_as_color_sets(desc, line)) == (
            4, 4, SPACE_C, 4, 8)

    def test_lengthy_undefined(self, colors):
        desc = [ColorBlock(2, 4), ColorBlock(1, 4), ColorBlock(1, 8)]
        line = [colors] * 6
        assert tuple(self.solve_as_color_sets(desc, line)) == (
            4 | SPACE_C, 4, 4 | SPACE_C, 4 | SPACE_C, 4 | 8 | SPACE_C, 8 | SPACE_C)

    def test_first_not_space(self, colors):
        desc = (ColorBlock(2, 4), ColorBlock(1, 8))
        line = [4] + [colors] * 3

        assert tuple(self.solve_as_color_sets(desc, line)) == (
            4, 4, 8 | SPACE_C, 8 | SPACE_C)

    def test_bad(self, colors):
        desc = [ColorBlock(2, 4), ColorBlock(1, 4), ColorBlock(1, 8)]
        line = [colors] * 4
        with pytest.raises(NonogramError):
            tuple(self.solve_as_color_sets(desc, line))

    def test_backtracking(self):
        board = make_board(*Pbn.read(4581))
        propagation.solve(board, methods=self.method_name())

        assert is_close(board.solution_rate, 0.75416666667)
        assert len(board.solutions) == 0
