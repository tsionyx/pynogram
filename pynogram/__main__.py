#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The program's entry point
"""

from __future__ import unicode_literals, print_function

import json
import logging
from argparse import ArgumentParser

from pynogram.__version__ import __version__
from pynogram.core.board import make_board
from pynogram.core.common import BOX
from pynogram.core.solver.contradiction import Solver
from pynogram.reader import read_example, Pbn, PbnLocal
from pynogram.renderer import BaseAsciiRenderer


def cli_args():
    """Parses the arguments given to the script"""
    parser = ArgumentParser(
        description='Solve predefined board (see in examples/ folder)')

    parser.add_argument('--version', action='store_true',
                        help='show version and exit')

    puzzle_source = parser.add_mutually_exclusive_group()
    puzzle_source.add_argument('-b', '--board', default='hello',
                               help='board file to solve')
    puzzle_source.add_argument('--pbn', type=int,
                               help='ID of a board to solve on the http://webpbn.com')
    puzzle_source.add_argument('--local-pbn',
                               help='read PBN-formatted puzzle from a local file')

    parser.add_argument('--max-solutions', type=int,
                        help='stop after finding specified number of solutions')
    parser.add_argument('--timeout', type=int,
                        help='stop if the searching took too long (in seconds)')
    parser.add_argument('--max-depth', type=int,
                        help='try to solve without getting too deep into search')

    parser.add_argument('--verbose', '-v', action='count',
                        help='increase logging level')
    parser.add_argument('--draw-final', action='store_true',
                        help='draw only final result, skip all the intermediate steps')
    return parser.parse_args()


def draw_solution(board_def, every_round=True, box_symbol=None, **solver_args):
    """Solve the given board in terminal with animation"""

    d_board = make_board(*board_def, renderer=BaseAsciiRenderer)
    if box_symbol is not None:
        d_board.renderer.icons.update({BOX: box_symbol})
    if every_round:
        d_board.on_solution_round_complete = lambda board: board.draw()

    solver = Solver(d_board, **solver_args)

    exc = False
    try:
        solver.solve()
    except BaseException:
        exc = True
        raise
    finally:
        if exc or not every_round:
            # draw the last solved cells
            d_board.draw()

        if not d_board.is_solved_full:
            d_board.draw_solutions()

        if solver.search_map:
            print(json.dumps(solver.search_map.to_dict(), indent=1))


def log_level(verbosity):
    """Returns the log level based on given verbosity"""
    if not verbosity or verbosity < 1:
        return logging.ERROR

    if verbosity == 1:
        return logging.WARNING
    elif verbosity == 2:
        return logging.INFO

    return logging.DEBUG


def _setup_logs(
        level,
        format_='[%(asctime)s] '
                '%(levelname)-8s %(filename)s(%(module)s):%(lineno)d -> %(message)s'):
    console = logging.StreamHandler()

    try:
        from tornado.log import LogFormatter
        format_ = '%(color)s' + format_.replace('%(lineno)d', '%(lineno)d%(end_color)s')
    except ImportError:
        from logging import Formatter as LogFormatter

    formatter = LogFormatter(format_)
    console.setFormatter(formatter)

    logging.getLogger('').addHandler(console)
    logging.getLogger('').setLevel(level)


def main():
    """Main function for setuptools console_scripts"""
    args = cli_args()
    if args.version:
        print(__version__)
        return

    _setup_logs(log_level(args.verbose))

    if args.pbn:
        board_def = Pbn.read(args.pbn)
    elif args.local_pbn:
        board_def = PbnLocal.read(args.local_pbn)
    else:
        board_def = read_example(args.board)

    draw_solution(board_def,
                  box_symbol='\u2B1B',
                  every_round=not args.draw_final,
                  max_solutions=args.max_solutions,
                  timeout=args.timeout,
                  max_depth=args.max_depth)


if __name__ == '__main__':
    main()
