# -*- coding: utf-8 -*-
"""
Here lie the utilities methods that does not depend on any domain
e.g. manipulations with collections or streams.
"""

from __future__ import unicode_literals, print_function, division

import logging
import multiprocessing
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from threading import Lock

from memoized import memoized
from six import (
    text_type,
    iteritems,
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
START_TIME = datetime.now()


def get_uptime():  # pragma: no cover
    """Return the time program run in human-readable form"""
    return text_type(datetime.now() - START_TIME)


_IMPORT_LOCK = Lock()


@contextmanager
def extend_import_path(dir_name, first=False):
    """
    Temporarily add the `dir_name` to the sys.path
    If `first` flag provided, the directory will be added
    at the very beginning to override any other imported resources.
    """

    if dir_name not in sys.path:
        with _IMPORT_LOCK:  # prevent from doing path manipulations concurrently
            if first:
                sys.path.insert(0, dir_name)
            else:
                sys.path.append(dir_name)

            logging.info('The %r added to the sys.path', dir_name)

            try:
                yield
            finally:
                if first:
                    removed_path = sys.path.pop(0)
                else:
                    removed_path = sys.path.pop()

                logging.info('The %r removed from the sys.path', removed_path)
                assert dir_name == removed_path


def get_version():
    """Return the program's version from the package root"""

    root_dir = os.path.dirname(CURRENT_DIR)

    with extend_import_path(root_dir, first=True):
        try:
            from __version__ import VERSION
        except ImportError:  # pragma: no cover
            # noinspection PyPep8Naming
            VERSION = ()

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


def is_close(first, second, rel_tol=1e-09, abs_tol=0.0):
    """
    Almost equality for float numbers

    :param first
    :param second

    :param rel_tol: relative tolerance, it is multiplied
    by the greater of the magnitudes of the two arguments;
    as the values get larger, so does the allowed difference
    between them while still considering them equal.
    :param abs_tol: absolute tolerance that is applied as-is in all cases.

    If the difference is less than either of those tolerances,
    the values are considered equal.

    Source: https://stackoverflow.com/a/33024979
    """
    return abs(first - second) <= max(rel_tol * max(abs(first), abs(second)), abs_tol)


def log_call(log_func=print):  # pragma: no cover
    """Print every function call along with its arguments"""

    def _decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__

            msg = 'Calling function {}('.format(func_name)
            _args = args
            if _args:
                _self = _args[0]
                if isinstance(_self, object) and hasattr(_self, func_name):
                    _args = args[1:]

            msg += ', '.join(map(str, _args))
            msg += ', '.join('{}={}'.format(k, v) for k, v in iteritems(kwargs))

            msg += ')'

            # start_time = time.time()
            result = func(*args, **kwargs)
            msg += ' --> {}'.format(result)
            log_func(msg)

            return result

        return wrapper

    return _decorator


@memoized
def two_powers(num):
    """
    Get a 'factorization' of number into powers of 2:

    42 --> [2, 8, 32]
    """

    # https://stackoverflow.com/a/51786889/1177288
    # return tuple(1 << i for i, d in enumerate(reversed(bin(num)[2:])) if d == '1')
    return tuple(_two_powers(num))


def _two_powers(num):
    """
    https://stackoverflow.com/a/51859187/1177288
    """
    while num > 0:
        rest = num & (num - 1)
        yield num - rest
        num = rest


def from_two_powers(numbers):
    """
    Construct a number from the powers of 2
    """

    # TODO: consider a simple sum() here
    result = 0
    for num in numbers:
        result |= num

    return result


def get_named_logger(name__, file__, auto_config_when_main=True):
    """
    Choose the best name for logger based on how the file is called.
    When the file is run with interpreter like `python foo.py`,
    the logger will be named 'foo.py'.
    When the file imported by another module,
    the logger will be named 'parent_module.foo'.

    You should always call it with the __name__ and __file__ arguments.
    """
    if name__ == '__main__':  # pragma: no cover
        name__ = os.path.basename(file__)
        if auto_config_when_main:
            logging.basicConfig()

    return logging.getLogger(name__)
