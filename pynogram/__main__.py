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

from pynogram.__version__ import __version__
from pynogram.core.board import make_board
from pynogram.core.solver import contradiction as contradiction_solver
from pynogram.reader import read_example, Pbn
from pynogram.renderer import BaseAsciiRenderer


def cli_args():
    """Parses the arguments given to the script"""
    parser = ArgumentParser(
        description='Solve predefined board (see in examples/ folder)')

    parser.add_argument('--version', action='store_true',
                        help='show version and exit')
    parser.add_argument('-b', '--board', default='hello',
                        help='board file to solve')
    parser.add_argument('--pbn', type=int,
                        help='ID of a board to solve on the http://webpbn.com')
    parser.add_argument('--verbose', '-v', action='count',
                        help='increase logging level')
    parser.add_argument('--draw-final', action='store_true',
                        help='draw only final result, skip all the intermediate steps')
    return parser.parse_args()


def draw_solution(board_def, every_round=True):
    """Solve the given board in terminal with animation"""

    d_board = make_board(*board_def, renderer=BaseAsciiRenderer)
    d_board.renderer.icons.update({True: '\u2B1B'})
    if every_round:
        d_board.on_solution_round_complete = lambda board: board.draw()

    try:
        contradiction_solver.solve(d_board, by_rows=False)
        if not every_round:
            d_board.draw()
    except Exception:
        # draw the last solved cells
        d_board.draw()
        raise


def log_level(verbosity):
    """Returns the log level based on given verbosity"""
    if not verbosity or verbosity < 1:
        return logging.ERROR

    if verbosity == 1:
        return logging.WARNING
    elif verbosity == 2:
        return logging.INFO

    return logging.DEBUG


def main():
    """Main function for setuptools console_scripts"""
    if PY2:
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)

    args = cli_args()
    if args.version:
        print(__version__)
        return

    logging.basicConfig(
        format='[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d -> %(message)s',
        level=log_level(args.verbose),
    )

    if args.pbn:
        board_def = Pbn.read(args.pbn)
    else:
        board_def = read_example(args.board)

    draw_solution(board_def, every_round=not args.draw_final)


if __name__ == '__main__':
    main()
