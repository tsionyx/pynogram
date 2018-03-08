# -*- coding: utf-8 -*-
"""Define nonogram solver that uses contradictions"""

from __future__ import unicode_literals, print_function

import logging
import time
from collections import OrderedDict

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


class _SearchNode(object):
    def __init__(self, value):
        self.value = value
        self.children = OrderedDict()

    def to_dict(self):
        if not self.children:
            return self.value

        return {
            'value': self.value,
            'children': OrderedDict(
                (str(k), v.to_dict())
                for k, v in iteritems(self.children)
            )
        }


class Solver(object):
    """
    Solve the nonogram using contradictions and depth-first search
    """

    def __init__(self, board, max_solutions=None, timeout=None, max_depth=None):
        """
        :type board: Board
        """
        self.board = board
        self.colors = tuple(board.colors())

        self.max_solutions = max_solutions
        self.timeout = timeout
        if max_depth is None:
            # why 400?
            # I simply searched for some value that will be somehow bigger
            # than 351 (the maximum useful search depth reached on the test set so far)
            # but still reachable for recursion calls.
            #
            # NB: in current implementation depth=444 fails with
            # 'RuntimeError: maximum recursion depth exceeded'
            self.max_depth = 400
        else:
            self.max_depth = max_depth

        self.depth_reached = 0
        self.start_time = None
        self.explored_paths = set()
        self.search_map = None

    def _add_search_result(self, path, score):
        if isinstance(score, float):
            score = round(score, 4)

        if not path:
            if not self.search_map:
                self.search_map = _SearchNode(score)
            else:
                self.search_map.value = score
            return

        current = self.search_map

        for i, node in enumerate(path):
            # node = (i + 1, node)
            if i == len(path) - 1:
                val = score
            else:
                val = None

            if node not in current.children:
                current.children[node] = _SearchNode(val)

            current = current.children[node]

        current.value = score

    def _solve_with_guess(self, row_index, column_index, assumption):
        board = self.board
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
            self._add_solution()

        return rate

    def probe(self, row_index, column_index, assumption, rollback=True, force=False):
        """
        Try to find if the given cell can be in an assumed state.
        If the contradiction is found, set the cell
        in an inverted state and propagate the changes if needed.
        If `rollback` then the solved board will restore to the previous state
        after the assumption was made.
        If `force`, try to solve it anyway, even if the cell is already solved
        (to rerun the line solver).

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
            if not force:
                return False, None

        if assumption not in board.cell_colors(row_index, column_index):
            LOG.warning("The probe is useless: color '%s' already unset", assumption)
            return False, None

        save = board.make_snapshot()

        try:
            rate = self._solve_with_guess(row_index, column_index, assumption)
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
        try:
            board.unset_state(assumption, row_index, column_index)
        except ValueError as ex:
            raise NonogramError(str(ex))

        # try to solve with additional info
        # solve with only one cell as new info
        line.solve(
            board,
            row_indexes=(row_index,),
            column_indexes=(column_index,))

        return True, before_contradiction

    def _new_jobs_from_solution(self, job, previous_state, is_contradiction):
        board = self.board

        # evaluate generator
        changed = list(board.changed(previous_state))
        i, j, assumption = job
        log_contradiction = '(not) ' if is_contradiction else ''
        LOG.info('Changed %d cells with %s%s assumption',
                 len(changed), log_contradiction, assumption)

        # add the neighbours of the changed cells into jobs
        for coord in changed:
            for neighbour in board.unsolved_neighbours(*coord):
                yield neighbour, 1

        # add the neighbours of the selected cell into jobs
        for neighbour in board.unsolved_neighbours(i, j):
            yield neighbour, 0

    def _set_probe(self, state):
        board = self.board
        is_contradiction, prev_state = self.probe(*state, rollback=False, force=True)

        if is_contradiction:
            raise NonogramError('Real contradiction was found: %s' % (state,))

        if prev_state is None:
            LOG.warning("The probe for state '%s' does not return anything new", state)
            return ()

        if board.is_solved_full:
            return ()

        return self._new_jobs_from_solution(state, prev_state, is_contradiction)

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
                    if board.is_solved_full:
                        self._add_solution()
                        return counter_found, None

                    for new_job, priority in self._new_jobs_from_solution(
                            (i, j, assumption), info, is_contradiction):
                        jobs[new_job] = priority
                else:
                    rates[(i, j, assumption)] = (info, priority)

        return counter_found, self._probes_from_rates(rates)

    def _add_solution(self):
        line.solve(self.board, contradiction_mode=True)
        self.board.add_solution()

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
        if board.is_solved_full:
            board.set_finished()
            LOG.info('No need to solve with contradictions')
            return

        LOG.warning('Trying to solve using contradictions method')
        start = time.time()

        round_number = 1

        while True:
            # at first, take only high rated cells into account
            if round_number == 1:
                every = False
            else:
                # then, solve every cell that is left
                every = True

            found_contradictions, best_candidates = self._solve_without_search(every=every)
            current_solution_rate = board.solution_rate
            LOG.warning('Contradictions (%d): (found %d): %f',
                        round_number, found_contradictions, current_solution_rate)

            if found_contradictions == 0:
                break

            if current_solution_rate == 1:
                break

            round_number += 1

        if current_solution_rate < 1:
            # if stalled with sophisticated selection of cells
            # do the brute force search
            LOG.warning('Starting DFS (intelligent brute-force)')
            self.search(best_candidates)

            current_solution_rate = board.solution_rate
            LOG.warning('Search completed (depth reached: %d, solutions found: %d)',
                        self.depth_reached, len(board.solutions))

        if current_solution_rate != 1:
            LOG.warning('The nonogram is not solved full (with contradictions). '
                        'The rate is %.4f', current_solution_rate)

        board.set_finished()
        LOG.info('Full solution: %.6f sec', time.time() - start)
        for method, hit_rate in cache_hit_rate().items():
            if hit_rate > 0:
                LOG.warning('Cache hit rate (%s): %.4f%%', method, hit_rate * 100.0)

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

    def _try_state(self, state, path):
        """
        Trying to search for solutions in the given direction.
        At first it set the given state and get a list of the
        further jobs for finding the contradictions.
        Later that jobs will be used as candidates for a deeper search.

        :param state: the next cell and color to set
        :param path: the path that already have done
        """
        board = self.board

        depth = len(path)
        full_path = path + (state,)

        # add every cell to the jobs queue
        probe_jobs = self._get_all_unsolved_jobs()
        try:
            # update with more prioritized cells
            for new_job, priority in self._set_probe(state):
                probe_jobs[new_job] = priority

            if self._limits_reached(depth):
                return True

            __, best_candidates = self._solve_jobs(probe_jobs)
        except NonogramError as ex:
            LOG.error('Dead end found (%s): %s', full_path, str(ex))
            self._add_search_result(full_path, False)
            return False

        rate = board.solution_rate
        LOG.warning('Reached rate %.4f on %s path', rate, full_path)
        self._add_search_result(full_path, rate)

        if rate == 1 or self._limits_reached(depth):
            return True

        cells_left = round((1 - rate) * board.width * board.height)
        LOG.info('Unsolved cells left: %d', cells_left)

        if best_candidates:
            return self.search(best_candidates, path=full_path)

        return True

    # TODO: such a mapping should appear inside a ColoredBoard implementation:
    # the operations with integers always faster than with the strings.
    def _push_state(self, queue, state, priority):
        """
        Prevents annoying error for colored puzzles:
        'TypeError: unorderable types: bool() < str()'

        The state is a triple (x, y, color) which represent
        a single assumption about the next search direction.
        The error appears because of the color
        can be a string instance or 'False' (which is SPACE).
        That is why we move from a color name to a color index.
        """
        color = state[2]
        color_id = self.colors.index(color)
        state = tuple(state[:2]) + (color_id,)
        queue[state] = priority

    def _get_next_state(self, queue):
        """
        Transform the color index of a state to usable color name
        """
        state = list(queue.pop_smallest()[0])
        state[2] = self.colors[state[2]]
        return tuple(state)

    def _set_explored(self, path):
        self.explored_paths.add(tuple(sorted(path)))

    def _is_explored(self, path):
        return tuple(sorted(path)) in self.explored_paths

    def search(self, states, path=()):
        """
        Recursively search for solutions

        Return False if the given path is a dead end (no solutions can be found)
        """

        if self._is_explored(path):
            return True

        if self.start_time is None:
            self.start_time = time.time()

        board = self.board
        depth = len(path)

        if self._limits_reached(depth):
            return True

        if self.max_depth and depth >= self.max_depth:
            LOG.warning('Next step on the depth %d is deeper than the max (%d)',
                        depth, self.max_depth)
            return True

        # going to dive deeper, so increment it (full_path's length)
        if depth + 1 > self.depth_reached:
            self.depth_reached = depth + 1

        search_directions = PriorityDict()
        for state in states:
            self._push_state(search_directions, state, 1)

        search_counter = 0
        save = board.make_snapshot()
        try:
            while search_directions:
                total_number_of_directions = len(search_directions)
                state = self._get_next_state(search_directions)
                search_counter += 1

                if self._limits_reached(depth):
                    return True

                if state in path:
                    continue

                i, j, assumption = state
                cell = i, j
                cell_colors = board.cell_colors(*cell)

                if assumption not in cell_colors:
                    LOG.error("The assumption '%s' is already expired. "
                              "Possible colors for %s are %s",
                              assumption, cell, cell_colors)
                    continue

                if len(cell_colors) == 1:
                    LOG.error("Only one color for cell '%s' left: %s. Solve it unconditionally",
                              cell, assumption)
                    assert assumption == tuple(cell_colors)[0]
                    try:
                        self._solve_without_search(every=True)
                    except NonogramError:
                        # the whole `path` branch of a search tree is a dead end
                        LOG.error(
                            "The last possible color '%s' for the cell '%s' "
                            "lead to the contradiction. "
                            "The path %s is invalid", assumption, cell, path)
                        # self._add_search_result(path, False)
                        return False

                    rate = board.solution_rate
                    # self._add_search_result(path, rate)
                    if rate == 1:
                        self._add_solution()
                        LOG.warning(
                            "The only color '%s' for the cell '%s' lead to full solution. "
                            "No need to traverse the path %s anymore", assumption, cell, path)
                        return True
                    continue

                full_path = path + (state,)
                if self._is_explored(full_path):
                    LOG.info('The path %s already explored', full_path)
                    continue

                rate = board.solution_rate
                guess_save = board.make_snapshot()
                try:
                    LOG.warning('Trying state (%d/%d): %s (depth=%d, rate=%.4f, previous=%s)',
                                search_counter, total_number_of_directions,
                                state, depth, rate, path)
                    self._add_search_result(path, rate)
                    success = self._try_state(state, path)
                    is_solved = board.is_solved_full
                finally:
                    board.cells = guess_save
                    self._set_explored(full_path)

                if not success:
                    try:
                        board.unset_state(assumption, *cell)
                        self._solve_without_search(every=True)
                    except ValueError:
                        # the whole `path` branch of a search tree is a dead end
                        LOG.error(
                            "The last possible color '%s' for the cell '%s' "
                            "lead to the contradiction. "
                            "The path %s is invalid", assumption, cell, path)
                        # self._add_search_result(path, False)
                        return False

                    rate = board.solution_rate
                    # self._add_search_result(path, rate)
                    if rate == 1:
                        self._add_solution()
                        LOG.warning(
                            "The negation of color '%s' for the cell '%s' lead to full solution. "
                            "No need to traverse the path %s anymore", assumption, cell, path)
                        return True

                if not success or is_solved:
                    # immediately try the other colors as well
                    # if all of them goes to the dead end,
                    # then the parent path is a dead end
                    for color in cell_colors:
                        if color == assumption:
                            continue
                        self._push_state(search_directions, cell + (color,), 0)

        finally:
            # do not restore the solved cells on a root path - they are really solved!
            if path:
                board.cells = save
                self._set_explored(path)

        return True
