# -*- coding: utf-8 -*-
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

# import raven
import tornado.web

from pynogram.utils.other import get_uptime, get_version

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)
SENTRY_DSN = 'https://user:password@sentry.io/project-id'


class BaseHandler(tornado.web.RequestHandler):
    """
    Defines RequestHandler with a couple of useful methods
    """

    def data_received(self, chunk):
        """Prevents warning 'must implement all abstract methods'"""
        pass

    def write_as_json(self, chunk, pretty=True):
        """
        Respond by JSON-ify given object
        """
        if isinstance(chunk, (dict, list, tuple)):
            indent = None if pretty is None else 2
            chunk = json.dumps(chunk, indent=indent,
                               sort_keys=True, ensure_ascii=False)
            if pretty is not None:
                chunk += '\n'

            self.set_header(str("Content-Type"), "application/json")

        return super(BaseHandler, self).write(chunk)

    # _raven_client = None
    #
    # @classmethod
    # def raven_client(cls):
    #     if cls._raven_client is None:
    #         cls._raven_client = raven.Client(SENTRY_DSN)
    #     return cls._raven_client

    def write_error(self, status_code, **kwargs):
        """
        Respond with JSON-formatted error instead of standard one
        """
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
            # if exc_info:
            #     self.raven_client().captureException(exc_info)
            LOG.error("Server problem", exc_info=exc_info)

        self.set_header(str("Content-Type"), "application/json")
        self.write_as_json(dict(error=error))


# noinspection PyAbstractClass
# pylint: disable=abstract-method
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

    # pylint: disable=arguments-differ
    def initialize(self, *args, **kwargs):
        super(ThreadedHandler, self).initialize()
        # noinspection PyAttributeOutsideInit
        self.executor = ThreadPoolExecutor(*args, **kwargs)


class ThreadedBaseHandler(ThreadedHandler, BaseHandler):
    """
    Mix the ability to thread your CPU-intensive tasks
    with the utility methods.
    """

    # pylint: disable=arguments-differ
    def initialize(self, max_workers=10, **kwargs):
        super(ThreadedBaseHandler, self).initialize(max_workers=max_workers, **kwargs)


class HelloHandler(BaseHandler):
    """
    Show application routes and methods in JSON form
    """

    # noinspection PyMethodOverriding
    # pylint: disable=arguments-differ
    def initialize(self, name, handlers, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.name = name
        # noinspection PyAttributeOutsideInit
        self.routes = self._process_handlers(handlers)
        # noinspection PyArgumentList
        super(HelloHandler, self).initialize(**kwargs)

    METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS')

    @classmethod
    def _process_handlers(cls, handlers):
        routes = []
        for handler_pair in handlers:
            route, handler = handler_pair[:2]
            methods = [m for m in cls.METHODS if m.lower() in handler.__dict__]
            route_desc = "{}: {}".format(route, ', '.join(methods))
            if issubclass(handler, ThreadedHandler):
                route_desc += "(threaded)"
            routes.append(route_desc)
        return routes

    def get(self):
        res = dict(
            greeting="This is the start page of a '%s' service" % self.name,
            uptime=get_uptime(),
            version='.'.join(map(str, get_version())),
            paths=self.routes)

        self.write_as_json(res)


class LongPollNotifier(object):
    """
    Defines helper class to use when implementing
    long-polling behaviour.

    You should simply call `register(callback)`
    in your request method (always make it `@tornado.web.asynchronous`
    to prevent finishing request when method ends).
    """

    def __init__(self):
        self.callbacks = []

    def register(self, callback):
        """
        Registers the function to call when the
        `notify_callbacks` will be fired.
        """
        self.callbacks.append(callback)

    def notify_callbacks(self, *args, **kwargs):
        """
        Run the callbacks previously collected.
        In case of long-polling the callback should call
        `finish()` on `tornado.web.RequestHandler` instance
        to send the answer to the client.
        """
        for callback in self.callbacks:
            self.callback_helper(callback, *args, **kwargs)
        self.callbacks = []

    # pylint: disable=no-self-use
    def callback_helper(self, callback, *args, **kwargs):
        """
        Simply call the callback with the parameters provided.

        You should override this to pass additional arguments.
        """

        LOG.debug(args)
        LOG.debug(kwargs)
        callback(*args, **kwargs)
