# -*- coding: utf-8 -*-
"""
Defines web routes and tornado application
to visualize nonogram solutions
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

from pynogram.core.board import make_board
from pynogram.core.solver.contradiction import Solver
from pynogram.reader import (
    read_example, list_examples, read_example_source,
    Pbn, PbnNotFoundError,
)
from pynogram.renderer import (
    StreamRenderer,
    RENDERERS,
)
from .common import (
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


class BoardHandler(ThreadedBaseHandler):
    """Actually renders a board to an HTML-page"""

    @property
    def board_mode(self):
        """The sting that identifies board's source (local, pbn)"""
        raise NotImplementedError()

    @property
    def renderer(self):
        """Get the renderer class based on user choice (?render=MODE)"""

        rend_mode = self.get_argument('render', 'svg')
        res = RENDERERS.get(rend_mode)
        if not res:
            raise tornado.web.HTTPError(404, 'Not found renderer: %s', rend_mode)

        return res

    def get(self, _id):
        board_notifier = self.application.get_board_notifier(
            _id, self.board_mode, create=True, renderer=self.renderer)

        self.render('index.html',
                    board_mode=self.board_mode,
                    board_id=_id,
                    board_image=board_notifier.get_board_image())

    @tornado.gen.coroutine
    def post(self, _id):
        board_notifier = self.application.get_board_notifier(
            _id, self.board_mode, create=True, renderer=self.renderer)

        if not board_notifier:
            raise tornado.web.HTTPError(404, 'Not found board %s', _id)

        LOG.info('Solving board #%s', _id)
        LOG.debug('Callbacks: %s', board_notifier.callbacks)

        solver = Solver(board_notifier.board)
        yield self.executor.submit(solver.solve)

        # force callbacks to execute
        board_notifier.board.solution_round_completed()


class BoardLocalHandler(BoardHandler):
    """Renders local boards (bundled in distribution)"""

    @property
    def board_mode(self):
        return 'local'


class ListLocalHandler(BaseHandler):
    """Show the list of local puzzles"""

    def get(self):
        self.render('local.html', files=list_examples())


class BoardLocalSourceHandler(BaseHandler):
    """Show the source text of a local puzzle"""

    def get(self, _id):
        self.set_header(str('Content-Type'), 'text/plain')
        try:
            self.write(read_example_source(_id))
        except IOError:
            raise tornado.web.HTTPError(
                404, 'File not found: %s', _id)


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

        if board_notifier.board.is_finished:
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

    def update_renderer(self, **renderer_params):
        """Update the render method for given board"""

        if 'stream' not in renderer_params:
            self.stream = StringIO()
            renderer_params['stream'] = self.stream
        self.board.set_renderer(**renderer_params)

    def clear_stream(self):
        """
        Just reinitialize the stream

        https://stackoverflow.com/a/4330829
        """
        self.board.renderer.stream = StringIO()
        self.stream = self.board.renderer.stream

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
            (r'/board/local/', ListLocalHandler),
            (r'/board/local/source/(.+)/?', BoardLocalSourceHandler),
            (r'/board/local/(.+)/?', BoardLocalHandler),
            (r'/board/pbn/([0-9]+)/?', BoardPbnHandler),
            (r'/board/status/(.+)/(.+)/?', BoardStatusHandler),
        ]
        # noinspection PyTypeChecker
        handlers += [('/', HelloHandler, {
            'name': 'Nonogram Solver', 'handlers': handlers})]

        settings = dict(
            kwargs,
            compress_response=True,
            template_path=os.path.join(CURRENT_DIR, 'templates'),
            static_path=os.path.join(CURRENT_DIR, 'static')
        )
        super(Application, self).__init__(handlers, **settings)

    @classmethod
    def get_board(cls, _id, create_mode, **renderer_params):
        """Generates a board using given ID and mode"""
        if create_mode == 'local':
            board_def = read_example(_id)
        elif create_mode == 'pbn':
            board_def = Pbn.read(_id)
        else:
            raise tornado.web.HTTPError(400, 'Bad mode: %s', create_mode)

        return make_board(*board_def, **renderer_params)

    def get_board_notifier(self, _id, mode, create=False, **renderer_params):
        """
        Get the notifier wrapper around the board
        and optionally creates it.
        """
        board_notifier = self.board_notifiers.get((_id, mode))

        if not board_notifier and create:
            try:
                board = self.get_board(_id, mode, **renderer_params)
                board_notifier = BoardUpdateNotifier(_id, board)
            except IOError:
                raise tornado.web.HTTPError(
                    404, 'File not found: %s', _id)
            except PbnNotFoundError:
                raise tornado.web.HTTPError(
                    404, "Webpbn's puzzle not found: %s", _id)

            self.board_notifiers[(_id, mode)] = board_notifier

        else:
            # do not change the renderer if not said to
            if renderer_params:
                board_notifier.update_renderer(**renderer_params)

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
