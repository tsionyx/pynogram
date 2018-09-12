# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import pytest

from pynogram.core import propagation
from pynogram.core.board import (
    BlackBoard,
)
from pynogram.core.color import ColorBlock
from pynogram.core.common import (
    NonogramError,
    BlottedBlock,
)
from pynogram.core.line import solve_line
from pynogram.core.line.bgu import (
    BguColoredSolver,
    BguColoredBlottedSolver,
)
from pynogram.reader import (
    read_example,
)
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

        board = BlackBoard(columns, rows)

        propagation.solve(board, methods='bgu')
        assert board.is_solved_full


class TestBguColoredSolver(ColorTest):
    @classmethod
    def solve_as_color_sets(cls, desc, line):
        return BguColoredSolver.solve(desc, line)

    @classmethod
    def method_name(cls):
        return 'bgu_color'


class TestBguColoredBlotted(object):
    def test_19787(self):
        """13 column from http://webpbn/19787"""
        desc = (
            ColorBlock(size=BlottedBlock, color=16),
            ColorBlock(size=BlottedBlock, color=2),
            ColorBlock(size=BlottedBlock, color=16),
            ColorBlock(size=1, color=2),
            ColorBlock(size=BlottedBlock, color=8),
            ColorBlock(size=BlottedBlock, color=8),
            ColorBlock(size=BlottedBlock, color=16),
        )

        line = (
            17, 17, 19, 19, 19,
            19, 17, 17, 27, 19,
            19, 19, 11, 8, 9,
            9, 9, 9, 9, 9,
            8, 8, 9, 9, 25,
            9, 17, 17, 17, 17,
        )

        assert BguColoredBlottedSolver.block_ranges(desc, line) == [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [2, 3, 4, 5, 8, 9, 10],
            [3, 4, 5, 6, 7, 8, 9, 10, 11],
            [4, 5, 8, 9, 10, 11, 12],
            [8, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
            [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
            [24, 26, 27, 28, 29],
        ]
