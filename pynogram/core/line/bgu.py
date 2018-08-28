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
    UNKNOWN, BOX, SPACE, SPACE_COLORED,
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
        self._additional_space = self._set_additional_space()

        self.block_sums = self.calc_block_sum(description)
        self.solved_line = list(self.line)

        positions = len(self.line)
        job_size = len(description) + 1
        self.sol = [[None] * positions for _ in range(job_size)]

    def _set_additional_space(self):
        """
        Define the internal representation of a line to be one cell larger then the original.
        This is done to avoid an edge case later in our recursive formula.
        """
        if self.line[-1] != SPACE:
            self.line = list(self.line) + [SPACE]
            return True

        return False

    def _solve(self):
        if self.try_solve():
            solved = self.solved_line
            if self._additional_space:
                solved = solved[:-1]
            solved = (UNKNOWN if cell == BOTH_COLORS else cell for cell in solved)
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
            res.append(blocks[0] - 1)

        for block in blocks[1:]:
            res.append(res[-1] + block + 1)

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

        # recursive case
        if self.line[position] == BOX:  # current cell is BOX
            return False  # can't place a block if the cell is black

        # base case
        if position == 0:  # reached the end of the line
            if block == 0:
                self.add_cell_color(position, SPACE)
                return True

            return False

        # current cell is either white or unknown
        white_ans = self.get_sol(position - 1, block)

        # block == 0 means we finished filling all the blocks (can still fill whitespace)
        if block > 0:
            block_size = self.description[block - 1]

            if self.can_place_block(position - block_size, block_size):
                black_ans = self.get_sol(position - block_size - 1, block - 1)
                if black_ans:
                    # set cell white, place the current block and continue
                    self.set_line_block(position - block_size, position)
                    return True

        if white_ans:
            # set cell white and continue
            self.add_cell_color(position, SPACE)
            return True

        return False  # no solution

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

            # self.set_sol(position, block, can_be_solved)
            self.sol[block][position] = can_be_solved

        return can_be_solved


UNKNOWN_COLORED = 0


class BguColoredSolver(BguSolver):
    """
    The BGU solver for colored puzzles
    """

    def __init__(self, description, line):
        super(BguColoredSolver, self).__init__(description, line)
        self.solved_line = [UNKNOWN_COLORED] * len(self.line)

    def _set_additional_space(self):
        """Additional space is useless in colored"""
        return False

    def _solve(self):
        if self.try_solve():
            solved = self.solved_line  # [:-1]
            return solved

        raise NonogramError('Bad line')

    @classmethod
    def calc_block_sum(cls, blocks):
        res = [0]

        if blocks:
            res.append(blocks[0].size - 1)

        for i, block in enumerate(blocks[1:], 1):
            size, color = block
            prev = res[-1]
            if blocks[i - 1].color == color:
                # at least one space + block size
                current = prev + 1 + size
            else:
                # only block size, can be no delimited space
                current = prev + size

            res.append(current)

        return res

    def _precede_with_space(self, j):
        current_color = self.description[j].color

        if j > 0:
            prev_color = self.description[j - 1].color
            if prev_color == current_color:
                return True

        return False

    def _trail_with_space(self, block):
        current_color = self.description[block - 1].color

        if block < len(self.description):
            next_color = self.description[block].color
            if next_color == current_color:
                return True

        return False

    def fill_matrix_top_down(self, position, block):
        if (position < 0) or (block < 0):
            return None

        # too many blocks left to fit this line segment
        if position < self.block_sums[block]:
            return False

        # recursive case
        # if self.line[position] == BOX:  # current cell is BOX
        #     return False  # can't place a block if the cell is black

        # base case
        if position == -1:  # reached the end of the line
            if block == 0:
                return True

            return False

        white_ans = False
        if self.can_be_space(position):
            # current cell is either white or unknown
            white_ans = self.get_sol(position - 1, block)
            if white_ans:
                # set cell white and continue
                self.add_cell_color(position, SPACE_COLORED)

        color_ans = False
        # block == 0 means we finished filling all the blocks (can still fill whitespace)
        if block > 0:
            block_size, current_color = self.description[block - 1]
            trailing_space = self._trail_with_space(block)
            if trailing_space:
                block_size += 1

            # (position-block_size, position]
            if self.can_place_color(position - block_size + 1, position,
                                    current_color, trailing_space=trailing_space):
                color_ans = self.get_sol(position - block_size, block - 1)
                if color_ans:
                    # set cell white, place the current block and continue
                    self.set_color_block(position - block_size + 1, position,
                                         current_color, trailing_space=trailing_space)

        return color_ans or white_ans

    def can_be_space(self, position):
        """The symbol at given position can be a space"""
        return bool(self.line[position] & SPACE_COLORED)

    def can_place_color(self, position, end_pos, color, trailing_space=True):
        """
        check if we can place a colored block of a specific length in this position
        we check that our partial solution does not negate the line's partial solution
        :param position:  position to place block at
        :param end_pos:   position to stop placing the block
        :param color:     color number
        :param trailing_space: whether to check for trailing space
        """
        if position < 0:
            return False

        if trailing_space:
            if not self.can_be_space(end_pos):
                return False
        else:
            end_pos += 1

        # the color can be placed in every cell
        return all(cell & color
                   for cell in self.line[position: end_pos])

    def add_cell_color(self, position, value):
        self.solved_line[position] |= value

    def set_color_block(self, start_pos, end_pos, color, trailing_space=True):
        """
        sets a block in the solution matrix. all cells are painted black,
        except the end_pos which is white.
        :param start_pos: position to start painting
        :param end_pos: position to stop painting
        :param color:     color number
        :param trailing_space: whether to set the trailing space
        """

        if trailing_space:
            self.add_cell_color(end_pos, SPACE_COLORED)
        else:
            end_pos += 1

        # set blacks
        for i in range(start_pos, end_pos):
            self.add_cell_color(i, color)
