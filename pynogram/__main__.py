#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The program's entry point
"""

from __future__ import unicode_literals, print_function

import json
import locale
import logging
import platform
from argparse import ArgumentParser
from datetime import datetime
from threading import Thread

try:
    import curses
except ImportError:
    curses = None

from six import (
    PY2,
    text_type,
)
from six.moves import queue

from pynogram.__version__ import __version__
from pynogram.animation import (
    CursesRenderer,
    StringsPager,
)
from pynogram.core.board import make_board
from pynogram.core.common import BOX
from pynogram.core.backtracking import Solver
from pynogram.core.renderer import BaseAsciiRenderer
from pynogram.reader import (
    read_example, example_file,
    Pbn, PbnLocal,
    NonogramsOrg,
)


def cli_args():
    """Parses the arguments given to the script"""
    parser = ArgumentParser(
        description='Solve predefined board (see in examples/ folder)')

    parser.add_argument('--version', action='store_true',
                        help='show version and exit')
    parser.add_argument('--show-examples-folder', action='store_true',
                        help='show the path to examples folder and exit')

    puzzle_source = parser.add_mutually_exclusive_group()
    puzzle_source.add_argument('-b', '--board', default='hello',
                               help='board file to solve')
    puzzle_source.add_argument('--pbn', type=int,
                               help='ID of a board to solve on the http://webpbn.com')
    puzzle_source.add_argument('--local-pbn',
                               help='read PBN-formatted puzzle from a local file')
    puzzle_source.add_argument('--nonograms-org', type=int,
                               help='read a puzzle from nonograms.org')

    parser.add_argument('--max-solutions', type=int,
                        help='stop after finding specified number of solutions')
    parser.add_argument('--timeout', type=int,
                        help='stop if the searching took too long (in seconds)')
    parser.add_argument('--max-depth', type=int,
                        help='try to solve without getting too deep into search')

    parser.add_argument('--verbose', '-v', action='count',
                        help='increase logging level')

    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument('--draw-final', action='store_true',
                             help='draw only final result, skip all the intermediate steps')
    output_mode.add_argument('--curses', action='store_true',
                             help='use curses for solving animation (experimental)')

    parser.add_argument('--draw-probes', action='store_true',
                        help='print probes map (if backtracking was used)')

    args = parser.parse_args()
    if args.draw_probes and args.curses:
        parser.error('Drawing probes do not supported in curses mode')
    return args


def solve(d_board, draw_final=False, draw_probes=False, **solver_args):
    """
    Wrapper for solver that handles errors and prints out the results
    """

    if not draw_final:
        d_board.on_solution_round_complete = lambda board: board.draw()

    solver = Solver(d_board, **solver_args)

    exc = False
    try:
        solver.solve()
    except BaseException:
        exc = True
        raise
    finally:
        if exc or draw_final:
            # draw the last solved cells
            d_board.draw()

        if not d_board.is_solved_full:
            d_board.draw_solutions()

        if draw_probes and solver.search_map:
            print(json.dumps(solver.search_map.to_dict(), indent=1))


class PagerWithUptime(StringsPager):
    """
    StringsPager that inserts the small counter
    in the upper left corner of curses window
    """

    def __init__(self, *args, **kwargs):
        super(PagerWithUptime, self).__init__(*args, **kwargs)
        self.start_time = datetime.now()

    @property
    def _last_update_timestamp(self):
        delta = datetime.now() - self.start_time
        delta = text_type(delta)
        # chop off microseconds
        return delta.split('.')[0]

    def update(self):
        redraw = super(PagerWithUptime, self).update()
        if redraw:
            self.put_line(self._last_update_timestamp, y_position=0, start_index=0)
            self.move_cursor(self.current_draw_position, 0)

        return redraw


def draw_solution(board_def, draw_final=False, box_symbol=None,
                  curses_animation=False, **solver_args):
    """Solve the given board in terminal with animation"""

    try:
        # to correctly print non-ASCII box symbols
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        pass

    if curses_animation:
        if draw_final:
            logging.warning('No need to use curses with draw_final=True')
            curses_animation = False

    if curses_animation:
        board_queue = queue.Queue()
        d_board = make_board(*board_def, renderer=CursesRenderer, stream=board_queue)

        if box_symbol is not None:
            d_board.renderer.icons.update({BOX: box_symbol})

        thread = Thread(target=solve, args=(d_board,), kwargs=solver_args)
        thread.daemon = True
        thread.start()
        curses.wrapper(PagerWithUptime.draw, board_queue)
    else:
        d_board = make_board(*board_def, renderer=BaseAsciiRenderer)

        if box_symbol is not None:
            d_board.renderer.icons.update({BOX: box_symbol})

        solve(d_board, draw_final=draw_final, **solver_args)


def log_level(verbosity):
    """Returns the log level based on given verbosity"""
    if not verbosity or verbosity < 1:
        return logging.ERROR

    if verbosity == 1:
        return logging.WARNING

    if verbosity == 2:
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

    if args.show_examples_folder:
        print(example_file())
        return

    is_windows = platform.system() == 'Windows'
    is_pypy2 = PY2 and platform.python_implementation() == 'PyPy'
    is_curses = args.curses

    if is_curses and is_windows:
        exit('Curses do not supported on Windows')

    _setup_logs(log_level(args.verbose))

    if args.pbn:
        board_def = Pbn.read(args.pbn)
    elif args.local_pbn:
        board_def = PbnLocal.read(args.local_pbn)
    elif args.nonograms_org:
        board_def = NonogramsOrg.read(args.nonograms_org)
    else:
        board_def = read_example(args.board)

    # the Windows does not support Unicode, so does the curses on PyPy2
    if (is_curses and is_pypy2) or is_windows:
        box_symbol = '#'
    else:
        box_symbol = '\u2B1B'

    draw_solution(board_def,
                  box_symbol=box_symbol,
                  draw_final=args.draw_final,
                  draw_probes=args.draw_probes,
                  curses_animation=is_curses,
                  max_solutions=args.max_solutions,
                  timeout=args.timeout,
                  max_depth=args.max_depth)


if __name__ == '__main__':
    main()
