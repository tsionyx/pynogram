#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
The program's entry point
"""

from __future__ import unicode_literals, print_function

import logging

from pyngrm.demo import demo_board


def main():
    """Traditional main function"""
    d_board = demo_board()
    d_board.solve()
    d_board.draw()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
