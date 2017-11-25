# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from io import StringIO
from unittest import TestCase

from pyngrm.board import BaseBoard, CellState, ConsoleBoard, StreamRenderer


def tested_board(board_cls=BaseBoard, **kwargs):
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
    return board_cls(r, c, **kwargs)


class BoardTest(TestCase):
    def setUp(self):
        self.board = tested_board()

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

    def test_bad_renderer(self):
        with self.assertRaises(TypeError) as cm:
            tested_board(renderer=True)

        self.assertEqual(str(cm.exception), 'Bad renderer: True')

    def test_bad_row_value(self):
        with self.assertRaises(ValueError) as cm:
            BaseBoard(rows=[1, 2], columns=[2.0, 1])

        self.assertEqual(str(cm.exception), 'Bad row: 2.0')

    def test_columns_and_rows_does_not_match(self):
        with self.assertRaises(ValueError) as cm:
            BaseBoard(rows=[1, 2], columns=[1, 1])

        self.assertEqual(str(cm.exception),
                         'Number of boxes differs: 3 (rows) and 2 (columns)')

    def test_row_does_not_fit(self):
        with self.assertRaises(ValueError) as cm:
            BaseBoard(rows=[1, [1, 1]], columns=[1, 1])

        self.assertEqual(str(cm.exception),
                         'Cannot allocate row [1, 1] in just 2 cells')


class ConsoleBoardTest(TestCase):
    def setUp(self):
        # devnull = open(os.devnull, 'w')
        self.stream = StringIO()
        self.board = tested_board(ConsoleBoard,
                                  renderer=StreamRenderer(stream=self.stream))

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

    def test_bad_cell_value(self):
        self.board.cells[2][0] = str('space')
        with self.assertRaises(KeyError) as cm:
            self.board.draw()

        self.assertEqual(str(cm.exception), "'space'")
