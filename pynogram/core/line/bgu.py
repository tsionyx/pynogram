# -*- coding: utf-8 -*-
"""
Dynamic programming algorithm to solve nonograms (using recursion)

See details:
https://www.cs.bgu.ac.il/~benr/nonograms/
"""

from __future__ import unicode_literals

import logging

from six.moves import range

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE,
)
from pynogram.core.line.base import (
    BaseLineSolver,
    NonogramError,
)

LOG = logging.getLogger(__name__)

# dummy constant
BOTH_COLORS = -1


class BguSolver(BaseLineSolver):
    """
    The solver uses recursion to solve the line to the most
    """

    def __init__(self, description, line):
        super(BguSolver, self).__init__(description, line)
        self.block_sums = self.calc_block_sum(description)

        # define the internal representation of a line to be one cell larger then the original
        # this is done to avoid an edge case later in our recursive formula
        self.line = list(line) + [UNKNOWN]
        self.solved_line = list(self.line)

        positions = len(self.line)
        job_size = len(description) + 1
        self.sol = [[None] * positions for _ in range(job_size)]

    def _solve(self):
        if self.try_solve():
            solved = self.solved_line[:-1]
            solved = tuple(UNKNOWN if cell == BOTH_COLORS else cell for cell in solved)
            return solved

        raise NonogramError('Bad line')

    def try_solve(self):
        """
        The main solver function.
        Return whether the line is solvable.
        """
        position, block = len(self.line) - 1, len(self.description)
        return self.get_sol(position, block)

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
        Calculate the solution for line[:position+1]
        in respect to description[:block]

        :param position: position of cell we're currently trying to fill
        :param block: current block number
        :return: whether the segment of line solvable
        """

        if (position < 0) or (block < 0):
            return None

        # too many blocks left to fit this line segment
        if position < self.block_sums[block]:
            return False

        # base case
        if position == 0:  # reached the end of the line
            if (block == 0) and (self.line[position] != BOX):
                self.add_cell_color(position, SPACE)
                return True

            return False

        # finished filling all blocks (can still fill whitespace)
        if block == 0:
            if (self.line[position] != BOX) and self.get_sol(position - 1, block):
                self.add_cell_color(position, SPACE)
                return True

            return False

        # recursive case
        if self.line[position] == BOX:  # current cell is BOX
            return False  # can't place a block if the cell is black

        # current cell is either white or unknown
        white_ans = self.get_sol(position - 1, block)  # set cell white and continue

        prev_block_size = self.description[block - 1]
        # set cell white, place the current block and continue

        black_ans = False
        if self.can_place_block(position - prev_block_size, prev_block_size):
            black_ans = self.get_sol(position - prev_block_size - 1, block - 1)

        if not white_ans and not black_ans:
            return False  # no solution

        if white_ans:  # only space
            self.add_cell_color(position, SPACE)

        if black_ans:  # both space and block
            self.set_line_block(position - prev_block_size, position)

        return True

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

    def add_cell_color(self, position, value):
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
            self.add_cell_color(i, BOX)

        self.add_cell_color(end_pos, SPACE)

    def set_sol(self, position, block, value):
        """
        sets a value in the solution matrix
        so we wont calculate this value recursively anymore
        """
        if position < 0:
            return

        self.sol[block][position] = value

    def get_sol(self, position, block):
        """
        gets the value from the solution matrix
        if the value is missing, we calculate it recursively
        """

        if position == -1:
            # finished placing the last block, exactly at the beginning of the line.
            return block == 0

        can_be_solved = self.sol[block][position]  # self._get_sol(position, block)
        if can_be_solved is None:
            can_be_solved = self.fill_matrix_top_down(position, block)
            if can_be_solved is not None:
                self.set_sol(position, block, can_be_solved)

        return can_be_solved
