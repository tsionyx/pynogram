# -*- coding: utf-8 -*
"""
Here lie the utilities methods that does not depend on any domain
e.g. manipulations with collections or streams.
"""

from __future__ import unicode_literals, print_function, division

import multiprocessing
import sys
from contextlib import contextmanager
from datetime import datetime
from heapq import heapify, heappush, heappop
from itertools import islice

from six import iteritems, text_type


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


def pad(coll, size, padding, left=True):
    """
    Pad the collection `coll` with `padding` items
    until it reaches the length of `size`.
    By default do padding in the beginning (on the left side).
    """
    padding_size = size - len(coll)
    if padding_size <= 0:
        return coll

    padding = [padding] * padding_size
    new_list = list(coll)
    return padding + new_list if left else new_list + padding


def interleave(list_a, list_b):
    """
    >>> interleave([0, 2, 4, 6], [1, 3, 5])
    [0, 1, 2, 3, 4, 5, 6]

    https://stackoverflow.com/a/7947461
    """
    size_a, size_b = len(list_a), len(list_b)
    if size_a - size_b not in (0, 1):
        raise ValueError("The lists' sizes are too different: ({}, {})"
                         .format(size_a, size_b))
    res = [None] * (size_a + size_b)
    res[::2] = list_a
    res[1::2] = list_b
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


def list_replace(a_list, x, y):  # pylint: disable=invalid-name
    """
    Replaces every `x` item in `a_list` with `y` item
    """
    for i, item in enumerate(a_list):
        if item == x:
            a_list[i] = y


def split_seq(iterable, size):
    """
    Split `iterable` into chunks with specified `size`
    # http://stackoverflow.com/a/312467/

    :param iterable: any iterable
    :param size: chunk size
    :return: chunks one by one
    """
    it = iter(iterable)  # pylint: disable=invalid-name
    item = list(islice(it, size))
    while item:
        yield item
        item = list(islice(it, size))


def avg(iterable):
    """
    Return the average value of an iterable of numbers
    """

    # the iterable can be an iterator that gets exhausted
    # while `sum` and `len` will return 0
    list_copy = list(iterable)
    if not list_copy:
        return None

    return sum(list_copy) / len(list_copy)


START_TIME = datetime.now()


def get_uptime():  # pragma: no cover
    """Return the time program run in human-readable form"""
    return text_type(datetime.now() - START_TIME)


@contextmanager
def terminating_mp_pool(*args, **kwargs):
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


# Based on Matteo Dell'Amico's solution
# https://gist.github.com/matteodellamico/4451520
class PriorityDict(dict):
    """
    Dictionary that can be used as a priority queue.

    Keys of the dictionary are items to be put into the queue, and values
    are their respective priorities. All dictionary methods work as expected.
    The advantage over a standard heapq-based priority queue is
    that priorities of items can be efficiently updated (amortized O(1))
    using code as 'the_dict[item] = new_priority.'

    The 'smallest' method can be used to return the object with lowest
    priority, and 'pop_smallest' also removes it.

    The 'sorted_iter' method provides a destructive sorted iterator.
    """

    def __init__(self, *args, **kwargs):
        super(PriorityDict, self).__init__(*args, **kwargs)
        self._rebuild_heap()

    def _rebuild_heap(self):
        self._heap = [(val, key) for key, val in iteritems(self)]
        heapify(self._heap)

    def smallest(self):
        """Return the item with the lowest priority.

        Raises IndexError if the object is empty.
        """

        heap = self._heap
        val, key = heap[0]
        while key not in self or self[key] != val:
            heappop(heap)
            val, key = heap[0]
        return key, val

    def pop_smallest(self):
        """Return the item with the lowest priority and remove it.

        Raises IndexError if the object is empty.
        """

        heap = self._heap
        val, key = heappop(heap)
        while key not in self or self[key] != val:
            val, key = heappop(heap)
        del self[key]
        return key, val

    def __setitem__(self, key, val):
        # We are not going to remove the previous value from the heap,
        # since this would have a cost O(n).

        super(PriorityDict, self).__setitem__(key, val)

        if len(self._heap) < 2 * len(self):
            heappush(self._heap, (val, key))
        else:
            # When the heap grows larger than 2 * len(self), we rebuild it
            # from scratch to avoid wasting too much memory.
            self._rebuild_heap()

    def setdefault(self, key, d=None):
        if key not in self:
            self[key] = d
            return d
        return self[key]

    def update(self, *args, **kwargs):
        # Reimplementing dict.update is tricky -- see e.g.
        # http://mail.python.org/pipermail/python-ideas/2007-May/000744.html
        # We just rebuild the heap from scratch after passing to super.

        super(PriorityDict, self).update(*args, **kwargs)
        self._rebuild_heap()

    def sorted_iter(self):
        """Sorted iterator of the priority dictionary items.

        Beware: this will destroy elements as they are returned.
        """

        while self:
            yield self.pop_smallest()
