# -*- coding: utf-8 -*-
"""
Dynamic programming algorithm to solve nonograms (using recursion)

See details:
https://www.cs.bgu.ac.il/~benr/nonograms/
"""

from __future__ import unicode_literals

import logging

from six import add_metaclass
from six.moves import range

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE
)
from pynogram.core.solver.common import (
    LineSolutionsMeta,
    NonogramError)

LOG = logging.getLogger(__name__)

# dummy constant
BOTH_COLORS = -1


@add_metaclass(LineSolutionsMeta)
class BguSolver(object):
    """
    The solver uses recursion to solve the line to the most
    """

    def __init__(self, clue, line):
        self.blocks = clue
        self.block_sums = self.calc_block_sum(clue)

        # define the internal representation of a line to be
        # one cell larger then the original
        # this is done to avoid an edge case later in our recursive formula
        self.line = list(line) + [UNKNOWN]
        self.solved_line = list(self.line)

        line_size = len(line)
        mat_rows = line_size + 1
        self.mat_cols = int(line_size / 2) + 2
        self.memoized = [False] * (mat_rows * self.mat_cols)
        self.sol = [None] * (mat_rows * self.mat_cols)
        self.num_both_color_cells = 0

    @classmethod
    def solve(cls, clue, line):
        """Solve the line (or use cached value)"""
        clue, line = tuple(clue), tuple(line)

        # pylint: disable=no-member
        solved = cls.solutions_cache.get((clue, line))
        if solved is not None:
            assert len(solved) == len(line)
            return solved

        solver = BguSolver(clue, line)
        if solver.try_solve():
            solved = solver.solved_line[:-1]
            solved = tuple(UNKNOWN if cell == BOTH_COLORS else cell for cell in solved)

            # pylint: disable=no-member
            cls.solutions_cache.save((clue, line), solved)
            return solved
        else:
            raise NonogramError("Failed to solve line '{}' with clues '{}'".format(line, clue))

    def try_solve(self):
        """
        The main solver function.
        Return whether the line is solvable.
        """
        position, job = len(self.line) - 1, len(self.blocks)
        self.fill_matrix_top_down(position, job)
        return self.sol[self.get_mat_index(position, job)]

    def get_mat_index(self, row, col):
        """Convert the 2D matrix address into a 1D address"""
        return row * self.mat_cols + col

    @classmethod
    def calc_block_sum(cls, blocks):
        """
        calculates the partial sum of the blocks.
        this is used later to determine if we can fit some blocks in the space left on the line
        """
        res = [0]

        if blocks:
            res.append(blocks[0])

        for i, block in enumerate(blocks[1:]):
            res.append(res[i + 1] + block)

        for i in range(1, len(res)):
            res[i] += i - 2

        return res

    def fill_matrix_top_down(self, position, job):
        """
        fills the solution matrix in a top-down
        using memoization to determine if a recursive call has already been calculated
        :param position: position of cell we're currently trying to fill
        :param job: current job of the cell
        """

        if (position < 0) or (job < 0):
            return

        # if we have too many jobs to fit this line segment
        # we can stop the recursion and return false
        if position < self.block_sums[job]:
            self.set_sol(position, job, False)
            return

        # base case
        if position == 0:  # reached the end of the line
            if (job == 0) and (self.line[position] != BOX):
                self.set_sol(position, job, True)
                self.set_line_cell(position, SPACE)
            else:
                self.set_sol(position, job, False)

            return

        # finished filling all jobs (can still fill whitespace)
        if job == 0:
            if (self.line[position] != BOX) and self.get_sol(position - 1, job):
                self.set_sol(position, job, True)
                self.set_line_cell(position, SPACE)
            else:
                self.set_sol(position, job, False)

            return

        # recursive case
        if self.line[position] == BOX:  # current cell is BOX
            self.set_sol(position, job, False)  # can't place a block if the cell is black

        else:  # current cell is either white or unknown
            white_ans = self.get_sol(position - 1, job)  # set cell white and continue

            # set cell white, place the current block and continue
            black_ans = (self.can_place_block(position - self.blocks[job - 1],
                                              self.blocks[job - 1]) and
                         self.get_sol(position - self.blocks[job - 1] - 1, job - 1))

            if white_ans:
                self.set_line_cell(position, SPACE)
                if black_ans:  # both space and block
                    self.set_sol(position, job, True)
                    self.set_line_block(position - self.blocks[job - 1], position)
                else:  # space, but not block
                    self.set_sol(position, job, True)

            elif black_ans:  # block, but not space
                self.set_sol(position, job, True)
                self.set_line_block(position - self.blocks[job - 1], position)
            else:
                self.set_sol(position, job, False)  # no solution

    def can_place_block(self, position, length):
        """
        check if we can place a block of a specific length in this position
        we check that our partial solution does not negate the line's partial solution
        :param position:  position to place block at
        :param length:  length of block
        :return: "true" if block can be placed, "false otherwise
        """
        if position < 0:
            return False

        for i in range(length):
            if self.line[position + i] == 0:
                return False

        # if no negations were found, the block can be placed
        return True

    def set_line_cell(self, position, value):
        """sets a cell in the solution matrix"""

        cell = self.solved_line[position]
        if cell == UNKNOWN:
            self.solved_line[position] = value
        elif cell == BOTH_COLORS:
            pass
        elif cell != value:
            LOG.info('orig cell color: %s', self.solved_line[position])
            LOG.info('setting cell %s as both colors', position)
            self.solved_line[position] = BOTH_COLORS
            self.num_both_color_cells += 1

    def set_line_block(self, start_pos, end_pos):
        """
        sets a block in the solution matrix. all cells are painted black,
        except the end_pos which is white.
        :param start_pos: position to start painting
        :param end_pos: position to stop painting
        """

        # set blacks
        for i in range(start_pos, end_pos):
            cell = self.solved_line[i]
            if cell == UNKNOWN:
                self.solved_line[i] = BOX
            elif cell == SPACE:
                LOG.info('orig cell color: %s', self.solved_line[i])
                LOG.info('setting cell %s as both colors', i)
                self.solved_line[i] = BOTH_COLORS
                self.num_both_color_cells += 1

        cell = self.solved_line[end_pos]
        if cell == UNKNOWN:
            self.solved_line[end_pos] = SPACE
        elif cell == BOX:
            LOG.info('orig cell color: %s', self.solved_line[end_pos])
            LOG.info('setting cell %s as both colors', end_pos)
            self.solved_line[end_pos] = BOTH_COLORS
            self.num_both_color_cells += 1

    def set_sol(self, position, job, value):
        """
        sets a value in the solution matrix
        also sets cell as TRUE in the memoization matrix
        (so we wont calculate this value recursively anymore)
        """
        if position < 0:
            return

        self.sol[self.get_mat_index(position, job)] = value
        self.memoized[self.get_mat_index(position, job)] = True

    def get_sol(self, position, job):
        """
        gets the value from the solution matrix
        if the value is not memoized yet, we calculate it recursively
        :return: value of pos,job in the solution matrix
        """

        if position == -1:
            # finished placing the last block, exactly at the beginning of the line.
            return job == 0

        if not self.memoized[self.get_mat_index(position, job)]:
            self.fill_matrix_top_down(position, job)

        return self.sol[self.get_mat_index(position, job)]
