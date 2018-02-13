# -*- coding: utf-8 -*-
"""
Here lie the utilities methods that does not depend on any domain
e.g. manipulations with collections or streams.
"""

from __future__ import unicode_literals, print_function, division

import multiprocessing
import os
import sys
from contextlib import contextmanager
from datetime import datetime

from six import text_type

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
START_TIME = datetime.now()


def get_uptime():  # pragma: no cover
    """Return the time program run in human-readable form"""
    return text_type(datetime.now() - START_TIME)


def get_version():
    """Return the program's version from the package root"""

    root_dir = os.path.dirname(CURRENT_DIR)

    if root_dir not in sys.path:
        sys.path.append(root_dir)
        remove = True
    else:
        remove = False

    try:
        from __version__ import VERSION
    except ImportError:  # pragma: no cover
        # noinspection PyPep8Naming
        VERSION = ()

    if remove:
        sys.path.remove(root_dir)

    return VERSION


@contextmanager
def terminating_mp_pool(*args, **kwargs):  # pragma: no cover
    """
    Allows to use multiprocessing.Pool as a contextmanager in both PY2 and PY3

    https://stackoverflow.com/a/25968716
    """
    pool = multiprocessing.Pool(*args, **kwargs)
    try:
        yield pool
    finally:
        pool.terminate()


def is_close(a, b, rel_tol=1e-09, abs_tol=0.0):  # pylint: disable=invalid-name
    """
    Almost equality for float numbers

    :param a: first number
    :param b: second number

    :param rel_tol: relative tolerance, it is multiplied
    by the greater of the magnitudes of the two arguments;
    as the values get larger, so does the allowed difference
    between them while still considering them equal.
    :param abs_tol: absolute tolerance that is applied as-is in all cases.

    If the difference is less than either of those tolerances,
    the values are considered equal.

    Source: https://stackoverflow.com/a/33024979
    """
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
