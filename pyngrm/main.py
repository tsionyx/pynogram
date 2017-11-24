#!/usr/bin/env python
# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from pyngrm.utils import use_test_instance
from tests.test_board import ConsoleBoardTest

if __name__ == '__main__':
    print("Work in progress")
    test = use_test_instance(ConsoleBoardTest)
    b = test.board
    print(b.rows)

    b.draw()
    print(test.stream.getvalue())
