# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function


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
