# -*- coding: utf-8 -*-
"""
Demos and examples
"""

from __future__ import unicode_literals, print_function

from pynogram.core.board import make_board
from pynogram.core.common import BOX, SPACE
from pynogram.reader import read_example
from pynogram.renderer import (
    AsciiRenderer,
    AsciiRendererWithBold,
    SvgRenderer,
)


def _example_board(file_name, renderer, **kwargs):
    board_def = read_example(file_name)

    return make_board(*board_def, renderer=renderer, **kwargs)


def w_board(**kwargs):
    """
    The demonstration 'W' letter board with customized cells icons
    source: https://en.wikipedia.org/wiki/Nonogram#/media/File:Nonogram.svg
    """
    renderer = AsciiRendererWithBold()
    renderer.icons.update({BOX: '\u2B1B', SPACE: '\u2022'})

    return _example_board('w', renderer, **kwargs)


def einstein_board(**kwargs):
    """Einstein's tongue"""
    return _example_board('einstein', SvgRenderer, **kwargs)


def mlp_board(**kwargs):
    """Friendship and Magic"""
    renderer = AsciiRenderer()
    renderer.icons[BOX] = '\u2B1B'

    return _example_board('MLP', renderer, **kwargs)


def local_boards():
    """Examples of local boards with various renderers"""
    return [w_board, einstein_board, mlp_board]
