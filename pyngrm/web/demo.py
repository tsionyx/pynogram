# -*- coding: utf-8 -*
"""
Demos and examples
"""

from __future__ import unicode_literals, print_function

from pyngrm.core import BOX, SPACE
from pyngrm.core.board import Board
from pyngrm.input.reader import examples_file, read
from pyngrm.renderer import (
    AsciiRenderer,
    AsciiRendererWithBold,
)


def _example_board(file_name, renderer, **kwargs):
    with open(examples_file(file_name)) as _file:
        columns, rows = read(_file)

    return Board(columns, rows, renderer=renderer, **kwargs)


def w_board(**kwargs):
    """
    The demonstration board with the 'W' letter
    source: https://en.wikipedia.org/wiki/Nonogram#/media/File:Nonogram.svg
    """
    return _example_board('w', AsciiRendererWithBold, **kwargs)


def p_board(**kwargs):
    """
    Very simple demonstration 'P' letter board with customized cells icons
    source: https://en.wikipedia.org/wiki/Nonogram#Example
    """
    renderer = AsciiRendererWithBold()
    renderer.icons.update({BOX: '\u2B1B', SPACE: '\u2022'})

    return _example_board('p', renderer, **kwargs)


def mlp_board(**kwargs):
    """Friendship and Magic"""
    renderer = AsciiRenderer()
    renderer.icons[BOX] = '\u2B1B'

    return _example_board('MLP', renderer, **kwargs)
