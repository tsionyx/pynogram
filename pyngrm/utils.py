# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import sys


def merge_dicts(*dict_args, **kwargs):
    """
    Thanks Aaron Hall http://stackoverflow.com/a/26853961/
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    _type = kwargs.get('type', dict)
    # noinspection PyCallingNonCallable
    result = _type()
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def pad_list(l, n, x, left=True):
    if len(l) >= n:
        return l

    padding = [x] * (n - len(l))
    return padding + list(l) if left else list(l) + padding


def interleave(a, b):
    """
    >>> interleave([0, 2, 4, 6], [1, 3, 5])
    [0, 1, 2, 3, 4, 5, 6]

    https://stackoverflow.com/a/7947461
    """
    la, lb = len(a), len(b)
    if la - lb not in (0, 1):
        raise ValueError("The lists' sizes are too different: ({}, {})"
                         .format(la, lb))
    res = [None] * (la + lb)
    res[::2] = a
    res[1::2] = b
    return res


def max_safe(*args, **kwargs):
    """
    Returns max element of an iterable.

    Adds a `default` keyword for any version of python that do not support it
    """
    if sys.version_info < (3, 4):  # `default` supported since 3.4
        if len(args) == 1:
            arg = args[0]
            if 'default' in kwargs:
                default = kwargs.pop('default')
                if not arg:
                    return default

                # https://stackoverflow.com/questions/36157995#comment59954203_36158079
                arg = list(arg)
                if not arg:
                    return default

                # if the `arg` was an iterator, it's exhausted already
                # so use a new list instead
                return max(arg, **kwargs)

    return max(*args, **kwargs)
