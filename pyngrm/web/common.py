# -*- coding: utf-8 -*
"""
Defines a board of nonogram game
"""

from __future__ import unicode_literals, print_function

import json
import logging
import os
import traceback
# noinspection PyCompatibility
from concurrent.futures import ThreadPoolExecutor

import tornado.web

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


class BaseHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        """Prevents warning 'must implement all abstract methods'"""
        pass

    def write_as_json(self, chunk, pretty=True):
        if isinstance(chunk, (dict, list, tuple)):
            indent = None if pretty is None else 2
            chunk = json.dumps(chunk, indent=indent,
                               sort_keys=True, ensure_ascii=False)
            if pretty is not None:
                chunk += '\n'

            self.set_header(str("Content-Type"), "application/json")

        return super(BaseHandler, self).write(chunk)

    def write_error(self, status_code, **kwargs):
        message = ''
        exc_info = kwargs.get("exc_info")
        if exc_info:
            exception = exc_info[1]
            if hasattr(exception, 'log_message'):
                message = exception.log_message
                if exception.args:
                    message = message % exception.args
            else:
                message = str(exception)

        error = dict(
            status="%d: %s" % (status_code, self._reason),
            message=message)
        if self.settings.get("serve_traceback") and exc_info:
            error["exc_info"] = ''.join(
                traceback.format_exception(*exc_info))

        if (status_code // 100) == 4:
            LOG.info("Client request problem")
        elif (status_code // 100) == 5:
            LOG.error("Server problem", exc_info=exc_info)

        self.set_header(str("Content-Type"), "application/json")
        self.write_as_json(dict(error=error))


# noinspection PyAbstractClass
class ThreadedHandler(tornado.web.RequestHandler):
    # noinspection SpellCheckingInspection
    """
    To make use of this class:
    1. subclass your handler. Place the ThreadedHandler first in case of multiple inheritance
       (see http://stackoverflow.com/a/20450978/ for details):
        `class TimeConsumedHandler(ThreadedHandler)`
    2. define methods handlers with decorator:
         `@tornado.gen.coroutine
          def get(self):`
    3. whenever your call the time consuming operation, do
        `res = yield self.executor.submit(my_heavy_routine, arg1, arg2, kwarg1=value1)`
    4. provide `max_workers` argument for initializing the thread pool while init your routes:
        `(r"/my-route/?", TimeConsumedHandler, dict(max_workers=10))`

    Based on https://gist.github.com/simplyvikram/6997323
    """

    def initialize(self, *args, **kwargs):
        super(ThreadedHandler, self).initialize()
        # noinspection PyAttributeOutsideInit
        self.executor = ThreadPoolExecutor(*args, **kwargs)  # pylint: disable=W0201


class ThreadedBaseHandler(ThreadedHandler, BaseHandler):
    def initialize(self, max_workers=10, **kwargs):
        super(ThreadedBaseHandler, self).initialize(max_workers=max_workers, **kwargs)


class LongPollNotifier(object):
    def __init__(self):
        self.callbacks = []

    def register(self, callback):
        self.callbacks.append(callback)

    def notify_callbacks(self, *args, **kwargs):
        for c in self.callbacks:
            self.callback_helper(c, *args, **kwargs)
        self.callbacks = []

    @classmethod
    def callback_helper(cls, callback, *args, **kwargs):
        LOG.debug(args)
        LOG.debug(kwargs)
        callback(*args, **kwargs)
