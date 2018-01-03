# -*- coding: utf-8 -*
"""Define nonogram solver that solve line-by-line"""

from __future__ import unicode_literals, print_function

import logging
import os
import time

from pyngrm.core import UNKNOWN, BOX, SPACE
from pyngrm.core.solve import assert_match, solve_line
from pyngrm.utils.priority_dict import PriorityDict

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


# pylint: disable=too-many-arguments, too-many-locals
def solve_row(self, index, is_column, priority, jobs_queue,
              contradiction_mode=False):
    """
    Solve one line with FSM.
    If line gets partially solved,
    put the crossed lines into queue
    """

    start = time.time()

    if is_column:
        row_desc, row = self.columns_descriptions[index], self.cells.T[index]
        desc = 'column'
    else:
        row_desc, row = self.rows_descriptions[index], self.cells[index]
        desc = 'row'

    pre_solution_rate = self.row_solution_rate(row)

    if pre_solution_rate == 1:
        if contradiction_mode:
            assert_match(row_desc, row)
        else:
            # do not check solved lines in trusted mode
            return

    LOG.debug('Solving %s %s: %s. Partial: %s. Priority: %s',
              index, desc, row_desc, row, priority)

    updated = solve_line(row_desc, row)

    if self.row_solution_rate(updated) > pre_solution_rate:
        LOG.debug('New info on %s %s: %s', desc, index, updated)
        LOG.debug('Queue: %s', jobs_queue)

        for i, (pre, post) in enumerate(zip(row, updated)):
            if pre != post:
                assert pre == UNKNOWN
                assert post in (BOX, SPACE)

                jobs_queue[(not is_column, i)] = priority - 1
        LOG.debug('Queue: %s', jobs_queue)

        if is_column:
            self.cells[:, index] = updated
            self.column_updated(index)
        else:
            self.cells[index] = updated
            self.row_updated(index)

    LOG.debug('%ss solution: %.6f sec', desc.title(), time.time() - start)


def solve(board, parallel=False,
          row_indexes=None, column_indexes=None,
          contradiction_mode=False):
    """Solve the nonogram to the most with FSM using priority queue"""
    if board.solution_rate == 1:
        return

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

    line_jobs = PriorityDict()

    if row_indexes is None:
        row_indexes = range(board.height)

    for row_index in row_indexes:
        line_jobs[(False, row_index)] = 0

    if column_indexes is None:
        column_indexes = range(board.width)

    for column_index in column_indexes:
        line_jobs[(True, column_index)] = 0

    while line_jobs:
        (is_column, index), priority = line_jobs.pop_smallest()
        solve_row(board, index, is_column, priority, line_jobs,
                  contradiction_mode=contradiction_mode)
        lines_solved += 1

    # all the following actions applied only to verified solving
    if contradiction_mode:
        return

    board.solution_round_completed()

    # self._solved = True
    if board.solution_rate != 1:
        LOG.warning('The nonogram is not solved full. The rate is %.4f', board.solution_rate)
    LOG.info('Full solution: %.6f sec', time.time() - start)
    LOG.info('Lines solved: %i', lines_solved)
