# -*- coding: utf-8 -*-
"""Define nonogram solver that uses contradictions"""

from __future__ import unicode_literals, print_function

import logging
import time

from six.moves import range

from pynogram.core.solver import line
from pynogram.core.solver.base import cache_hit_rate
from pynogram.core.solver.common import NonogramError
from pynogram.utils.priority_dict import PriorityDict

LOG = logging.getLogger(__name__)

USE_CONTRADICTION_RESULTS = True


def probe(board, row_index, column_index, assumption):
    """
    Try to find if the given cell can be in an assumed state.
    If the contradiction is found, set the cell
    in an inverted state and propagate the changes if needed.

    Returns a snapshot of the board. It contains the state of a board
    before any assumptions was made. It will help further to determine
    which cells has changed on that probe.
    """
    # already solved
    if board.cell_solved(row_index, column_index):
        return None

    save = board.make_snapshot()

    try:
        LOG.debug('Pretend that (%i, %i) is %s',
                  row_index, column_index, assumption)

        if board.is_colored:
            assumption = [assumption]

        board.cells[row_index][column_index] = assumption
        line.solve(
            board,
            row_indexes=(row_index,),
            column_indexes=(column_index,),
            contradiction_mode=True)

        if board.solution_rate == 1:
            LOG.warning("Found one of the solutions!")

        return None

    except NonogramError:
        LOG.debug('Contradiction', exc_info=True)
    finally:
        # rollback solved cells
        board.cells = save

    if USE_CONTRADICTION_RESULTS:
        before_contradiction = board.make_snapshot()
    else:
        before_contradiction = None

    LOG.info("Found contradiction at (%i, %i)",
             row_index, column_index)
    board.unset_state(assumption, row_index, column_index)

    # try to solve with additional info
    # solve with only one cell as new info
    line.solve(
        board,
        row_indexes=(row_index,),
        column_indexes=(column_index,))

    return before_contradiction


# pylint: disable=too-many-locals
def _solution_round(board, ignore_neighbours=False):
    """
    Do the one round of solving with contradictions.
    Returns the number of contradictions found.

    Based on https://www.cs.bgu.ac.il/~benr/nonograms/
    """

    counter_total, counter_found = 0, 0

    probe_jobs = PriorityDict()

    def _add_job(job, _priority):
        probe_jobs[job] = _priority

    for i in range(board.height):
        for j in range(board.width):
            if board.cell_solved(i, j):
                continue
            no_unsolved = len(list(board.unsolved_neighbours(i, j)))
            if ignore_neighbours or no_unsolved < 4:
                cell_rate = board.row_solution_rate(i) + board.column_solution_rate(j)
                _add_job((i, j), 4 - cell_rate + no_unsolved)

    while probe_jobs:
        (i, j), priority = probe_jobs.pop_smallest()
        counter_total += 1
        LOG.info('Probe #%d: %s (%f)', counter_total, (i, j), priority)

        for assumption in board.cell_colors(i, j):
            cells = probe(board, i, j, assumption)
            if cells is None:
                continue

            counter_found += 1
            if board.solution_rate == 1:
                return counter_found

            # evaluate generator
            changed = list(board.changed(cells))
            LOG.info('Changed %d cells with %s assumption',
                     len(changed), assumption)

            # add the neighbours of the changed cells into jobs
            for coord in changed:
                for neighbour in board.unsolved_neighbours(*coord):
                    _add_job(neighbour, 1)

            # add the neighbours of the selected cell into jobs
            for neighbour in board.unsolved_neighbours(i, j):
                _add_job(neighbour, 0)

    return counter_found


def solve(board):
    """
    Solve the nonogram to the most with contradictions
    and the basic `solve` method.

    :type board: Board
    """

    line.solve(board)
    if board.solution_rate == 1:
        board.set_solved()
        LOG.info('No need to solve with contradictions')
        return

    LOG.warning('Trying to solve using contradictions method')
    board.set_solved(False)
    start = time.time()

    round_number = 0
    # at first, take the number of unknown neighbours into account
    brute_force = False

    while True:
        prev_solution_rate = board.solution_rate
        found_contradictions = _solution_round(board, ignore_neighbours=brute_force)
        current_solution_rate = board.solution_rate

        round_number += 1
        LOG.warning('Contradiction round #%d (found %d): %f',
                    round_number, found_contradictions, current_solution_rate)

        if current_solution_rate == 1:
            break

        if current_solution_rate == prev_solution_rate:
            if brute_force:
                # give up if the brute force search is exhausted
                break
            else:
                # if stalled with sophisticated selection of cells
                # do the brute force search
                LOG.warning('Enabling brute force contradictions mode')
                brute_force = True

    board.set_solved()
    solution_rate = board.solution_rate
    if solution_rate != 1:
        LOG.warning('The nonogram is not solved full (with contradictions). '
                    'The rate is %.4f', solution_rate)
    LOG.info('Full solution: %.6f sec', time.time() - start)
    for method, hit_rate in cache_hit_rate().items():
        LOG.info('Cache hit rate (%s): %.4f%%', method, hit_rate * 100.0)
