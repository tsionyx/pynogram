# -*- coding: utf-8 -*
"""Define nonogram solver that solves line-by-line"""

from __future__ import unicode_literals, print_function

import logging
import os
import time

from pynogram.core.board import ColoredBoard
from pynogram.core.common import (
    UNKNOWN, BOX, SPACE,
    is_list_like,
)
from pynogram.core.solver.base import (
    assert_match, solve_line,
)
from pynogram.utils.priority_dict import PriorityDict

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


# pylint: disable=too-many-arguments, too-many-locals
def solve_row(board, index, is_column, method,
              contradiction_mode=False):
    """
    Solve a line with the solving `method`.
    If the line gets partially solved,
    put the crossed lines into queue.

    Return the list of new jobs that should be put into queue.
    """

    start = time.time()

    if is_column:
        row_desc = board.columns_descriptions[index]
        row = board.get_column(index)
        desc = 'column'
    else:
        row_desc = board.rows_descriptions[index]
        row = board.get_row(index)
        desc = 'row'

    pre_solution_rate = board.line_solution_rate(row)

    if pre_solution_rate == 1:
        if contradiction_mode:
            assert_match(row_desc, row)
        else:
            # do not check solved lines in trusted mode
            return ()

    LOG.debug('Solving %s %s: %s. Partial: %s',
              index, desc, row_desc, row)

    updated = solve_line(row_desc, row, method=method)

    new_jobs = []
    if board.line_solution_rate(updated) > pre_solution_rate:
        # LOG.debug('Queue: %s', jobs_queue)
        LOG.debug(row)
        LOG.debug(updated)
        for i, (pre, post) in enumerate(zip(row, updated)):
            if pre != post:
                if is_list_like(post):  # colored
                    if set(pre) == set(post):
                        continue
                    assert len(pre) > len(post)
                else:
                    assert pre == UNKNOWN
                    assert post in (BOX, SPACE)

                new_jobs.append((not is_column, i))
        # LOG.debug('Queue: %s', jobs_queue)
        LOG.debug('New info on %s %s: %s', desc, index, [job_index for _, job_index in new_jobs])

        if is_column:
            board.set_column(index, updated)
        else:
            board.set_row(index, updated)

    LOG.debug('%ss solution: %.6f sec', desc.title(), time.time() - start)
    return new_jobs


def solve(board, parallel=False,
          row_indexes=None, column_indexes=None,
          contradiction_mode=False, methods=None):
    """
    Solve the nonogram to the most using two methods (by default):
    - firstly with simple right-left overlap algorithm
    - then with FSM and reverse tracking

    All methods use priority queue to store the lines needed to solve.
    """

    if methods is None:
        if isinstance(board, ColoredBoard):
            methods = ('reverse_tracking_color',)
        else:
            methods = ('simpson', 'reverse_tracking')

    if not isinstance(methods, (tuple, list)):
        methods = [methods]

    for method in methods:
        jobs = _solve_with_method(
            board, method,
            parallel=parallel,
            row_indexes=row_indexes,
            column_indexes=column_indexes,
            contradiction_mode=contradiction_mode)

        row_indexes = [index for is_column, index in jobs if not is_column]
        column_indexes = [index for is_column, index in jobs if is_column]


def _solve_with_method(
        board, method, parallel=False,
        row_indexes=None, column_indexes=None,
        contradiction_mode=False):
    """Solve the nonogram to the most using given method"""

    if board.solution_rate == 1:
        return ()

    lines_solved = 0

    if parallel:
        # TODO: add parallel logic here
        LOG.info("Using several processes to solve")

    start = time.time()

    # every job is a tuple (is_column, index)
    #
    # Why `is_column`, not `is_row`?
    # To assign more priority to the rows:
    # when adding row, `is_column = False = 0`
    # when adding column, `is_column = True = 1`
    # heap always pops the lowest item, so the rows will go first

    LOG.info("Solving %s rows and %s columns with '%s' method",
             row_indexes, column_indexes, method)

    line_jobs = PriorityDict()
    all_jobs = set()

    def _add_job(job, _priority):
        line_jobs[job] = _priority
        all_jobs.add(job)

    if row_indexes is None:
        row_indexes = range(board.height)

    for row_index in row_indexes:
        _add_job((False, row_index), 0)

    if column_indexes is None:
        column_indexes = range(board.width)

    for column_index in column_indexes:
        _add_job((True, column_index), 0)

    while line_jobs:
        (is_column, index), priority = line_jobs.pop_smallest()
        new_jobs = solve_row(board, index, is_column, method,
                             contradiction_mode=contradiction_mode)

        for new_job in new_jobs:
            # lower priority = more priority
            _add_job(new_job, priority - 1)

        lines_solved += 1

    # all the following actions applied only to verified solving
    if not contradiction_mode:
        board.solution_round_completed()

        # self._solved = True
        if board.solution_rate != 1:
            LOG.warning("The nonogram is not solved full ('%s'). The rate is %.4f",
                        method, board.solution_rate)
        LOG.info('Full solution: %.6f sec', time.time() - start)
        LOG.info('Lines solved: %i', lines_solved)

    return all_jobs
