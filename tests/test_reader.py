# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import os

import pytest
from six.moves import StringIO

from pyngrm.core.board import Board
from pyngrm.core.solve import line_solver
from pyngrm.input.reader import example_file, read, read_example
from pyngrm.renderer import BaseAsciiRenderer


class TestReader(object):
    def test_hello(self):
        columns, rows = read_example('hello.txt')

        stream = StringIO()
        board = Board(columns, rows, renderer=BaseAsciiRenderer, stream=stream)
        line_solver.solve(board)
        board.draw()

        assert stream.getvalue().rstrip() == '\n'.join([
            '- - - - - - - - -               1 1                          ',
            '- - - - - - - - -               1 1               1   1     5',
            '- - - - - - - - - 7 1 1 1 7 0 3 1 1 2 0 6 0 6 0 3 1 5 1 3 0 1',
            '            1 1 1 X . . . X . . . . . . . . . . . . . . . . X',
            '        1 1 1 1 1 X . . . X . . . . . . X . X . . . . . . . X',
            '    1 1 2 1 1 3 1 X . . . X . . X X . . X . X . . X X X . . X',
            '5 1 1 1 1 1 1 1 1 X X X X X . X . . X . X . X . X . X . X . X',
            '1 1 4 1 1 1 1 1 1 X . . . X . X X X X . X . X . X . X . X . X',
            '  1 1 1 1 1 1 1 1 X . . . X . X . . . . X . X . X . X . X . .',
            '    1 1 2 1 1 3 1 X . . . X . . X X . . X . X . . X X X . . X',
        ])
        assert board.solution_rate == 1
        # currently simple `solve` method does not mark the board as solved
        # assert board.solved

    def test_examples_dir(self):
        assert os.path.isdir(example_file())

    def test_read_after_eof(self):
        text = '\n'.join(['1', '', '', '1', '', '', 'bad'])
        stream = StringIO(text)

        with pytest.raises(ValueError) as ei:
            read(stream)

        assert str(ei.value) == "Found excess info on the line 6 while EOF expected: 'bad'"

    def test_txt_suffix(self):
        columns1, rows1 = read_example('w.txt')
        columns2, rows2 = read_example('w')

        assert columns1 == columns2
        assert rows1 == rows2

    def test_not_existed_file_does_not_append_txt(self):
        assert example_file('board.pbm').endswith('board.pbm')
