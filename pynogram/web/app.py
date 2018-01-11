# -*- coding: utf-8 -*
"""
Defines web routes and tornado application
to demonstrate nonogram solutions
"""

from __future__ import unicode_literals, print_function

import logging
import os
import socket
from io import StringIO

import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web

import pynogram.core.solver.contradiction as contradiction_solver
from pynogram.core.board import make_board
from pynogram.reader import read_example, Pbn, PbnNotFoundError
from pynogram.renderer import (
    StreamRenderer,
    BaseAsciiRenderer,
    SvgRenderer,
)
from .common import (
    BaseHandler,
    HelloHandler,
    ThreadedBaseHandler,
    LongPollNotifier,
)
from .demo import local_boards

# pylint: disable=arguments-differ

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class BoardHandler(ThreadedBaseHandler):
    """Actually renders a board to an HTML-page"""

    @property
    def board_mode(self):
        """The sting that identifies board's source (demo, local, pbn)"""
        raise NotImplementedError()

    def get(self, _id):
        board_notifier = self.application.get_board_notifier(_id, self.board_mode)

        self.render('index.html',
                    board_mode=self.board_mode,
                    board_id=_id,
                    board_image=board_notifier.get_board_image())

    @tornado.gen.coroutine
    def post(self, _id):
        rows_first = 'columns_first' not in self.request.arguments
        # parallel = 'parallel' in self.request.arguments

        board_notifier = self.application.get_board_notifier(_id, self.board_mode)

        if not board_notifier:
            raise tornado.web.HTTPError(404, 'Not found board %s', _id)

        LOG.info('Solving board #%s', _id)
        LOG.debug('Callbacks: %s', board_notifier.callbacks)

        yield self.executor.submit(contradiction_solver.solve,
                                   board_notifier.board,
                                   by_rows=rows_first)

        # force callbacks to execute
        board_notifier.board.solution_round_completed()


class BoardDemoHandler(BoardHandler):
    """Renders demonstration boards"""

    @property
    def board_mode(self):
        return 'demo'


class BoardLocalHandler(BoardHandler):
    """Renders local boards (bundled in distribution)"""

    @property
    def board_mode(self):
        return 'local'


class BoardPbnHandler(BoardHandler):
    """Renders webpbn.com boards"""

    @property
    def board_mode(self):
        return 'pbn'


class BoardStatusHandler(BaseHandler):
    """
    Returns a status of a board given its ID.
    This handler uses long-polling technique to
    respond only when the status gets updated
    """

    @tornado.web.asynchronous
    def get(self, mode, _id):
        board_notifier = self.application.get_board_notifier(_id, mode)
        if not board_notifier:
            raise tornado.web.HTTPError(404, 'Not found board %s', (_id, mode))

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
            (r'/demo/([0-9]+)/?', BoardDemoHandler),
            (r'/board/local/(.+)/?', BoardLocalHandler),
            (r'/board/pbn/([0-9]+)/?', BoardPbnHandler),
            (r'/board/status/(.+)/(.+)/?', BoardStatusHandler),
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
    def get_board(cls, _id, create_mode, **board_params):
        """
        Generates a board using given ID.

        This can be a function that extracts a board
        from a database for example. By now it just returns
        one of hardcoded demo boards.
        """

        if create_mode == 'demo':
            _id = int(_id)
            predefined = local_boards()
            board_factory = predefined[_id % len(predefined)]
            return board_factory(**board_params)

        elif create_mode == 'local':
            board_def = read_example(_id)
            return make_board(*board_def, renderer=BaseAsciiRenderer)

        elif create_mode == 'pbn':
            board_def = Pbn.read(_id)
            return make_board(*board_def, renderer=SvgRenderer, **board_params)

        raise tornado.web.HTTPError(400, 'Bad mode: %s', create_mode)

    def get_board_notifier(self, _id, create_mode):
        """
        Get the notifier wrapper around the board
        and optionally creates it.
        """
        board_notifier = self.board_notifiers.get((_id, create_mode))

        if not board_notifier and create_mode:
            try:
                board_notifier = BoardUpdateNotifier(_id, self.get_board(_id, create_mode))
            except IOError:
                raise tornado.web.HTTPError(
                    404, 'File not found: %s', _id)
            except PbnNotFoundError:
                raise tornado.web.HTTPError(
                    404, "Webpbn's puzzle not found: %s", _id)

            self.board_notifiers[(_id, create_mode)] = board_notifier

        return board_notifier


def run(port, debug=False):
    """
    Starts the tornado application on a given port
    """
    app = Application(debug=debug)

    try:
        host = socket.gethostbyname(socket.gethostname())
        full_address = 'http://{}:{}'.format(host, port)

        if debug:
            app.listen(port)
            LOG.info('Server started on %s', full_address)
            tornado.ioloop.IOLoop.instance().start()
        else:
            server = tornado.httpserver.HTTPServer(app)
            server.bind(port)
            LOG.info('Server started on %s', full_address)
            server.start(0)

            # if you want to setup some DB connections
            # do it now right after the fork
            # to avoid shared DB connections

            tornado.ioloop.IOLoop.current().start()
    except (KeyboardInterrupt, SystemExit):
        LOG.warning('Exit...')
