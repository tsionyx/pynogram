# -*- coding: utf-8 -*
"""Define nonogram solving operations"""

from __future__ import unicode_literals, print_function

import logging

from pyngrm.core.solve.common import NonogramError
from pyngrm.core.solve.machine import NonogramFSM, LOG as MACHINE_LOGGER

MACHINE_LOGGER.setLevel(logging.WARNING)


def _solver(name):
    if name in ('partial_match', 'reverse_tracking'):
        def _solve(row_desc, row):
            nfsm = NonogramFSM.from_description(row_desc)

            method_func = getattr(nfsm, 'solve_with_' + name)
            return method_func(row)

        return _solve

    raise AttributeError("Cannot find solving method '%s'" % name)


def solve_line(*args, **kwargs):
    """
    Utility for row solving that can be used in multiprocessing map
    """
    method = kwargs.pop('method', 'reverse_tracking')

    if len(args) == 1:
        # mp's map supports only one iterable, so this weird syntax
        args = args[0]

    row_desc, row = args

    return _solver(method)(row_desc, row)


def assert_match(row_desc, row):
    """
    Verifies that the given row matches the description
    """
    nfsm = NonogramFSM.from_description(row_desc)
    if not nfsm.match(row):
        raise NonogramError("The row '{}' cannot fit".format(row))
