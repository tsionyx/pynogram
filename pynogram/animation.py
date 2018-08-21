# -*- coding: utf-8 -*-
"""
Defines various renderers for the game of nonogram
"""

from __future__ import unicode_literals, print_function

import locale
import logging
import time

try:
    import curses
except ImportError:
    curses = None

from six import (
    string_types,
    itervalues,
)
from six.moves import queue

from pynogram.core.renderer import BaseAsciiRenderer

_LOG_NAME = __name__
LOG = logging.getLogger(_LOG_NAME)

# need for unicode support on PY2 (however pypy2 does not work)
# https://docs.python.org/2/library/curses.html
locale.setlocale(locale.LC_ALL, '')


class StringsPager(object):
    """
    Draws the strings on a curses window.
    The strings are come from the queue and draws on subsequent lines one after another.
    When the specified line (`restart_on`) appears in the queue,
    the drawing restarts from the very beginning.
    Also vertical scrolling is supported.

    Best suitable for fixed-size but constantly changed set of lines (like the gaming board).

    Inspired by https://gist.github.com/claymcleod/b670285f334acd56ad1c
    """

    def __init__(self, window, source_queue, restart_on='\n'):
        self.window = window
        self.source_queue = source_queue
        self.restart_on = restart_on

        self.lines = dict()
        self.row_index = 0
        self._current_start_index = 0

        # the index from which to start drawing (for long pages)
        self.vertical_offset = 0

    @property
    def window_size(self):
        """The (height, width) pair of active window"""
        return self.window.getmaxyx()

    @property
    def window_height(self):
        """The height of active window"""
        return self.window_size[0]

    @property
    def window_width(self):
        """The width of active window"""
        return self.window_size[1]

    def scroll_down(self, full=False):
        """Scroll the page down"""

        # we should not hide more than a third of the lines
        # if some spaces are presented below
        allow_to_hide = int(len(self.lines) / 3)

        # we should be able to see the lower edge anyway
        max_offset = max(len(self.lines) - self.window_height + 1, allow_to_hide)

        if self.vertical_offset < max_offset:
            if full:
                self.vertical_offset = max_offset
            else:
                self.vertical_offset += 1
            self.redraw()

    def scroll_up(self, full=False):
        """Scroll the page up"""

        # do not allow empty lines at the top
        if self.vertical_offset > 0:
            if full:
                self.vertical_offset = 0
            else:
                self.vertical_offset -= 1
            self.redraw()

    def scroll_right(self):
        """Scroll the page to the right"""

        if not self.lines:
            return

        max_len = max(len(line) for line in itervalues(self.lines))
        # we should not hide more than a third of the lines
        # if some spaces are presented further to the right
        allow_to_hide = 0  # int(max_len / 3)

        # we should be able to see the right edge anyway
        max_offset = max(max_len - self.window_width + 1, allow_to_hide)

        if self.current_start_index < max_offset:
            self.current_start_index += 1
            self.redraw()

    def scroll_left(self):
        """Scroll the page to the left"""

        # do not allow empty lines at the top
        if self.current_start_index > 0:
            self.current_start_index -= 1
            self.redraw()

    @property
    def current_draw_position(self):
        """The y-coordinate to draw next line on"""
        return self.row_index - self.vertical_offset

    @property
    def current_start_index(self):
        """The default index to start printing the line from"""
        return self._current_start_index

    @current_start_index.setter
    def current_start_index(self, value):
        if value < 0:
            value = 0

        self._current_start_index = value

    def put_line(self, line, y_position=None, x_offset=0, start_index=None):
        """
        Draws the line on the current position
        (if it is within visible area)
        """

        if y_position is None:
            y_position = self.current_draw_position

        if start_index is None:
            start_index = self.current_start_index

        height, width = self.window_size
        # only draw if will be visible on a screen
        if 0 <= y_position <= height - 1:
            if start_index != 0:
                line = line[start_index:]

            # to fit in the screen
            line = line[:width - 1]

            if isinstance(line, string_types):
                line = line.encode('UTF-8')

            self.window.addstr(y_position, x_offset, line)

    def move_cursor(self, y_position, x_position):
        """Move the cursor to the specified coordinates"""

        if ((0 <= y_position <= self.window_height - 1) and (
                0 <= x_position <= self.window_width - 1)):
            self.window.move(y_position, x_position)

    def line_feed(self, x_cursor_position=0):
        """
        Shift the cursor (and the next line position) one line lower
        """
        self.row_index += 1
        self.move_cursor(self.current_draw_position, x_cursor_position)

    def redraw(self):
        """
        Redraw the whole screen from cached lines
        """
        save_index = self.row_index

        self.row_index = 0
        self.window.clear()
        for _, line in sorted(self.lines.items()):
            self.put_line(line)
            self.line_feed()

        self.row_index = save_index

    def update(self):
        """
        Read from the queue and update the screen if needed
        Return whether the screen was actually updated.
        """

        try:
            line = self.source_queue.get_nowait()
        except queue.Empty:
            return False

        if line == self.restart_on:
            self.window.refresh()
            self.row_index = 0
            return False

        redraw = False
        old_line = self.lines.get(line)
        if old_line != line:
            self.lines[self.row_index] = line
            redraw = True

        if redraw:
            self.put_line(line)

        self.line_feed()
        return redraw

    NO_OF_IDLE_UPDATES_TO_PAUSE = 1000
    # if you make it too low, the CPU will use its power for useless looping
    # on the other side, if the pause will be too high, the UI can become unresponsive
    PAUSE_ON_IDLE = 0.005

    def handle_pressed_key(self, key):
        """
        React when user press the key
        """
        if key in (curses.KEY_DOWN, ord(' ')):
            self.scroll_down()
        elif key == curses.KEY_END:
            self.scroll_down(full=True)

        elif key == curses.KEY_UP:
            self.scroll_up()
        elif key == curses.KEY_HOME:
            self.scroll_up(full=True)

        elif key == curses.KEY_RIGHT:
            self.scroll_right()
        elif key == curses.KEY_LEFT:
            self.scroll_left()

    @classmethod
    def draw(cls, window, source_queue, restart_on='\n'):
        """
        The entry point for a curses.wrapper to start the pager.

        `curses.wrapper(StringsPager.draw, queue)`
        """
        # clear and refresh the screen for a blank canvas
        window.clear()
        window.refresh()
        window.nodelay(True)
        curses.curs_set(False)

        # start colors in curses
        # curses.start_color()
        # curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)

        _self = cls(window, source_queue, restart_on=restart_on)

        idle_updates_counter = 0
        # prevent unnecessary lookups inside a loop
        idle_timeout = cls.PAUSE_ON_IDLE
        max_idle_updates = cls.NO_OF_IDLE_UPDATES_TO_PAUSE

        # k is the last character pressed
        k = 0
        while k != ord('q'):
            if k != -1:
                _self.handle_pressed_key(k)

            if _self.update():
                idle_updates_counter = 0
            else:
                idle_updates_counter += 1
                if idle_updates_counter >= max_idle_updates:
                    LOG.info('Pause curses for %s seconds...', idle_timeout)
                    time.sleep(idle_timeout)
                    idle_updates_counter = 0

            # Refresh the screen
            # window.refresh()

            # Wait for next input
            k = window.getch()


class CursesRenderer(BaseAsciiRenderer):
    """
    Hack for renderers to be able to put their strings in queue
    instead of printing them out into stream
    """

    def _print(self, *args):
        for arg in args:
            self.stream.put(arg)

    def render(self):
        # clear the screen before next board
        self._print(self.separator)
        super(CursesRenderer, self).render()
        # allow the drawing thread to do its job
        time.sleep(0)

    CLS_SEPARATOR = '\n'
    separator = CLS_SEPARATOR

    def draw(self, cells=None):
        """
        Additionally set up the separator between solutions
        to enable clearing the screen on ordinary update
        and informational message when a unique solution gets printed
        """
        if cells is None:
            self.separator = self.CLS_SEPARATOR
        else:
            # do not clear the screen for new solution
            self.separator = 'Unique solution'

        super(CursesRenderer, self).draw(cells=cells)
