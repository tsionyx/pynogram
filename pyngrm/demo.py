# -*- coding: utf-8 -*
"""
Demos and examples
"""

from __future__ import unicode_literals, print_function

from pyngrm.base import BOX, SPACE
from pyngrm.board import BaseBoard
from pyngrm.renderer import AsciiRendererWithBold, AsciiRenderer, Renderer


def demo_board(renderer=AsciiRendererWithBold, **rend_params):
    """
    The demonstration board with the 'W' letter
    source: https://en.wikipedia.org/wiki/Nonogram#/media/File:Nonogram.svg
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

    renderer = renderer(**rend_params)
    # renderer.icons.update({BOX: '\u2B1B', SPACE: '\u2022'})
    return BaseBoard(columns, rows, renderer=renderer)


def p_board(board_cls=BaseBoard, renderer=AsciiRendererWithBold, **rend_params):
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
        [2, 2],
        6,
        4,
        2,
        [2],
        2,
        0,
    ]

    if board_cls == BaseBoard:
        if renderer is Renderer:
            renderer = renderer(**rend_params)

        rend_params = dict(renderer=renderer)

    return board_cls(columns, rows, **rend_params)


def demo_board2(board_cls=BaseBoard, renderer=AsciiRendererWithBold, **rend_params):
    """
    Easy board with customized cells icons
    """
    board = p_board(board_cls, renderer=renderer, **rend_params)
    board.renderer.icons.update({BOX: '\u2B1B', SPACE: '\u2022'})
    return board


def more_complex_board(renderer=AsciiRenderer, **rend_params):
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
    renderer = renderer(**rend_params)

    cols = [
        '14 9',
        '3 2 10',
        '3 12 1 3 1 4',
        '2 2 4 3 1 1 4 5',
        '5 4 3 1 3 1 3 1 4',

        '3 1 2 3 5 1 10',
        '3 4 3 3 1 1 2 3 2',
        '3 2 1 3 4 1 1 1',
        '7 3 3 3 2 1 5',
        '8 5 4 3 2 1 1',

        '2 2 4 1 3',
        '9 3 8 5',
        '1 3 1 4',
        '7 1 8 2 5 1',
        '7 1 1 4 3',

        '7 1 1 5 3',
        '3 3 1 15 1 5 5',
        '7 1 15 2 6 5',
        '1 5 1 4 3 4',
        '9 4 1 4 3 4',

        '4 8 1 3 3 2',
        '9 4 1 2 1 3 2',
        '1 4 8 2 3 2 5',
        '7 1 4 1 2 5',
        '3 3 1 4 8 1 5 3',

        '7 1 4 1 4 3',
        '7 1 2 2 5 1',
        '7 1 15 1 1 4',
        '1 15 1 5',
        '9 1 3',
    ]

    rows = [
        '2 1 5 1 1 5 1',
        '2 1 5 1 1 5 1',
        '2 1 5 1 1 5 1',
        '2 1 3 1 1 1 1 3 1',
        '2 1 5 1 1 5 1',

        '2 1 5 1 1 5 1',
        '2 1 5 1 1 5 1',
        '1 1 1 1 1',
        '9 9',
        6,

        '8 3 2',
        '8 3 2',
        '1 1 13',
        '2 2 13',
        '2 2 10 2',

        '1 1 2 7 2',
        [2] * 4,
        '1 5 2 1 2 1 1 1 2',
        '2 2 5 2 2 1 1 1 2',
        '1 5 4 1 2 1 1 1 2',

        '1 10 1 2 1 1 1 2',
        '1 1 1 1 2 1 1 1 2',
        '1 1 6 1 1 2 1 1 1 2',
        '1 1 6 1 1 2 1 1 1 2',
        '1 1 6 1 1 2 1 1 1 2',

        [1] * 4,
        '1 5 4 6 3',
        '1 2 5 5 5',
        '1 6 3 3',
        '1 1 2 1 3 2',

        '1 6 4 4',
        '2 8 1 6',
        '9 12 5',
        '11 4',
        '7 8 4',

        '7 5 4',
        '6 2 1 1',
        '2 1 2 1 4',
        '3 3 1 4',
        '2 1 2 1 4',

        '6 2 2 2',
        '7 6 5',
        '7 7 6',
        '5 7 4',
        '5 2',
    ]

    return BaseBoard(cols, rows, renderer=renderer)
