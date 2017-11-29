# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import logging
import os

from six import string_types, integer_types

from pyngrm.renderer import (
    CellState,
    Renderer,
    StreamRenderer,
)

_log_name = __name__
if _log_name == '__main__':  # pragma: no cover
    _log_name = os.path.basename(__file__)

log = logging.getLogger(_log_name)


class BaseBoard(object):
    def __init__(self, columns, rows, renderer=Renderer):
        self.columns = self._normalize(columns)
        self.rows = self._normalize(rows)

        self.renderer = renderer
        if isinstance(self.renderer, type):
            self.renderer = self.renderer(self)
        elif isinstance(self.renderer, Renderer):
            self.renderer.init(self)
        else:
            raise TypeError('Bad renderer: %s' % renderer)

        self.cells = [[CellState.UNSURE] * self.width for _ in range(self.height)]
        self.validate()

    @classmethod
    def _normalize(cls, rows):
        res = []
        for r in rows:
            if not r:  # None, 0, '', [], ()
                r = ()
            elif isinstance(r, (tuple, list)):
                r = tuple(r)
            elif isinstance(r, integer_types):
                r = (r,)
            elif isinstance(r, string_types):
                r = tuple(map(int, r.split(' ')))
            else:
                raise ValueError('Bad row: %s' % r)
            res.append(r)
        return tuple(res)

    @property
    def height(self):
        return len(self.rows)

    @property
    def width(self):
        return len(self.columns)

    def validate(self):
        self.validate_headers(self.columns, self.height)
        self.validate_headers(self.rows, self.width)

        boxes_in_rows = sum(sum(block) for block in self.rows)
        boxes_in_columns = sum(sum(block) for block in self.columns)
        if boxes_in_rows != boxes_in_columns:
            raise ValueError('Number of boxes differs: {} (rows) and {} (columns)'.format(
                boxes_in_rows, boxes_in_columns))

    @classmethod
    def validate_headers(cls, rows, max_size):
        for row in rows:
            need_cells = sum(row)
            if row:
                # also need at least one space between every two blocks
                need_cells += len(row) - 1

            log.debug('Row: %s; Need: %s; Available: %s.',
                      row, need_cells, max_size)
            if need_cells > max_size:
                raise ValueError('Cannot allocate row {} in just {} cells'.format(
                    list(row), max_size))

    @property
    def full_size(self):
        return (
            self.headers_width + self.width,
            self.headers_height + self.height)

    def draw(self):
        self.renderer \
            .draw_header() \
            .draw_side() \
            .draw_grid() \
            .render()

    @property
    def headers_height(self):
        return max(map(len, self.columns))

    @property
    def headers_width(self):
        return max(map(len, self.rows))

    def __repr__(self):
        return '{}({}x{})'.format(self.__class__.__name__, self.height, self.width)


class ConsoleBoard(BaseBoard):
    def __init__(self, columns, rows, renderer=StreamRenderer):
        super(ConsoleBoard, self).__init__(
            columns, rows, renderer=renderer)


class GameBoard(BaseBoard):
    # TODO: http://programarcadegames.com/index.php?chapter=introduction_to_graphics
    pass
