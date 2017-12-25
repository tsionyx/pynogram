# -*- coding: utf-8 -*
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

    def __init__(self, max_size=10 ** 5):
        self._storage = dict()
        self.max_size = max_size
        self.hits = 0
        self.total_queries = 0

    def save(self, name, value, _time=None):
        """
        Write the value to cache.
        Optionally you can specify an expiration timeout.
        """
        if len(self._storage) >= self.max_size:
            LOG.warning('Maximum size for cache reached (%s).', self.max_size)

            self._storage.clear()

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

    def delete(self, name):
        """Just drop the value from a cache"""
        return bool(self._storage.pop(name, False))

    @property
    def hit_rate(self):
        """How much queries successfully reached the cache"""
        if not self.total_queries:
            return 0

        return float(self.hits) / self.total_queries
