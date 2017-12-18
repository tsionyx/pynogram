#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
The program's entry point
"""

from __future__ import unicode_literals, print_function

import codecs
import logging
import sys
from argparse import ArgumentParser

from six import PY2

from pyngrm.board import ConsoleBoard
from pyngrm.demo import base_demo_board
from pyngrm.reader import examples_file, read


def cli_args():
    """Parses the arguments given to the script"""
    parser = ArgumentParser(
        description='Solve predefined board (see in examples/ folder)')

    parser.add_argument('-b', '--board', default='hello',
                        help='board file to solve')
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--draw-final', action='store_true',
                        help='Draw only final result, skip all the intermediate steps')
    return parser.parse_args()


def main(board_file, draw_every_round=True):
    """Solve the given board in terminal with animation"""
    with open(examples_file(board_file)) as _file:
        columns, rows = read(_file)

    d_board = base_demo_board(columns, rows, board_cls=ConsoleBoard)
    d_board.renderer.icons.update({True: '\u2B1B'})
    if draw_every_round:
        d_board.on_solution_round_complete = lambda board: board.draw()

    try:
        d_board.solve_with_contradictions(by_rows=False)
        if not draw_every_round:
            d_board.draw()
    except Exception:
        # draw the last solved cells
        d_board.draw()
        raise


def log_level(verbosity):
    """Returns the log level based on given verbosity"""
    if not verbosity or verbosity < 1:
        return logging.WARNING

    if verbosity == 1:
        return logging.INFO

    return logging.DEBUG


if __name__ == '__main__':
    if PY2:
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)

    ARGS = cli_args()
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d -> %(message)s',
        level=log_level(ARGS.verbose),
    )
    main(ARGS.board, draw_every_round=not ARGS.draw_final)
