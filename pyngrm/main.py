#!/usr/bin/env python
# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from pyngrm.board import ConsoleBoard
from pyngrm.renderer import StreamRenderer, CellState, AsciiRenderer
from pyngrm.utils import merge_dicts
from tests.test_board import tested_board


class GraphicalRenderer(StreamRenderer):
    ICONS = merge_dicts(StreamRenderer.ICONS, {
        CellState.UNSURE: ' ',
        CellState.THUMBNAIL: '\u2B50',
        CellState.BOX: '\u2B1B',
        CellState.SPACE: '\u2022',
    })


if __name__ == '__main__':
    b = tested_board(ConsoleBoard, renderer=AsciiRenderer)
    b.cells[2] = [CellState.SPACE] + [CellState.BOX] * 6 + [CellState.SPACE]
    b.draw()
