# -*- coding: utf-8 -*
"""
Defines methods to parse data file with the board defined
"""

from __future__ import unicode_literals, print_function

import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def _append_line_to_list(clues_line, clues_list):
    """
    Parse a line and correctly add the clues to a collection
    """
    # there can be trailing commas if you copy from source code
    clues = clues_line.strip(',').split(',')

    # strip all the spaces and quotes
    clues = [clue.strip().strip("'").strip('"').strip() for clue in clues]

    return clues_list.extend(clues)


_ALLOWED_EMPTY_LINES_IN_A_ROW_INSIDE_BLOCK = 1


def read(stream):
    """
    Read and parse lines from a stream to create a nonogram board
    """
    # set when the appropriate text appears
    columns_appears = False
    rows_appears = False

    # signifies which collection to fill now
    fill_rows = False
    # shows that the columns and rows already filled up
    read_complete = False

    columns = []
    rows = []

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
            if columns_appears:
                if empty_lines_counter > _ALLOWED_EMPTY_LINES_IN_A_ROW_INSIDE_BLOCK:
                    fill_rows = True

            # if already start to read rows
            # and the empty line appeared
            # then all the info already had read
            if rows_appears:
                if empty_lines_counter > _ALLOWED_EMPTY_LINES_IN_A_ROW_INSIDE_BLOCK:
                    read_complete = True

            continue  # pragma: no cover

        empty_lines_counter = 0
        # the first non-empty line should contains column(s) info
        if fill_rows:  # pylint: disable=simplifiable-if-statement
            rows_appears = True
        else:
            columns_appears = True

        if read_complete:
            raise ValueError("Found excess info on the line {} "
                             "while EOF expected: '{}'".format(i, line))

        current = rows if fill_rows else columns
        _append_line_to_list(line, current)

    return columns, rows


def examples_file(file_name=''):
    """
    Returns a path to the examples board in text files
    """
    examples_dir = os.path.join(os.path.dirname(CURRENT_DIR), 'examples')
    if file_name:
        return os.path.join(examples_dir, file_name)

    return examples_dir
