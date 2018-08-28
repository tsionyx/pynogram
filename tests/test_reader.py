# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import os

import pytest
from six.moves import StringIO
# noinspection PyUnresolvedReferences
from six.moves.configparser import NoSectionError

from pynogram.core import propagation
from pynogram.core.board import BlackBoard
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
        board = BlackBoard(columns, rows, renderer=BaseAsciiRenderer, stream=stream)
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
        assert [(c.name, c.rgb, c.symbol) for c in colors.iter_colors()] == [
            ('white', 'FFFFFF', '.'),
            ('black', '000000', 'X'),
            ('red', 'FF0000', '*'),
            ('green', '00B000', '%'),
        ]


class TestCluesGenerator(object):
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


class TestNonogramsOrg(object):
    def test_black_and_white(self):
        """http://www.nonograms.org/nonograms/i/4353"""
        n = NonogramsOrg(4353)
        colors, solution = n.definition()
        assert solution == [
            [1, 1, 1, 0],
            [0, 0, 1, 1],
            [1, 0, 1, 0],
            [0, 1, 1, 0],
            [1, 1, 1, 0],
            [1, 0, 1, 0],
        ]
        columns, rows = n.parse()
        assert columns == [[1, 1, 2], [1, 2], [6], [1]]
        assert rows == [[3], [2], [1, 1], [2], [3], [1, 1]]

    def test_colored(self):
        """http://www.nonograms.org/nonograms2/i/4374"""
        n = NonogramsOrg(4374)

        colors, solution = n.definition()

        assert colors == ['fbf204', '000000', 'f4951c']

        assert solution == [
            [0, 0, 0, 1, 0],
            [1, 0, 0, 1, 1],
            [1, 3, 3, 0, 0],
            [2, 3, 3, 0, 0],
            [3, 3, 0, 0, 0],
        ]

        columns, rows, colors = n.parse()
        assert columns == [
            [(2, 'color-1'), (1, 'black'), (1, 'color-3')],
            [(3, 'color-3')],
            [(2, 'color-3')],
            [(2, 'color-1')],
            [(1, 'color-1')],
        ]

        assert rows == [
            [(1, 'color-1')],
            [(1, 'color-1'), (2, 'color-1')],
            [(1, 'color-1'), (2, 'color-3')],
            [(1, 'black'), (2, 'color-3')],
            [(2, 'color-3')],
        ]

        assert set(colors) == {'black', 'white', 'color-1', 'color-3'}

    def test_not_found(self):
        with pytest.raises(PbnNotFoundError, match='444444'):
            NonogramsOrg(444444).parse()

    @pytest.mark.skip('Now it is found on .org too')
    def test_not_found_on_org_but_found_on_ru(self):
        x = 19836
        with pytest.raises(PbnNotFoundError):
            NonogramsOrg(x).parse()

        columns, rows, colors = NonogramsOrg.read(x)
        assert set(colors) == {
            'black', 'white',
            'color-1', 'color-2',
            'color-4', 'color-5',
            'color-6', 'color-7',
        }
