# -*- coding: utf-8 -*
"""
Demos and examples
"""

from __future__ import unicode_literals, print_function

from pyngrm.base import BOX, SPACE
from pyngrm.board import BaseBoard
from pyngrm.reader import examples_file, read
from pyngrm.renderer import AsciiRendererWithBold, AsciiRenderer, Renderer


def base_demo_board(columns, rows, board_cls=BaseBoard,
                    renderer=AsciiRendererWithBold, **rend_params):
    """
    :param columns:
    :param rows:
    :type board_cls: Type[BaseBoard]
    :type renderer: Type[Renderer]
    """
    if board_cls == BaseBoard:
        if isinstance(renderer, type) and issubclass(renderer, Renderer):
            renderer = renderer(**rend_params)

        rend_params = dict(renderer=renderer)

    return board_cls(columns, rows, **rend_params)


def demo_board(**kwargs):
    """
    The demonstration board with the 'W' letter
    source: https://en.wikipedia.org/wiki/Nonogram#/media/File:Nonogram.svg
    """
    with open(examples_file('w.txt')) as _file:
        columns, rows = read(_file)
    return base_demo_board(columns, rows, **kwargs)


def p_board(**kwargs):
    """
    Very simple demonstration board with the 'P' letter
    source: https://en.wikipedia.org/wiki/Nonogram#Example
    """
    columns = [[], 9, [9], [2, 2], (2, 2), 4, '4', '']
    rows = [
        None,
        4,
        6,
        '2 2',
        [2] * 2,
        6,
        4,
        2,
        [2],
        2,
        0,
    ]
    return base_demo_board(columns, rows, **kwargs)


def demo_board2(**kwargs):
    """
    Easy board with customized cells icons
    """
    board = p_board(**kwargs)
    board.renderer.icons.update({BOX: '\u2B1B', SPACE: '\u2022'})
    return board


def more_complex_board(renderer=AsciiRenderer, **kwargs):
    # noinspection SpellCheckingInspection
    """
    The board from a magazine.
    Currently it takes 29 rounds to solve it.

    Time consuming (8-cores Intel(R) Xeon(R) CPU E3-1275 v5 @ 3.60GHz):
    py27:
        8.4 seconds with multiprocessing;
        2.2 seconds in a single process.

    py35:
        8.5 seconds with multiprocessing;
        1.7 seconds in a single process.
    """
    with open(examples_file('intermediate.txt')) as _file:
        columns, rows = read(_file)
    return base_demo_board(columns, rows, renderer=renderer, **kwargs)
