# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import unittest
from io import StringIO

from pyngrm.board import CellState, ConsoleBoard, StreamRenderer


class ConsoleBoardTest(unittest.TestCase):
    def setUp(self):
        """
        Simple example with 'P' letter

        https://en.wikipedia.org/wiki/Nonogram#Example
        """
        c = [[], 9, [9], [2, 2], (2, 2), 4, '4', '']
        r = [
            None,
            4,
            6,
            '2 2',
            [2, 2],
            6,
            4,
            2,
            [2],
            2,
            0,
        ]

        # devnull = open(os.devnull, 'w')
        self.stream = StringIO()

        self.board = ConsoleBoard(
            r, c, renderer=StreamRenderer(stream=self.stream))

    def test_rows(self):
        self.assertTupleEqual(
            self.board.rows, tuple([
                (),
                (4,),
                (6,),
                (2, 2),
                (2, 2),
                (6,),
                (4,),
                (2,),
                (2,),
                (2,),
                (),
            ]))

    def test_columns(self):
        self.assertTupleEqual(
            self.board.columns, tuple([
                (),
                (9,),
                (9,),
                (2, 2),
                (2, 2),
                (4,),
                (4,),
                (),
            ]))

    def test_draw_empty(self):
        self.board.draw()
        self.assertEqual(
            self.stream.getvalue().rstrip(), '\n'.join([
                't t       2 2      ',
                't t 0 9 9 2 2 4 4 0',
                '  0 _ _ _ _ _ _ _ _',
                '  4 _ _ _ _ _ _ _ _',
                '  6 _ _ _ _ _ _ _ _',
                '2 2 _ _ _ _ _ _ _ _',
                '2 2 _ _ _ _ _ _ _ _',
                '  6 _ _ _ _ _ _ _ _',
                '  4 _ _ _ _ _ _ _ _',
                '  2 _ _ _ _ _ _ _ _',
                '  2 _ _ _ _ _ _ _ _',
                '  2 _ _ _ _ _ _ _ _',
                '  0 _ _ _ _ _ _ _ _',
            ]))

    def test_draw_filled_line(self):
        self.board.cells[2][0] = CellState.SPACE
        self.board.cells[2][1:-1] = [CellState.BOX] * 6
        self.board.cells[2][-1] = CellState.SPACE
        self.board.draw()
        self.assertEqual(
            self.stream.getvalue().rstrip(), '\n'.join([
                't t       2 2      ',
                't t 0 9 9 2 2 4 4 0',
                '  0 _ _ _ _ _ _ _ _',
                '  4 _ _ _ _ _ _ _ _',
                '  6 . X X X X X X .',
                '2 2 _ _ _ _ _ _ _ _',
                '2 2 _ _ _ _ _ _ _ _',
                '  6 _ _ _ _ _ _ _ _',
                '  4 _ _ _ _ _ _ _ _',
                '  2 _ _ _ _ _ _ _ _',
                '  2 _ _ _ _ _ _ _ _',
                '  2 _ _ _ _ _ _ _ _',
                '  0 _ _ _ _ _ _ _ _',
            ]))
