# -*- coding: utf-8 -*
"""
Defines methods to parse data file with the board defined
"""

from __future__ import unicode_literals, print_function

import os
import re

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def _append_line_to_list(description_line, descriptions_list):
    """
    Parse a line and correctly add the description(s) to a collection
    """
    # there can be trailing commas if you copy from source code
    descriptions = description_line.strip(',').split(',')

    # strip all the spaces and quotes
    descriptions = [desc.strip().strip("'").strip('"').strip() for desc in descriptions]

    return descriptions_list.extend(descriptions)


_ALLOWED_EMPTY_LINES_IN_A_ROW_INSIDE_BLOCK = 1

_NOT_READ = 0
_READ_COLORS = 1
_READ_COLUMNS = 2
_READ_ROWS = 3
_COMPLETE = 4

_STATES = (_NOT_READ, _READ_COLORS, _READ_COLUMNS, _READ_ROWS, _COMPLETE)
_COLOR_RE = re.compile(r'color:[ \t]*(.+)\((.+)\) (.+)')


def read(stream):
    """
    Read and parse lines from a stream to create a nonogram board
    """
    colors = dict()
    columns = []
    rows = []

    state = _NOT_READ
    next_block = False
    empty_lines_counter = 0

    for i, line in enumerate(stream):
        # ignore whitespaces
        line = line.strip()

        # strip out the trailing comment
        comment_index = line.find('#')
        if comment_index >= 0:
            line = line[:comment_index].rstrip()

        # ignore empty lines
        if not line:
            empty_lines_counter += 1

            # if already start to read columns
            # and the empty line appeared
            # then the following info is about rows
            if empty_lines_counter > _ALLOWED_EMPTY_LINES_IN_A_ROW_INSIDE_BLOCK:
                next_block = True

            continue  # pragma: no cover

        if state == _NOT_READ or next_block:
            state += 1
            next_block = False

        empty_lines_counter = 0

        if state == _READ_COLORS:
            match = _COLOR_RE.match(line)
            if match:
                colors[match.group(1)] = match.groups()[1:]
                continue
            else:
                # black and white nonogram
                state += 1

        if state == _COMPLETE:
            raise ValueError("Found excess info on the line {} "
                             "while EOF expected: '{}'".format(i, line))

        assert state in (_READ_ROWS, _READ_COLUMNS)
        current = rows if state == _READ_ROWS else columns
        _append_line_to_list(line, current)

    if colors:
        return columns, rows, colors

    return columns, rows


def examples_file(file_name=''):
    """
    Returns a path to the examples board in text files
    """
    project_dir = os.path.dirname(os.path.dirname(CURRENT_DIR))
    examples_dir = os.path.join(project_dir, 'examples')
    if file_name:
        file_name = os.path.join(examples_dir, file_name)
        if not os.path.isfile(file_name):
            txt_file_name = file_name + '.txt'
            if os.path.isfile(txt_file_name):
                return txt_file_name

        return file_name

    return examples_dir
