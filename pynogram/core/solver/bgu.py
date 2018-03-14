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
        positions = line_size + 1
        self.job_size = len(clue) + 1
        self.sol = [None] * (self.job_size * positions)

    @classmethod
    def solve(cls, clue, line):
        """Solve the line (or use cached value)"""
        clue, line = tuple(clue), tuple(line)

        # pylint: disable=no-member
        solved = cls.solutions_cache.get((clue, line))
        if solved is not None:
            if solved is False:
                raise NonogramError("Failed to solve line '{}' with clues '{}' (cached)".format(
                    line, clue))

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
            cls.solutions_cache.save((clue, line), False)
            raise NonogramError("Failed to solve line '{}' with clues '{}'".format(line, clue))

    def try_solve(self):
        """
        The main solver function.
        Return whether the line is solvable.
        """
        position, block = len(self.line) - 1, len(self.blocks)
        return self.get_sol(position, block)

    def get_mat_index(self, row, col):
        """Convert the 2D matrix address into a 1D address"""
        return row * self.job_size + col

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

    def fill_matrix_top_down(self, position, block):
        """
        fills the solution matrix in a top-down
        using memoization to determine if a recursive call has already been calculated
        :param position: position of cell we're currently trying to fill
        :param block: current block of the cell
        """

        if (position < 0) or (block < 0):
            return

        # if we have too many blocks to fit this line segment
        # we can stop the recursion and return false
        if position < self.block_sums[block]:
            self.set_sol(position, block, False)
            return

        # base case
        if position == 0:  # reached the end of the line
            if (block == 0) and (self.line[position] != BOX):
                self.set_sol(position, block, True)
                self.set_line_cell(position, SPACE)
            else:
                self.set_sol(position, block, False)

            return

        # finished filling all blocks (can still fill whitespace)
        if block == 0:
            if (self.line[position] != BOX) and self.get_sol(position - 1, block):
                self.set_sol(position, block, True)
                self.set_line_cell(position, SPACE)
            else:
                self.set_sol(position, block, False)

            return

        # recursive case
        if self.line[position] == BOX:  # current cell is BOX
            self.set_sol(position, block, False)  # can't place a block if the cell is black

        else:  # current cell is either white or unknown
            white_ans = self.get_sol(position - 1, block)  # set cell white and continue

            prev_block_size = self.blocks[block - 1]
            # set cell white, place the current block and continue

            black_ans = False
            if self.can_place_block(position - prev_block_size, prev_block_size):
                black_ans = self.get_sol(position - prev_block_size - 1, block - 1)

            if not white_ans and not black_ans:
                self.set_sol(position, block, False)  # no solution
                return

            if white_ans:
                self.set_line_cell(position, SPACE)
                self.set_sol(position, block, True)

            if black_ans:  # both space and block
                self.set_line_block(position - prev_block_size, position)
                self.set_sol(position, block, True)

    def can_place_block(self, position, length):
        """
        check if we can place a block of a specific length in this position
        we check that our partial solution does not negate the line's partial solution
        :param position:  position to place block at
        :param length:  length of block
        """
        if position < 0:
            return False

        # if no negations were found, the block can be placed
        return SPACE not in self.line[position: position + length]

    def set_line_cell(self, position, value):
        """sets a cell in the solution matrix"""

        cell = self.solved_line[position]
        if cell == BOTH_COLORS:
            pass
        elif cell == UNKNOWN:
            self.solved_line[position] = value
        elif cell != value:
            self.solved_line[position] = BOTH_COLORS

    def set_line_block(self, start_pos, end_pos):
        """
        sets a block in the solution matrix. all cells are painted black,
        except the end_pos which is white.
        :param start_pos: position to start painting
        :param end_pos: position to stop painting
        """

        # set blacks
        for i in range(start_pos, end_pos):
            self.set_line_cell(i, BOX)

        self.set_line_cell(end_pos, SPACE)

    def set_sol(self, position, block, value):
        """
        sets a value in the solution matrix
        so we wont calculate this value recursively anymore
        """
        if position < 0:
            return

        self._set_sol(position, block, value)

    def _set_sol(self, position, block, value):
        self.sol[self.get_mat_index(position, block)] = value

    def get_sol(self, position, block):
        """
        gets the value from the solution matrix
        if the value is missing, we calculate it recursively
        """

        if position == -1:
            # finished placing the last block, exactly at the beginning of the line.
            return block == 0

        if self._get_sol(position, block) is None:
            self.fill_matrix_top_down(position, block)

        return self._get_sol(position, block)

    def _get_sol(self, position, block):
        return self.sol[self.get_mat_index(position, block)]
