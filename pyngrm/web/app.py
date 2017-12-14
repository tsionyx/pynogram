# -*- coding: utf-8 -*
"""
Defines a board of nonogram game
"""

from __future__ import unicode_literals, print_function

import logging
import os
import socket
from io import StringIO

import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from pyngrm.demo import demo_board, demo_board2, more_complex_board
from pyngrm.renderer import StreamRenderer
from pyngrm.web.common import (
    BaseHandler,
    HelloHandler,
    ThreadedBaseHandler,
    LongPollNotifier,
)

# pylint: disable=arguments-differ

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

tornado.options.define("port", default=3145, help="run on the given port", type=int)
tornado.options.define("debug", default=False, help="debug mode", type=bool)


class BoardLiveHandler(ThreadedBaseHandler):
    """Actually renders a board to an HTML-page"""

    def get(self, _id):
        _id = int(_id)
        board_notifier = self.application.get_board_notifier(_id, create=True)

        self.render("index.html",
                    _id=_id,
                    board_image=board_notifier.get_board_image())

    @tornado.gen.coroutine
    def post(self, _id):
        rows_first = 'columns_first' not in self.request.arguments
        parallel = 'parallel' in self.request.arguments

        _id = int(_id)
        board_notifier = self.application.get_board_notifier(_id, create=True)

        if not board_notifier:
            raise tornado.web.HTTPError(404, 'Not found board %s', _id)

        LOG.info('Solving board #%s', _id)
        LOG.debug('Callbacks: %s', board_notifier.callbacks)

        yield self.executor.submit(board_notifier.board.solve,
                                   rows_first=rows_first,
                                   parallel=parallel)

        # force callbacks to execute
        board_notifier.board.solution_round_completed()


class BoardStatusHandler(BaseHandler):
    """
    Returns a status of a board given its ID.
    This handler uses long-polling technique to
    respond only when the status gets updated
    """

    @tornado.web.asynchronous
    def get(self, _id):
        _id = int(_id)

        board_notifier = self.application.get_board_notifier(_id)
        if not board_notifier:
            raise tornado.web.HTTPError(404, 'Not found board %s', _id)

        board_notifier.register(self.on_update)

        if board_notifier.board.solved:
            board_notifier.notify_callbacks(complete=True)

    def on_update(self, **kwargs):
        """
        Actually finish the request only when the status gets changed.
        """
        LOG.debug(list(kwargs.keys()))
        self.write_as_json(kwargs)
        self.finish()


class BoardUpdateNotifier(LongPollNotifier):
    """
    Stores info needed to correctly update board
    image when its status gets changed.
    """

    def __init__(self, _id, board):
        super(BoardUpdateNotifier, self).__init__()
        self._id = _id
        self.board = board
        if not isinstance(board.renderer, StreamRenderer):
            raise TypeError('Board renderer should be streamed')

        self.stream = None
        self.clear_stream()

        # subscribe on updates
        board.on_solution_round_complete = self.notify_callbacks
        board.on_row_update = self.notify_callbacks
        board.on_column_update = self.notify_callbacks

    def clear_stream(self):
        """
        Just reinitialize the stream

        https://stackoverflow.com/a/4330829
        """
        self.stream = StringIO()
        self.board.renderer.stream = self.stream

    def callback_helper(self, callback, *args, **kwargs):
        if args:
            LOG.warning("Some args: '%s' are ignored", args)
        params = dict(kwargs, board=self.get_board_image())
        LOG.debug(params)
        callback(**params)

    def get_board_image(self):
        """
        Return current image of a draw using board's renderer
        """
        self.board.draw()
        image = self.stream.getvalue()
        self.clear_stream()

        return image


class Application(tornado.web.Application):
    """
    Customized tornado application with
    the routes and settings defined.
    """

    def __init__(self, **kwargs):
        self.board_notifiers = dict()

        handlers = [
            (r"/board/([0-9]+)?", BoardLiveHandler),
            (r"/board/status/([0-9]+)?", BoardStatusHandler),
        ]
        # noinspection PyTypeChecker
        handlers += [('/', HelloHandler, {
            'name': 'Nonogram Solver', 'handlers': handlers})]

        settings = dict(
            kwargs,
            template_path=os.path.join(CURRENT_DIR, 'templates'),
            static_path=os.path.join(CURRENT_DIR, 'static')
        )
        super(Application, self).__init__(handlers, **settings)

    @classmethod
    def get_board(cls, _id, **board_params):
        """
        Generates a board using given ID.

        This can be a function that extracts a board
        from a database for example. By now it just returns
        one of hardcoded demo boards.
        """
        remainder = _id % 3
        board_factory = [demo_board, demo_board2, more_complex_board][remainder]
        return board_factory(**board_params)

    def get_board_notifier(self, _id, create=False):
        """
        Get the notifier wrapper around the board
        and optionally creates it.
        """
        board_notifier = self.board_notifiers.get(_id)

        if not board_notifier and create:
            board_notifier = BoardUpdateNotifier(_id, self.get_board(_id))
            self.board_notifiers[_id] = board_notifier

        return board_notifier


def main(port, debug=False):
    """
    Starts the tornado application on a given port
    """
    app = Application(debug=debug)

    try:
        host = socket.gethostbyname(socket.gethostname())
        full_address = "http://{}:{}".format(host, port)

        if debug:
            app.listen(port)
            LOG.info("Server started on %s", full_address)
            tornado.ioloop.IOLoop.instance().start()
        else:
            server = tornado.httpserver.HTTPServer(app)
            server.bind(port)
            LOG.info("Server started on %s", full_address)
            server.start(0)

            # if you want to setup some DB connections
            # do it now right after the fork
            # to avoid shared DB connections

            tornado.ioloop.IOLoop.current().start()
    except (KeyboardInterrupt, SystemExit):
        LOG.warning("Exit...")


if __name__ == '__main__':
    tornado.options.parse_command_line()
    PORT, DEBUG = tornado.options.options.port, tornado.options.options.debug
    if not DEBUG:
        # FIXME
        LOG.warning('Only debug mode supported for now. Switching.')
        DEBUG = True

    main(port=PORT, debug=DEBUG)
