# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import os

import pytest
from six.moves import StringIO
# noinspection PyUnresolvedReferences
from six.moves.configparser import NoSectionError

from pynogram.core import propagation
from pynogram.core.board import Board
from pynogram.core.common import clues
from pynogram.core.propagation import solve
from pynogram.core.renderer import BaseAsciiRenderer
from pynogram.reader import (
    example_file, read_ini, read_example,
    Pbn, PbnNotFoundError,
    NonogramsOrg,
)
from .test_board import tested_board


class TestReader(object):
    def test_hello(self):
        columns, rows = read_example('hello.txt')

        stream = StringIO()
        board = Board(columns, rows, renderer=BaseAsciiRenderer, stream=stream)
        propagation.solve(board)
        board.draw()

        assert stream.getvalue().rstrip() == '\n'.join([
            '# # # # # # # # #               1 1                          ',
            '# # # # # # # # #               1 1               1   1     5',
            '# # # # # # # # # 7 1 1 1 7 0 3 1 1 2 0 6 0 6 0 3 1 5 1 3 0 1',
            '            1 1 1 X . . . X . . . . . . . . . . . . . . . . X',
            '        1 1 1 1 1 X . . . X . . . . . . X . X . . . . . . . X',
            '    1 1 2 1 1 3 1 X . . . X . . X X . . X . X . . X X X . . X',
            '5 1 1 1 1 1 1 1 1 X X X X X . X . . X . X . X . X . X . X . X',
            '1 1 4 1 1 1 1 1 1 X . . . X . X X X X . X . X . X . X . X . X',
            '  1 1 1 1 1 1 1 1 X . . . X . X . . . . X . X . X . X . X . .',
            '    1 1 2 1 1 3 1 X . . . X . . X X . . X . X . . X X X . . X',
        ])
        assert board.is_solved_full
        # currently the line solver does not mark the board as finished
        # assert board.is_finished

    def test_examples_dir(self):
        assert os.path.isdir(example_file())

    def test_section_typo(self):
        text = '\n'.join(['[clue]', 'rows=1', 'columns=1'])
        stream = StringIO(text)

        with pytest.raises(NoSectionError, match="No section: u?'clues'"):
            read_ini(stream)

    def test_txt_suffix(self):
        columns1, rows1 = read_example('w.txt')
        columns2, rows2 = read_example('w')

        assert columns1 == columns2
        assert rows1 == rows2

    def test_not_existed_file_does_not_append_txt(self):
        assert example_file('board.pbm').endswith('board.pbm')


class TestPbn(object):
    def test_simple(self):
        columns, rows = Pbn.read(1)
        assert columns == [(2, 1), (2, 1, 3), (7,), (1, 3), (2, 1)]
        assert rows == [(2,), (2, 1), (1, 1), (3,), (1, 1), (1, 1), (2,), (1, 1), (1, 2), (2,)]

    def test_absent(self):
        with pytest.raises(PbnNotFoundError, match='5'):
            Pbn.read(5)

    def test_colored(self):
        columns, rows, colors = Pbn.read(898)
        assert colors == {
            'white': ('FFFFFF', '.'),
            'black': ('000000', 'X'),
            'red': ('FF0000', '*'),
            'green': ('00B000', '%'),
        }


class TestNonogramsOrg(object):
    def test_black_and_white(self):
        """http://www.nonograms.org/nonograms/i/4353"""
        solution = NonogramsOrg(4353).read()
        assert solution == [
            [1, 1, 1, 0],
            [0, 0, 1, 1],
            [1, 0, 1, 0],
            [0, 1, 1, 0],
            [1, 1, 1, 0],
            [1, 0, 1, 0],
        ]

    def test_colored(self):
        """http://www.nonograms.org/nonograms2/i/4374"""
        colors, solution = NonogramsOrg(4374).read()

        assert colors == [
            ('fbf204', 0),
            ('000000', 1),
            ('f4951c', 0),
        ]

        assert solution == [
            [0, 0, 0, 1, 0],
            [1, 0, 0, 1, 1],
            [1, 3, 3, 0, 0],
            [2, 3, 3, 0, 0],
            [3, 3, 0, 0, 0],
        ]

    def test_not_found(self):
        with pytest.raises(PbnNotFoundError, match='444444'):
            NonogramsOrg(444444).read()

    def test_black_and_white_with_empty_rows(self):
        """https://en.wikipedia.org/wiki/Nonogram#Example"""
        board = tested_board()
        solve(board)

        sol = board.cells
        columns, rows = clues(sol)

        assert columns == [
            [],
            [9],
            [9],
            [2, 2],
            [2, 2],
            [4],
            [4],
            [],
        ]

        assert rows == [
            [],
            [4],
            [6],
            [2, 2],
            [2, 2],
            [6],
            [4],
            [2],
            [2],
            [2],
            [],
        ]

    def test_colored_clues(self):
        """http://www.nonograms.org/nonograms2/i/4374"""
        sol = NonogramsOrg(4374).read()[1]
        columns, rows = clues(sol)

        assert columns == [
            [(2, 1), (1, 2), (1, 3)],
            [(3, 3)],
            [(2, 3)],
            [(2, 1)],
            [(1, 1)],
        ]

        assert rows == [
            [(1, 1)],
            [(1, 1), (2, 1)],
            [(1, 1), (2, 3)],
            [(1, 2), (2, 3)],
            [(2, 3)],
        ]
