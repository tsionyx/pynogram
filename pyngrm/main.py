#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Examples run here
"""

from __future__ import unicode_literals, print_function

import logging

from pyngrm.base import BOX, SPACE
from pyngrm.board import AsciiBoard


def main():
    """
    The main function
    """

    # predefined Wikipedia board
    # https://en.wikipedia.org/wiki/Nonogram#/media/File:Nonogram.svg
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
    rend.ICONS[SPACE] = ' '  # '\u2022'

    board.solve()
    board.draw()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
