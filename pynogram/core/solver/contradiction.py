# -*- coding: utf-8 -*-
"""Define nonogram solver that uses contradictions"""

from __future__ import unicode_literals, print_function

import logging
import time

from six import iteritems
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

    Return the pair `(useful, new_info)` where

    useful: whether the assumption led to a contradiction

    new_info:
      a) when `useful`, it contains the state of the board
      before any assumptions was made. It will help further to determine
      which cells has changed on that probe.
      b) otherwise it contains the solution rate for the partially solved board
    """
    # already solved
    if board.cell_solved(row_index, column_index):
        return False, None

    save = board.make_snapshot()

    try:
        LOG.debug('Assume that (%i, %i) is %s',
                  row_index, column_index, assumption)

        if board.is_colored:
            assumption = [assumption]

        board.cells[row_index][column_index] = assumption
        line.solve(
            board,
            row_indexes=(row_index,),
            column_indexes=(column_index,),
            contradiction_mode=True)

        rate = board.solution_rate
        if rate == 1:
            LOG.info("Found one of the solutions!")
            board.add_solution(copy_=False)

        return False, rate

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

    return True, before_contradiction


def _new_jobs_from_solution(board, job, previous_state):
    # evaluate generator
    changed = list(board.changed(previous_state))
    i, j, assumption = job
    LOG.info('Changed %d cells with %s assumption',
             len(changed), assumption)

    # add the neighbours of the changed cells into jobs
    for coord in changed:
        for neighbour in board.unsolved_neighbours(*coord):
            yield neighbour, 1

    # add the neighbours of the selected cell into jobs
    for neighbour in board.unsolved_neighbours(i, j):
        yield neighbour, 0


def _solve_jobs(board, jobs):
    """
    Given a board and a list of jobs try to solve that board
    using the jobs as probes.

    Return the number of contradictions found and the
    best candidate for the following search
    """

    counter_total, counter_found = 0, 0
    rates = dict()

    while jobs:
        (i, j), priority = jobs.pop_smallest()
        counter_total += 1
        LOG.info('Probe #%d: %s (%f)', counter_total, (i, j), priority)

        for assumption in board.cell_colors(i, j):
            is_contradiction, info = probe(board, i, j, assumption)

            if info is None:
                continue

            if is_contradiction:
                counter_found += 1
                if board.solution_rate == 1:
                    return counter_found, None

                for new_job, priority in _new_jobs_from_solution(
                        board, (i, j, assumption), info):
                    jobs[new_job] = priority
            else:
                rates[(i, j, assumption)] = info

    return counter_found, _probes_from_rates(board, rates)


def _probes_from_rates(board, rates):
    best = dict()
    for (i, j, __), rate in iteritems(rates):
        cell = (i, j)
        if board.cell_solved(*cell):
            continue

        if rate > best.get(cell, 0):
            best[cell] = rate

    return tuple(k for v, k in sorted(
        ((v, k) for k, v in iteritems(best)), reverse=True))


def _solve_without_search(board, every=False):
    """
    Do the one round of solving with contradictions.
    Returns the number of contradictions found.

    Based on https://www.cs.bgu.ac.il/~benr/nonograms/
    """

    probe_jobs = PriorityDict()

    for i in range(board.height):
        for j in range(board.width):
            if board.cell_solved(i, j):
                continue

            no_unsolved = len(list(board.unsolved_neighbours(i, j)))
            if every or no_unsolved < 4:
                cell_rate = board.row_solution_rate(i) + board.column_solution_rate(j)
                probe_jobs[(i, j)] = 4 - cell_rate + no_unsolved

    return _solve_jobs(board, jobs=probe_jobs)


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

    # at first, take the number of unknown neighbours into account
    found_contradictions, best_candidates = _solve_without_search(board)
    current_solution_rate = board.solution_rate

    LOG.warning('Contradictions: (found %d): %f',
                found_contradictions, current_solution_rate)

    if current_solution_rate < 1:
        # if stalled with sophisticated selection of cells
        # do the brute force search
        # TODO: add some DFS-routine here
        depth = 0
        LOG.warning('Full search: (max depth %d): %f',
                    depth, current_solution_rate)

    board.set_solved()
    solution_rate = board.solution_rate
    if solution_rate != 1:
        LOG.warning('The nonogram is not solved full (with contradictions). '
                    'The rate is %.4f', solution_rate)
    LOG.info('Full solution: %.6f sec', time.time() - start)
    for method, hit_rate in cache_hit_rate().items():
        LOG.info('Cache hit rate (%s): %.4f%%', method, hit_rate * 100.0)
