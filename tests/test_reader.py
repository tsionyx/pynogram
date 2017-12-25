# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import os

import pytest
from six.moves import StringIO

from pyngrm.demo import base_demo_board
from pyngrm.input.reader import examples_file, read
from pyngrm.renderer import StreamRenderer


class TestReader(object):
    def test_hello(self):
        with open(examples_file('hello.txt')) as f:
            columns, rows = read(f)

        stream = StringIO()
        board = base_demo_board(columns, rows,
                                renderer=StreamRenderer, stream=stream)
        board.solve()
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
        assert board.solved

    def test_examples_dir(self):
        assert os.path.isdir(examples_file())

    def test_read_after_eof(self):
        text = '\n'.join(['1', '', '', '1', '', '', 'bad'])
        stream = StringIO(text)

        with pytest.raises(ValueError) as ei:
            read(stream)

        assert str(ei.value) == "Found excess info on the line 6 while EOF expected: 'bad'"

    def test_txt_suffix(self):
        with open(examples_file('w.txt')) as f:
            columns1, rows1 = read(f)

        with open(examples_file('w')) as f:
            columns2, rows2 = read(f)

        assert columns1 == columns2
        assert rows1 == rows2

    def test_not_existed_file_does_not_append_txt(self):
        assert examples_file('board.pbm').endswith('board.pbm')
