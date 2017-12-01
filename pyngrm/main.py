#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Examples run here
"""

from __future__ import unicode_literals, print_function

from pyngrm.board import AsciiBoard
from pyngrm.state import BOX, SPACE


def _solve_on_space_hints(board, hints):
    """
    Pseudo solving with spaces given
    """
    # assert len(hints) == len(board.rows)
    for i, (spaces_hint, row) in enumerate(zip(hints, board.rows)):
        assert len(spaces_hint) == len(row)
        cells = []
        for space_size, box_size in zip(spaces_hint, row):
            cells.extend([SPACE] * space_size)
            cells.extend([BOX] * box_size)

        # pad with spaces
        solution = cells + ([SPACE] * (board.width - len(cells)))
        board.cells[i] = solution


def solve(board):
    """
    Pseudo solving predefined Wikipedia board
    https://en.wikipedia.org/wiki/Nonogram#/media/File:Nonogram.svg
    """
    _solve_on_space_hints(
        board,
        [
            [0, 1, 1, 1],
            [2, 3, 4, 4],
            [3, 5, 4, 5],
            [3, 5, 3, 5],
            [4, 5, 2, 6],

            [4, 5, 1, 5],
            [4, 5, 6],
            [5, 5, 6],
            [5, 5, 6],
            [6, 5, 5],

            [6, 4, 4],
            [7, 3, 3],
            [7, 3, 1, 3],
            [7, 1, 1, 1],
            [8, 1, 3, 1],

            [8, 3],
            [9, 4],
            [9, 6],
            [9, 6],
            [10, 8],
        ]
    )


def main():
    """
    The main function
    """
    columns = [
        1, 1, 2, 4, 7, 9, '2 8', '1 8', 8, '1 9', '2 7', '3 4',
        '6 4', '8 5', '1 11', '1 7', 8, '1 4 8', '6 8', '4 7',
        '2 4', '1 4', 5, '1 4', '1 5', 7, 5, 3, 1, 1,
    ]
    rows = [
        '8 7 5 7',
        '5 4 3 3',
        '3 3 2 3',
        '4 3 2 2',
        '3 3 2 2',
        '3 4 2 2',
        '4 5 2',
        '3 5 1',
        '4 3 2',
        '3 4 2',
        '4 4 2',
        '3 6 2',
        '3 2 3 1',
        '4 3 4 2',
        '3 2 3 2',
        '6 5',
        '4 5',
        '3 3',
        '3 3',
        '1 1',
    ]

    board = AsciiBoard(columns, rows)
    rend = board.renderer
    rend.ICONS[BOX] = '\u2B1B'
    rend.ICONS[SPACE] = ' '  # '\u2022',

    solve(board)
    board.draw()


if __name__ == '__main__':
    main()
