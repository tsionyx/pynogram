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

# use the position of a cell (number of neighbours and solution rate of row/column)
# to adjust its rate when choosing the next probe for DFS
ADJUST_RATE = True


class Solver(object):
    """
    Solve the nonogram using contradictions and depth-first search
    """

    def __init__(self, board, max_solutions=None, timeout=None, max_depth=None):
        """
        :type board: Board
        """
        self.board = board
        self.max_solutions = max_solutions
        self.timeout = timeout
        self.max_depth = max_depth

        self.depth_reached = 0
        self.start_time = None
        # TODO: do I need it?
        self.dead_ends = set()

    def probe(self, row_index, column_index, assumption, rollback=True):
        """
        Try to find if the given cell can be in an assumed state.
        If the contradiction is found, set the cell
        in an inverted state and propagate the changes if needed.
        If `rollback` the solved board will restore to the previous state
        after the assumption was made.

        Return the pair `(is_contradiction, new_info)` where

        is_contradiction: whether the assumption led to a contradiction

        new_info:
          a) when contradiction is found, it contains the state of the board
          before any assumptions was made. It will help further to determine
          which cells has changed on that probe.
          b) if no contradiction found, but `rollback` is False,
          then we do not restore the board and return the previous state also.
          c) otherwise it contains the solution rate for the partially
          solved board (if the assumption made is true)
        """
        board = self.board

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
                board.add_solution(copy_=False)

            if rollback:
                board.cells = save
                return False, rate

            return False, save

        except NonogramError:
            LOG.debug('Contradiction', exc_info=True)
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

    def _new_jobs_from_solution(self, job, previous_state):
        board = self.board

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

    def _guess(self, state):
        board = self.board
        is_contradiction, prev_state = self.probe(*state, rollback=False)

        if is_contradiction:
            LOG.warning('Real contradiction was found: %s', state)

        assert prev_state is not None

        if board.solution_rate == 1:
            board.add_solution()
            return ()

        return self._new_jobs_from_solution(state, prev_state)

    def _solve_jobs(self, jobs):
        """
        Given a board and a list of jobs try to solve that board
        using the jobs as probes.

        Return the number of contradictions found and the
        best candidate for the tree-base search
        """

        counter_total, counter_found = 0, 0
        rates = dict()

        board = self.board

        while jobs:
            job, priority = jobs.pop_smallest()
            counter_total += 1
            LOG.info('Probe #%d: %s (%f)', counter_total, job, priority)

            # if the job is only coordinates
            # then try all the possible colors
            if len(job) == 2:
                i, j = job
                assumptions = board.cell_colors(i, j)
            else:
                i, j, color = job
                assumptions = (color,)

            for assumption in assumptions:
                is_contradiction, info = self.probe(i, j, assumption)

                if info is None:
                    continue

                if is_contradiction:
                    counter_found += 1
                    if board.solution_rate == 1:
                        board.add_solution()
                        return counter_found, None

                    for new_job, priority in self._new_jobs_from_solution(
                            (i, j, assumption), info):
                        jobs[new_job] = priority
                else:
                    rates[(i, j, assumption)] = (info, priority)

        return counter_found, self._probes_from_rates(rates)

    def _probes_from_rates(self, rates):
        best = dict()
        for job, (rate, priority) in iteritems(rates):
            cell = job[:2]
            if self.board.cell_solved(*cell):
                continue

            # the more priority the less desired that job
            # priority is in the range [0, 8]
            if ADJUST_RATE:
                rate += (10 - priority)
            # if rate > best.get(job, 0):
            best[job] = rate

        # the biggest rate appears first
        best = sorted(iteritems(best), key=lambda x: x[1], reverse=True)
        LOG.debug('\n'.join(map(str, best)))

        # but return only the jobs, not rates
        return tuple(job for job, rate in best)

    def _get_all_unsolved_jobs(self, skip_low_rated=False):
        board = self.board

        probe_jobs = PriorityDict()
        # add every cell
        for i in range(board.height):
            for j in range(board.width):
                if board.cell_solved(i, j):
                    continue

                no_unsolved = len(list(board.unsolved_neighbours(i, j)))

                if no_unsolved >= 4 and skip_low_rated:
                    continue

                cell_rate = board.row_solution_rate(i) + board.column_solution_rate(j)
                probe_jobs[(i, j)] = 4 - cell_rate + no_unsolved

        return probe_jobs

    def _solve_without_search(self, every=False):
        """
        Do the one round of solving with contradictions.
        Returns the number of contradictions found.

        Based on https://www.cs.bgu.ac.il/~benr/nonograms/
        """

        probe_jobs = self._get_all_unsolved_jobs(skip_low_rated=not every)
        return self._solve_jobs(probe_jobs)

    def solve(self):
        """
        Solve the nonogram to the most with contradictions
        """

        board = self.board

        line.solve(board)
        if board.solution_rate == 1:
            board.set_solved()
            LOG.info('No need to solve with contradictions')
            return

        LOG.warning('Trying to solve using contradictions method')
        board.set_solved(False)
        start = time.time()

        # at first, take the number of unknown neighbours into account
        found_contradictions, best_candidates = self._solve_without_search()
        current_solution_rate = board.solution_rate
        LOG.warning('Contradictions: (found %d): %f',
                    found_contradictions, current_solution_rate)

        round_number = 2
        # prev_found = None
        # while True:
        #     if current_solution_rate == 1:
        #         break
        if current_solution_rate < 1:
            # then, solve every cell that is left
            found_contradictions, best_candidates = self._solve_without_search(every=True)
            current_solution_rate = board.solution_rate
            LOG.warning('Contradictions (%d): (found %d): %f',
                        round_number, found_contradictions, current_solution_rate)

            # if found_contradictions in (prev_found, 0):
            #     break
            #
            # prev_found = found_contradictions
            # round_number += 1

        if current_solution_rate < 1:
            # if stalled with sophisticated selection of cells
            # do the brute force search
            LOG.warning('Starting DFS (intelligent brute-force)')
            self.search(best_candidates)

            LOG.warning('Search completed (depth reached: %d, solutions found: %d)',
                        self.depth_reached, len(board.solutions))

        board.set_solved()
        solution_rate = board.solution_rate
        if solution_rate != 1:
            LOG.warning('The nonogram is not solved full (with contradictions). '
                        'The rate is %.4f', solution_rate)
        LOG.info('Full solution: %.6f sec', time.time() - start)
        for method, hit_rate in cache_hit_rate().items():
            LOG.info('Cache hit rate (%s): %.4f%%', method, hit_rate * 100.0)

    def _limits_reached(self, depth):
        """
        Whether we reached the defined limits:
        1) number of solutions found
        2) the maximum allowed run time
        """
        if self.max_solutions:
            solutions_number = len(self.board.solutions)
            if solutions_number >= self.max_solutions:
                if depth == 0:
                    # only show log on the top level
                    LOG.warning('%d solutions is enough', solutions_number)

                return True

        if self.timeout and self.start_time:
            run_time = time.time() - self.start_time
            if run_time > self.timeout:
                if depth == 0:
                    # only show log on the top level
                    LOG.warning('Searched too long: %.4fs', run_time)
                return True

        return False

    def search(self, states, path=()):
        """Recursively search for solutions"""

        if self.start_time is None:
            self.start_time = time.time()

        board = self.board
        depth = len(path)

        if self._limits_reached(depth):
            return

        if depth > self.depth_reached:
            self.depth_reached = depth

        if self.max_depth and depth > self.max_depth:
            LOG.warning('%d deeper than max (%d)', depth, self.max_depth)
            return

        rate = board.solution_rate

        number_of_states_to_try = len(states)

        for i, state in enumerate(states):
            if state in path:
                continue

            full_path = path + (state,)
            if full_path in self.dead_ends:
                LOG.info('The path %s already explored', full_path)
                continue

            save = board.make_snapshot()
            try:
                LOG.warning('Trying state (%d/%d): %s (depth=%d, rate=%.4f, previous=%s)',
                            i + 1, number_of_states_to_try, state, depth, rate, path)
                try:
                    # add every cell
                    probe_jobs = self._get_all_unsolved_jobs()

                    # update with more prioritized cells
                    for new_job, priority in self._guess(state):
                        probe_jobs[new_job] = priority

                    if self._limits_reached(depth):
                        return

                    __, best_candidates = self._solve_jobs(probe_jobs)

                    cells_left = round((1 - board.solution_rate) * board.width * board.height)
                    if cells_left > 0:
                        LOG.info('Unsolved cells left: %d', cells_left)

                except NonogramError:
                    self.dead_ends.add(full_path)
                    LOG.warning('Dead end found: %s', full_path)
                    continue

                LOG.warning('Reached rate %.4f on %s path', board.solution_rate, full_path)

                if self._limits_reached(depth):
                    return

                if best_candidates:
                    self.search(best_candidates, path=full_path)

                    if self._limits_reached(depth):
                        return

            finally:
                board.cells = save
