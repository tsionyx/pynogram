# -*- coding: utf-8 -*-
"""
Enables general-purpose cache
"""

from __future__ import unicode_literals, print_function

import logging
import os
from time import time

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


class Cache(object):
    """
    Presents the simple dictionary
    with size limit and hit counter.
    Also limited support for expiration is available.
    """

    # TODO: make thread to expire objects

    def __init__(self, max_size=10 ** 5, increase=False, do_not_increase_after=10 ** 6):
        """
        :param max_size: maximum number of items that the cache can store
        :param increase: whether to increase the size dynamically when reached the max.
        If you specify the True, the size will simply doubled. If you specify a number,
        the size will be multiplied by that amount.
        :param do_not_increase_after: prevent the cache from growing
        at certain number of items
        """
        self._storage = dict()
        self.init_size = max_size
        self.max_size = max_size
        self.hits = 0
        self.total_queries = 0

        if increase is True:
            increase = 2
        self.increase = increase
        self.do_not_increase_after = do_not_increase_after

    def save(self, name, value, _time=None):
        """
        Write the value to cache.
        Optionally you can specify an expiration timeout.
        """
        if len(self._storage) >= self.max_size:
            LOG.warning('Maximum size for cache reached (%s).', self.max_size)

            self._storage.clear()
            self._increase_size()

        self._storage[name] = (time(), _time, value)

    def get(self, name):
        """
        Gets the value from a cache.

        Expire the key if its time is over.
        """
        self.total_queries += 1
        item = self._storage.get(name)

        if item is None:
            return None
        else:
            self.hits += 1
            start, _time, value = item
            # expires
            if _time is not None and time() - start > _time:
                self.delete(name)

            return value

    def _increase_size(self):
        if self.max_size >= self.do_not_increase_after:
            return

        if self.increase and self.increase > 1:
            new_max = self.max_size * self.increase
            self.max_size = min(new_max, self.do_not_increase_after)
        else:
            LOG.info('Bad increase multiplier: %s', self.increase)

    def delete(self, name):
        """Just drop the value from a cache"""
        return bool(self._storage.pop(name, False))

    @property
    def hit_rate(self):
        """How much queries successfully reached the cache"""
        if not self.total_queries:
            return 0

        return float(self.hits) / self.total_queries
