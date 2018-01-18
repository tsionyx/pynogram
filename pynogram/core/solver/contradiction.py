# -*- coding: utf-8 -*
"""Define nonogram solver that uses contradictions"""

from __future__ import unicode_literals, print_function

import logging
import os
import time
from copy import deepcopy
from itertools import cycle

from pynogram.core.board import ColoredBoard
from pynogram.core.solver import line
from pynogram.core.solver.base import cache_hit_rate
from pynogram.core.solver.common import NonogramError

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


def try_contradiction(board, row_index, column_index,
                      assumption, propagate=True):
    """
    Try to find if the given cell can be in an assumed state.
    If the contradiction is found, set the cell
    in an inverted state and propagate the changes if needed.
    """
    # already solved
    if board.cell_solved(board.cells[row_index][column_index]):
        return

    save = deepcopy(board.cells)
    contradiction = False
    colored = isinstance(board, ColoredBoard)

    try:
        try:
            LOG.debug('Pretend that (%i, %i) is %s',
                      row_index, column_index, assumption)
            if colored:
                if assumption not in board.cells[row_index][column_index]:
                    return
                assumption = [assumption]

            board.cells[row_index][column_index] = assumption
            line.solve(
                board,
                row_indexes=(row_index,),
                column_indexes=(column_index,),
                contradiction_mode=True)
        except NonogramError:
            LOG.debug('Contradiction', exc_info=True)
            contradiction = True
        else:
            if board.solution_rate == 1:
                LOG.warning("Found one of the solutions!")
    finally:
        # rollback solved cells
        board.cells = save
        if contradiction:
            LOG.info("Found contradiction at (%i, %i)",
                     row_index, column_index)
            board.unset_state(assumption, row_index, column_index)

            # try to solve with additional info
            if propagate:
                # solve with only one cell as new info
                line.solve(
                    board,
                    row_indexes=(row_index,),
                    column_indexes=(column_index,))


def _contradictions_round(
        board, assumption,
        propagate_on_cell=True, by_rows=True):
    """
    Solve the nonogram with contradictions
    by trying every cell and the basic `solve` method.

    :param assumption: which state to try: BOX or SPACE
    or all the possible colors for colored boards
    :param propagate_on_cell: how to propagate changes:
    after each solved cell or in the end of the row
    :param by_rows: iterate by rows (left-to-right) or by columns (top-to-bottom)
    """

    if by_rows:
        for solved_row in range(board.height):
            if board.row_solution_rate(solved_row) == 1:
                continue

            LOG.info('Trying to assume on row %i', solved_row)
            for solved_column in range(board.width):
                try_contradiction(
                    board,
                    solved_row, solved_column,
                    assumption,
                    propagate=propagate_on_cell
                )

            if not propagate_on_cell:
                # solve with only one row as new info
                line.solve(
                    board, row_indexes=(solved_row,))
    else:
        for solved_column in range(board.width):
            if board.column_solution_rate(solved_column) == 1:
                continue

            LOG.info('Trying to assume on column %i', solved_column)
            for solved_row in range(board.height):
                try_contradiction(
                    board,
                    solved_row, solved_column,
                    assumption,
                    propagate=propagate_on_cell
                )

            if not propagate_on_cell:
                # solve with only one column as new info
                line.solve(
                    board, column_indexes=(solved_column,))


def solve(
        board, propagate_on_row=False, by_rows=True):
    """
    Solve the nonogram to the most with contradictions
    and the basic `solve` method.

    :type board: Board
    :param propagate_on_row: how to propagate changes:
    in the end of the row or after each solved cell
    :param by_rows: iterate by rows (left-to-right) or by columns (top-to-bottom)
    """

    line.solve(board)
    if board.solution_rate == 1:
        board.set_solved()
        LOG.info('No need to solve with contradictions')
        return

    LOG.warning('Trying to solve using contradictions method')
    propagate_on_cell = not propagate_on_row
    board.set_solved(False)
    start = time.time()

    counter = 0
    colored = isinstance(board, ColoredBoard)

    assumptions = board.colors()  # try the different assumptions every time
    active_assumptions_rate = {state: board.solution_rate for state in assumptions}

    assumptions = cycle(assumptions)
    while active_assumptions_rate:
        assumption = next(assumptions)
        if assumption not in active_assumptions_rate:
            continue

        counter += 1
        LOG.warning('Contradiction round %i (assumption %s)', counter, assumption)

        _contradictions_round(
            board, assumption,
            propagate_on_cell=propagate_on_cell,
            by_rows=by_rows)

        if board.solution_rate > active_assumptions_rate[assumption]:
            board.solution_round_completed()

        if board.solution_rate == 1:
            break

        if board.solution_rate == active_assumptions_rate[assumption]:
            if colored:
                # stalled
                del active_assumptions_rate[assumption]
            else:
                break
        else:
            active_assumptions_rate[assumption] = board.solution_rate

    board.set_solved()
    if board.solution_rate != 1:
        LOG.warning('The nonogram is not solved full (with contradictions). '
                    'The rate is %.4f', board.solution_rate)
    LOG.info('Full solution: %.6f sec', time.time() - start)
    for method, hit_rate in cache_hit_rate().items():
        LOG.info('Cache hit rate (%s): %.4f%%', method, hit_rate * 100.0)
