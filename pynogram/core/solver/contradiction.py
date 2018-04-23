# -*- coding: utf-8 -*-
"""Define nonogram solver that uses contradictions"""

from __future__ import unicode_literals, print_function

import logging
import time
from collections import OrderedDict, defaultdict, deque
from itertools import product

from six import iteritems
from six.moves import range

from pynogram.core.board import CellPosition, CellState
from pynogram.core.solver import line
from pynogram.core.solver.base import cache_hit_rate
from pynogram.core.solver.common import NonogramError
from pynogram.utils.priority_dict import PriorityDict

LOG = logging.getLogger(__name__)

USE_CONTRADICTION_RESULTS = True

# the fewer possible colors for a cell
# the earlier it appears in a list of candidates
FEW_COLORS_FIRST = False

# use the position of a cell (number of neighbours and solution rate of row/column)
# to adjust its rate when choosing the next probe for DFS
ADJUST_RATE = True


class _SearchNode(object):
    def __init__(self, value):
        self.value = value
        self.children = OrderedDict()

    def to_dict(self):
        """Represent the given node as the dictionary of other nodes"""

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

        self.max_solutions = max_solutions
        self.timeout = timeout
        if max_depth is None:
            # why 400?
            # I simply searched for some value that will be somehow bigger
            # than 351 (the maximum useful search depth reached on the test set so far),
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

    def propagate_change(self, cell_state):
        """
        Set the given color to given cell
        and try to solve the board with that new info.
        :type cell_state: CellState
        """
        board = self.board
        LOG.debug('Assume that (%i, %i) is %s', *tuple(cell_state))

        board.set_state(cell_state)

        return line.solve(
            board,
            row_indexes=(cell_state.row_index,),
            column_indexes=(cell_state.column_index,),
            contradiction_mode=True)

    def probe(self, cell_state, rollback=True, force=False):
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
          c) otherwise it contains the number of solved cells for the partially
          solved board (if the assumption made is true)
        """
        board = self.board

        pos = cell_state.position
        assumption = cell_state.color
        # already solved
        if board.cell_solved(pos):
            if not force:
                return False, None

        if assumption not in board.cell_colors(pos):
            LOG.warning("The probe is useless: color '%s' already unset", assumption)
            return False, None

        save = board.make_snapshot()

        try:
            solved_cells = self.propagate_change(cell_state)

            if board.is_solved_full:
                self._add_solution()

        except NonogramError:
            LOG.debug('Contradiction', exc_info=True)
            # rollback solved cells
            board.restore(save)

        else:
            if rollback:
                board.restore(save)
                return False, solved_cells

            return False, save

        if USE_CONTRADICTION_RESULTS:
            before_contradiction = board.make_snapshot()
        else:
            before_contradiction = None

        pos = cell_state.position
        LOG.info("Found contradiction at (%i, %i)", *pos)
        try:
            board.unset_state(cell_state)
        except ValueError as ex:
            raise NonogramError(str(ex))

        # try to solve with additional info
        # solve with only one cell as new info
        line.solve(
            board,
            row_indexes=(pos.row_index,),
            column_indexes=(pos.column_index,))

        return True, before_contradiction

    def _new_jobs_from_solution(self, cell_state, previous_state, is_contradiction):
        board = self.board

        # evaluate generator
        changed = list(board.changed(previous_state))
        assumption = cell_state.color
        log_contradiction = '(not) ' if is_contradiction else ''
        LOG.info('Changed %d cells with %s%s assumption',
                 len(changed), log_contradiction, assumption)

        # add the neighbours of the changed cells into jobs
        for pos in changed:
            for neighbour in board.unsolved_neighbours(pos):
                yield neighbour, 1

        # add the neighbours of the selected cell into jobs
        for neighbour in board.unsolved_neighbours(cell_state.position):
            yield neighbour, 0

    def _set_probe(self, state):
        board = self.board
        is_contradiction, prev_state = self.probe(state, rollback=False, force=True)

        if is_contradiction:
            raise NonogramError('Real contradiction was found: %s' % (state,))

        if prev_state is None:
            LOG.warning("The probe for state '%s' does not return anything new", state)
            return ()

        if board.is_solved_full:
            self._add_solution()
            return ()

        return self._new_jobs_from_solution(state, prev_state, is_contradiction)

    def _solve_jobs(self, jobs, refill=False):
        """
        Given a board and a list of jobs try to solve that board
        using the jobs as probes.
        If `refill` specified, solve in several rounds,
        until all the contradictions disappear.

        Return the number of contradictions found and
        list of the best candidates for the tree-based search
        """

        counter, counter_found = 0, 0
        rates = dict()

        board = self.board

        processed_after_refill = set()
        processed_before_contradiction = set()

        while jobs:
            state, priority = jobs.pop_smallest()
            counter += 1
            LOG.info('Probe #%d: %s (%f)', counter, state, priority)

            # if the job is only coordinates
            # then try all the possible colors
            pos = state[:2]
            if len(state) == 2:
                assumptions = board.cell_colors(state)
            else:
                assumptions = (state.color,)

            for assumption in assumptions:
                state = CellState.from_position(pos, assumption)
                is_contradiction, info = self.probe(state)

                if info is None:
                    continue

                if is_contradiction:
                    counter_found += 1
                    if board.is_solved_full:
                        self._add_solution()
                        return counter_found, None

                    for new_job, priority in self._new_jobs_from_solution(
                            state, info, is_contradiction):
                        jobs[new_job] = priority

                    # save all the jobs that already processed
                    processed_before_contradiction = set(processed_after_refill)
                else:
                    rates[state] = (info, priority)

            if not refill:
                continue

            # we have work to do!
            if jobs:
                processed_after_refill.add(pos)
            elif processed_before_contradiction:
                LOG.warning('No more jobs. Refill all the jobs processed before '
                            'the last found contradiction (%s)',
                            len(processed_before_contradiction))
                refill_processed = self._get_all_unsolved_jobs(
                    choose_from_cells=processed_before_contradiction)
                for new_job, priority in iteritems(refill_processed):
                    jobs[new_job] = priority

                processed_after_refill -= processed_before_contradiction
                processed_before_contradiction = set()
                counter = 0

        return counter_found, self._probes_from_rates(rates)

    def _add_solution(self):
        # force to check the board
        line.solve(self.board, contradiction_mode=True)
        self.board.add_solution()

    def _probes_from_rates(self, rates):
        jobs_with_rates = defaultdict(dict)

        for cell_state, (rate, priority) in iteritems(rates):
            pos = cell_state.position
            color = cell_state.color
            if self.board.cell_solved(pos):
                continue

            # the more priority the less desired that job
            # priority is in the range [0, 8]
            if ADJUST_RATE:
                rate += (10 - priority)
            # if rate > jobs_with_rates.get(job, 0):
            jobs_with_rates[pos][color] = rate

        max_rate = {pos: max(v.values()) for pos, v in iteritems(jobs_with_rates)}
        # the biggest rate appears first
        best = sorted(iteritems(max_rate), key=lambda x: x[1], reverse=True)
        if FEW_COLORS_FIRST:
            best = sorted(best, key=lambda x: len(jobs_with_rates[x[0]]))
        LOG.debug('\n'.join(map(str, best)))

        jobs = []
        for pos, max_rate in best:
            colors = sorted(iteritems(jobs_with_rates[pos]), key=lambda x: x[1], reverse=True)
            for color, rate in colors:
                jobs.append(CellState.from_position(pos, color))

        return tuple(jobs)

    def _get_all_unsolved_jobs(self, choose_from_cells=None):
        board = self.board

        if choose_from_cells is None:
            # add every cell
            choose_from_cells = product(range(board.height), range(board.width))

        probe_jobs = PriorityDict()

        for pos in choose_from_cells:
            pos = CellPosition(*pos)
            if board.cell_solved(pos):
                continue

            no_unsolved = len(list(board.unsolved_neighbours(pos)))

            # if no_unsolved >= 4 and skip_low_rated:
            #     continue

            row_rate = board.row_solution_rate(pos.row_index)
            column_rate = board.column_solution_rate(pos.column_index)
            cell_rate = row_rate + column_rate

            probe_jobs[pos] = 4 - cell_rate + no_unsolved

        return probe_jobs

    def _solve_without_search(self, to_the_max=False):
        """
        Do the one round of solving with contradictions.
        Returns the number of contradictions found.

        Based on https://www.cs.bgu.ac.il/~benr/nonograms/
        """

        probe_jobs = self._get_all_unsolved_jobs()
        return self._solve_jobs(probe_jobs, refill=to_the_max)

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

        found_contradictions, best_candidates = self._solve_without_search(to_the_max=True)
        current_solution_rate = board.solution_rate
        LOG.warning('Contradictions (found %d): %f',
                    found_contradictions, current_solution_rate)

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

        search_directions = deque(states)

        unconditional = False
        search_counter = 0
        save = board.make_snapshot()
        try:
            while search_directions:
                total_number_of_directions = len(search_directions)
                state = search_directions.popleft()
                search_counter += 1

                if self._limits_reached(depth):
                    return True

                if state in path:
                    continue

                assumption = state.color
                pos = state.position
                cell_colors = board.cell_colors(pos)

                if assumption not in cell_colors:
                    LOG.warning("The assumption '%s' is already expired. "
                                "Possible colors for %s are %s",
                                assumption, pos, cell_colors)
                    continue

                if len(cell_colors) == 1:
                    LOG.warning("Only one color for cell '%s' left: %s. Solve it unconditionally",
                                pos, assumption)
                    assert assumption == tuple(cell_colors)[0]
                    if unconditional:
                        LOG.warning(
                            "The board does not change since the last unconditional solving, skip.")
                        continue

                    try:
                        self._solve_without_search()
                        unconditional = True
                    except NonogramError:
                        # the whole `path` branch of a search tree is a dead end
                        LOG.error(
                            "The last possible color '%s' for the cell '%s' "
                            "lead to the contradiction. "
                            "The path %s is invalid", assumption, pos, path)
                        # self._add_search_result(path, False)
                        return False

                    # rate = board.solution_rate
                    # self._add_search_result(path, rate)
                    if board.is_solved_full:
                        self._add_solution()
                        LOG.warning(
                            "The only color '%s' for the cell '%s' lead to full solution. "
                            "No need to traverse the path %s anymore", assumption, pos, path)
                        return True
                    continue

                full_path = path + (state,)
                if self._is_explored(full_path):
                    LOG.info('The path %s already explored', full_path)
                    continue

                unconditional = False
                rate = board.solution_rate
                guess_save = board.make_snapshot()
                try:
                    LOG.warning('Trying state (%d/%d): %s (depth=%d, rate=%.4f, previous=%s)',
                                search_counter, total_number_of_directions,
                                state, depth, rate, path)
                    self._add_search_result(path, rate)
                    success = self._try_state(state, path)
                    # is_solved = board.is_solved_full
                finally:
                    board.restore(guess_save)
                    self._set_explored(full_path)

                if not success:
                    # TODO: add backjumping here
                    try:
                        LOG.warning(
                            "Unset the color %s for cell '%s'. Solve it unconditionally",
                            assumption, pos)
                        board.unset_state(state)
                        self._solve_without_search()
                        unconditional = True
                    except ValueError:
                        # the whole `path` branch of a search tree is a dead end
                        LOG.error(
                            "The last possible color '%s' for the cell '%s' "
                            "lead to the contradiction. "
                            "The path %s is invalid", assumption, pos, path)
                        # self._add_search_result(path, False)
                        return False

                    # rate = board.solution_rate
                    # self._add_search_result(path, rate)
                    if board.is_solved_full:
                        self._add_solution()
                        LOG.warning(
                            "The negation of color '%s' for the cell '%s' lead to full solution. "
                            "No need to traverse the path %s anymore", assumption, pos, path)
                        return True

                if not success or board.is_solved_full:
                    # immediately try the other colors as well
                    # if all of them goes to the dead end,
                    # then the parent path is a dead end
                    states_to_try = []
                    for color in cell_colors:
                        if color == assumption:
                            continue

                        states_to_try.append(CellState.from_position(pos, color))

                    # if all(self._is_explored(path + (state,)) for state in states_to_try):
                    #     LOG.error('All other colors (%s) of cell %s already explored',
                    #               states_to_try, cell)
                    #     return True

                    for state in states_to_try:
                        if state not in search_directions:
                            search_directions.appendleft(state)

        finally:
            # do not restore the solved cells on a root path - they are really solved!
            if path:
                board.restore(save)
                self._set_explored(path)

        return True
