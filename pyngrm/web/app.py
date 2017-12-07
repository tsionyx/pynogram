# -*- coding: utf-8 -*
"""
Defines a board of nonogram game
"""

from __future__ import unicode_literals, print_function

import logging
import os
from io import StringIO

import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web

from pyngrm.demo import demo_board, demo_board2, more_complex_board
from pyngrm.renderer import StreamRenderer
from pyngrm.web.common import BaseHandler, LongPollNotifier, ThreadedBaseHandler

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class BoardLiveHandler(ThreadedBaseHandler):
    @classmethod
    def get_board(cls, _id, **board_params):
        remainder = _id % 3
        board_factory = [demo_board, demo_board2, more_complex_board][remainder]
        return board_factory(**board_params)

    def get(self, _id):
        _id = int(_id)

        board_notifier = self.application.board_notifiers.get(_id)

        if not board_notifier:
            board_notifier = BoardUpdateNotifier(_id, self.get_board(_id))
            self.application.board_notifiers[_id] = board_notifier

        self.render("index.html",
                    _id=_id,
                    board_image=board_notifier.get_board_image())

    @tornado.gen.coroutine
    def post(self, _id):
        _id = int(_id)

        board_notifier = self.application.board_notifiers.get(_id)

        if not board_notifier:
            raise tornado.web.HTTPError(404, 'Not found board %s', _id)

        LOG.info('Solving board #%s', _id)
        LOG.debug('Callbacks: %s', board_notifier.callbacks)

        yield self.executor.submit(board_notifier.board.solve)

        # force callbacks to execute
        board_notifier.board.solution_round_completed()


class BoardStatusHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self, _id):
        _id = int(_id)

        board_notifier = self.application.board_notifiers.get(_id)
        if not board_notifier:
            raise tornado.web.HTTPError(404, 'Not found board %s', _id)

        board_notifier.register(self.on_update)

        if board_notifier.board.solved:
            board_notifier.notify_callbacks(complete=True)

    def on_update(self, **kwargs):
        LOG.debug(list(kwargs.keys()))
        self.write_as_json(kwargs)
        self.finish()


class BoardUpdateNotifier(LongPollNotifier):
    def __init__(self, _id, board):
        super(BoardUpdateNotifier, self).__init__()
        self._id = _id
        self.board = board
        if not isinstance(board.renderer, StreamRenderer):
            raise TypeError('Board renderer should be streamed')

        self.stream = None
        self.clear_stream()

        # subscribe on updates
        # TODO: make it work!
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
        self.board.draw()
        image = self.stream.getvalue()
        self.clear_stream()

        return image


class Application(tornado.web.Application):
    def __init__(self, **kwargs):
        self.board_notifiers = dict()
        handlers = [
            (r"/board/([0-9]+)?", BoardLiveHandler),
            (r"/board/status/([0-9]+)?", BoardStatusHandler),
        ]

        # TODO: do we need that?
        settings = dict(
            kwargs,
            template_path=os.path.join(CURRENT_DIR, 'templates'),
            static_path=os.path.join(CURRENT_DIR, 'static')
        )
        super(Application, self).__init__(handlers, **settings)


def main(port, debug=False):
    app = Application(debug=debug)

    try:
        if debug:
            app.listen(port)
            # init_app()
            LOG.info("Listening on %s port...", port)
            tornado.ioloop.IOLoop.instance().start()
        else:
            server = tornado.httpserver.HTTPServer(app)
            server.bind(port)
            LOG.info("Listening on %s port...", port)
            server.start(0)
            # init after the fork to avoid shared DB connections
            # init_app()
            tornado.ioloop.IOLoop.current().start()
    except (KeyboardInterrupt, SystemExit):
        LOG.warning("Exit...")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main(3145, debug=True)
