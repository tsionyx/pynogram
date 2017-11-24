#!/usr/bin/env python
# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from pyngrm.board import ConsoleBoard, StreamRenderer, CellState
from pyngrm.utils import use_test_instance, merge_dicts
from tests.test_board import ConsoleBoardTest


class GraphicalRenderer(StreamRenderer):
    ICONS = merge_dicts(StreamRenderer.ICONS, {
        CellState.UNSURE: ' ',
        CellState.THUMBNAIL: '\u25C8',
        CellState.BOX: '\u25A3',
        CellState.SPACE: '\u25A1',
    })


if __name__ == '__main__':
    test = use_test_instance(ConsoleBoardTest)
    b = test.board
    b2 = ConsoleBoard(test.board.rows, test.board.columns, renderer=GraphicalRenderer)
    b2.cells[2] = [CellState.SPACE] + [CellState.BOX] * 6 + [CellState.SPACE]
    b2.draw()
