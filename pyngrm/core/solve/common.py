# -*- coding: utf-8 -*
"""Define common solving utilities"""

from __future__ import unicode_literals, print_function


class NonogramError(ValueError):
    """
    Represents an error occurred when trying
    to solve a nonogram which has an internal contradiction.
    """
    pass
