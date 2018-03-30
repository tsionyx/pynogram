# -*- coding: utf-8 -*-
"""Define nonogram solver that solves line-by-line"""

from __future__ import unicode_literals, print_function

import logging
import time

from six.moves import zip

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE,
    is_list_like,
)
from pynogram.core.solver.base import solve_line
from pynogram.utils.priority_dict import PriorityDict

LOG = logging.getLogger(__name__)


# pylint: disable=too-many-arguments, too-many-locals, too-many-branches
def solve_row(board, index, is_column, method):
    """
    Solve a line with the solving `method`.
    If the line gets partially solved,
    put the crossed lines into queue.

    Return the number of solved cells and the list of new jobs that should be solved next.
    """

    # start = time.time()

    if is_column:
        row_desc = board.columns_descriptions[index]
        row = tuple(board.get_column(index))
        # desc = 'column'
    else:
        row_desc = board.rows_descriptions[index]
        row = tuple(board.get_row(index))
        # desc = 'row'

    # pre_solution_rate = board.line_solution_rate(row)

    # if board.is_line_solved(row):
    #     # do not check solved lines in trusted mode
    #     if contradiction_mode:
    #         assert_match(row_desc, row)
    #     return 0, ()

    # LOG.debug('Solving %s %s: %s. Partial: %s', index, desc, row_desc, row)

    updated = solve_line(row_desc, row, method=method)

    cells_solved = 0
    new_jobs = []

    # if board.line_solution_rate(updated) > pre_solution_rate:
    if row != updated:
        # LOG.debug('Queue: %s', jobs_queue)
        # LOG.debug(row)
        # LOG.debug(updated)
        for i, (pre, post) in enumerate(zip(row, updated)):
            if pre != post:
                if is_list_like(post):  # colored
                    if set(pre) == set(post):
                        continue
                    assert len(pre) > len(post)
                    cells_solved += 1
                else:
                    assert pre == UNKNOWN
                    assert post in (BOX, SPACE)
                    cells_solved += 1

                new_jobs.append((not is_column, i))
        # LOG.debug('Queue: %s', jobs_queue)
        # LOG.debug('New info on %s %s: %s', desc, index, [job_index for _, job_index in new_jobs])

        if is_column:
            board.set_column(index, updated)
        else:
            board.set_row(index, updated)

    # LOG.debug('%ss solution: %.6f sec', desc, time.time() - start)
    return cells_solved, new_jobs


def solve(board, parallel=False,
          row_indexes=None, column_indexes=None,
          contradiction_mode=False, methods=None):
    """
    Solve the nonogram to the most using two methods (by default):
    - firstly with simple right-left overlap algorithm
    - then with FSM and reverse tracking

    All methods use priority queue to store the lines needed to solve.

    Return the total number of solved cells.
    """

    if methods is None:
        if board.is_colored:
            methods = ('reverse_tracking_color',)
        else:
            # methods = ('simpson', 'reverse_tracking')
            methods = ('bgu',)

    if not isinstance(methods, (tuple, list)):
        methods = [methods]

    total_cells_solved = 0
    for method in methods:
        cells_solved, jobs = _solve_with_method(
            board, method,
            parallel=parallel,
            row_indexes=row_indexes,
            column_indexes=column_indexes,
            contradiction_mode=contradiction_mode)

        total_cells_solved += cells_solved
        row_indexes = [index for is_column, index in jobs if not is_column]
        column_indexes = [index for is_column, index in jobs if is_column]

    return total_cells_solved


def _solve_with_method(
        board, method, parallel=False,
        row_indexes=None, column_indexes=None,
        contradiction_mode=False):
    """Solve the nonogram to the most using given method"""

    # `is_solved_full` is cost, so minimize calls to it.
    # Do not call if only a handful of lines has to be solved
    if row_indexes is None or column_indexes is None or \
            len(row_indexes) > 2 or len(column_indexes) > 2:

        # do not call if contradiction_mode == False
        if not contradiction_mode and board.is_solved_full:
            return 0, ()

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

    LOG.debug("Solving %s rows and %s columns with '%s' method",
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

    total_cells_solved = 0

    while line_jobs:
        (is_column, index), priority = line_jobs.pop_smallest()
        cells_solved, new_jobs = solve_row(board, index, is_column, method)

        total_cells_solved += cells_solved
        for new_job in new_jobs:
            # lower priority = more priority
            _add_job(new_job, priority - 1)

        lines_solved += 1

    # all the following actions applied only to verified solving
    if not contradiction_mode:
        board.solution_round_completed()

        # rate = board.solution_rate
        # if rate != 1:
        #     LOG.warning("The nonogram is not solved full ('%s'). The rate is %.4f",
        #                 method, rate)
        LOG.info('Full solution: %.6f sec', time.time() - start)
        LOG.info('Lines solved: %i', lines_solved)

    return total_cells_solved, all_jobs
