#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
The program's entry point
"""

from __future__ import unicode_literals, print_function

import logging

from pyngrm.board import ConsoleBoard
from pyngrm.demo import base_demo_board
from pyngrm.reader import examples_file, read


def main():
    """Traditional main function"""
    with open(examples_file('hello.txt')) as _file:
        columns, rows = read(_file)

    d_board = base_demo_board(columns, rows, board_cls=ConsoleBoard)
    d_board.renderer.icons.update({True: '\u2B1B'})
    d_board.on_solution_round_complete = lambda board: board.draw()

    try:
        d_board.solve_with_contradictions(by_rows=False)
    finally:
        d_board.draw()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
