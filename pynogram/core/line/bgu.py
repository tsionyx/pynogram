# -*- coding: utf-8 -*-
"""
Dynamic programming algorithm to solve nonograms (using recursion)

See details:
https://www.cs.bgu.ac.il/~benr/nonograms/
"""

from __future__ import unicode_literals

import logging
from collections import defaultdict
from functools import reduce
from itertools import product

from six.moves import range, zip

from pynogram.core.color import ColorBlock
from pynogram.core.common import (
    UNKNOWN, BOX, SPACE, SPACE_COLORED,
    BlottedBlock,
    partial_sums,
    slack_space,
)
from pynogram.core.line.base import (
    BaseLineSolver,
    TrimmedSolver,
    NonogramError,
)
from pynogram.utils.iter import (
    expand_generator,
    max_continuous_interval,
)
from pynogram.utils.other import (
    two_powers, from_two_powers,
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

        self._reset_solutions_table()

    def _reset_solutions_table(self):
        positions = len(self.line)
        job_size = len(self.description) + 1
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
        min_indexes = [s - 1 for s in partial_sums(blocks, colored=False)]
        return [0] + min_indexes

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
        min_indexes = [s - 1 for s in partial_sums(blocks, colored=True)]
        return [0] + min_indexes

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


class BlottedSolver(BaseLineSolver):
    """Some additional routines to help solve blotted puzzles"""

    @classmethod
    def is_solved(cls, description, line):
        """
        Whether the line already solved.
        Do not solve if so, since the blotted algorithm is computationally heavy.
        """
        raise NotImplementedError()

    @classmethod
    def _blotted_combinations(cls, description, line):
        """
        Generate all the possible combinations of blotted blocks sizes.
        The routine suggests that every size can be in range [0..max_sum]
        """

        blocks_number = sum(1 for block in description
                            if cls._is_blotted(block))
        max_sum = slack_space(len(line), description)

        valid_range = range(max_sum + 1)
        for combination in product(valid_range, repeat=blocks_number):
            if sum(combination) <= max_sum:
                yield combination

    @classmethod
    def _is_blotted(cls, block):
        raise NotImplementedError()

    @classmethod
    def _update_block(cls, current, increase):
        raise NotImplementedError()

    @classmethod
    def _single_color(cls, values):
        raise NotImplementedError()

    @classmethod
    def merge_solutions(cls, one, other=None):
        """Merge solutions from different description suggestions"""
        if other is None:
            return one

        LOG.debug('Merging two solutions: %r and %r', one, other)
        return [cls._single_color(set(cells))
                for cells in zip(one, other)]

    @classmethod
    def solve(cls, description, line):
        """Solve the line (or use cached value)"""
        if not line:
            return line

        if not BlottedBlock.how_many(description):
            return super(BlottedSolver, cls).solve(description, line)

        if cls.is_solved(description, line):
            LOG.info('No need to solve blotted line: %r', line)
            return line

        blotted_desc, line = tuple(description), tuple(line)
        LOG.warning('Solving line %r with blotted description %r', line, blotted_desc)

        blotted_positions = [index for index, block in enumerate(blotted_desc)
                             if cls._is_blotted(block)]

        # prevent from incidental changing
        min_desc = tuple(BlottedBlock.replace_with_1(blotted_desc))

        solution = None
        for index, combination in enumerate(cls._blotted_combinations(
                blotted_desc, line)):

            current_description = list(min_desc)
            for pos, block_size in zip(blotted_positions, combination):
                block = current_description[pos]
                current_description[pos] = cls._update_block(block, block_size)

            LOG.debug('Trying %i-th combination %r', index, current_description)

            try:
                solved = tuple(super(BlottedSolver, cls).solve(current_description, line))
            except NonogramError:
                LOG.debug('Combination %r is invalid for line %r', current_description, line)
            else:
                solution = cls.merge_solutions(solved, solution)
                LOG.debug('Merged solution: %s', solution)
                if tuple(solution) == line:
                    LOG.warning('The combination %r (description=%r) is valid but '
                                'brings no new information. Stopping the combinations search.',
                                combination, current_description)
                    break

        if not solution:
            raise NonogramError('Cannot solve with blotted clues {!r}'.format(blotted_desc))

        LOG.info('United solution from all combinations: %r', solution)
        assert len(solution) == len(line)
        return tuple(solution)


class BguBlottedSolver(BlottedSolver, BguSolver):
    """
    Slightly modified algorithm to solve with blotted descriptions
    """

    @classmethod
    def is_solved(cls, description, line):
        if UNKNOWN in line:
            return False

        return BlottedBlock.matches(description, line)

    @classmethod
    def calc_block_sum(cls, blocks):
        blocks = BlottedBlock.replace_with_1(blocks)
        return super(BguBlottedSolver, cls).calc_block_sum(blocks)

    @classmethod
    def _is_blotted(cls, block):
        return block == BlottedBlock

    @classmethod
    def _update_block(cls, current, increase):
        return current + increase

    @classmethod
    def _single_color(cls, values):
        if len(values) > 1:
            return UNKNOWN

        return tuple(values)[0]


class BguColoredBlottedSolver(TrimmedSolver, BlottedSolver, BguColoredSolver):
    """
    Slightly modified algorithm to solve colored lines with blotted descriptions
    """

    @classmethod
    def is_solved(cls, description, line):
        if any(len(two_powers(cell)) > 1 for cell in line):
            return False

        return BlottedBlock.matches(description, line)

    @classmethod
    def calc_block_sum(cls, blocks):
        blocks = BlottedBlock.replace_with_1(blocks)
        return super(BguColoredBlottedSolver, cls).calc_block_sum(blocks)

    @classmethod
    def _is_blotted(cls, block):
        return block.size == BlottedBlock

    @classmethod
    def _update_block(cls, current, increase):
        return ColorBlock(current.size + increase, current.color)

    @classmethod
    def _single_color(cls, values):
        return from_two_powers(values)

    @classmethod
    @expand_generator
    def block_ranges_left(cls, description, line):
        """
        Shift the blocks to the left and find valid start positions
        """
        # line_colors = set(block.color for block in description)
        allowed_colors_positions = defaultdict(list)
        for index, cell in enumerate(line):
            for single_color in two_powers(cell):
                allowed_colors_positions[single_color].append(index)

        min_start_indexes = cls.calc_block_sum(description)[1:]
        LOG.debug(min_start_indexes)

        for block_index, block in enumerate(description):
            color = block.color
            # do not do `zip(desc, min_indexes)` because min_indexes changes
            min_index = min_start_indexes[block_index]

            rang = [index for index in allowed_colors_positions[color]
                    if index >= min_index]

            if not rang:
                raise NonogramError('The #{} block ({}) cannot be placed'.format(
                    block_index, block))

            min_index_shift = min(rang) - min_index
            if min_index_shift > 0:
                LOG.info('Minimum starting index for block #%i (%r) updated: %i --> %i',
                         block_index, block, min_index, min_index + min_index_shift)

                min_start_indexes[block_index:] = [
                    i + min_index_shift for i in min_start_indexes[block_index:]]

            yield rang

        LOG.debug(min_start_indexes)

    @classmethod
    @expand_generator
    def block_ranges(cls, description, line):
        """
        For every block in the description produce a valid cells range
        it can cover using partially solved line
        """
        left_ranges = cls.block_ranges_left(description, line)
        right_ranges = reversed(cls.block_ranges_left(
            tuple(reversed(description)), tuple(reversed(line))))

        for left, right in zip(left_ranges, right_ranges):
            right = [len(line) - 1 - i for i in reversed(right)]
            yield sorted(set(left) & set(right))

    @classmethod
    def _blotted_combinations(cls, description, line):
        """
        Generate all the possible combinations of blotted blocks sizes.
        The routine calculates the maximum possible block size
        by analyzing the line and finding valid positions range for every block.
        """

        max_sum = slack_space(len(line), description)

        sizes = []
        ranges = cls.block_ranges(description, line)

        for block, rang in zip(description, ranges):
            LOG.info('%s --> %s', block, rang)

        for block, rang in zip(description, ranges):
            if cls._is_blotted(block):
                max_block_size = max_continuous_interval(rang)

                # the algorithm already count the block as minimum size=1
                # max_block_size -= 1

                valid_range = tuple(range(max_block_size))
                sizes.append(valid_range)

        total_variations = tuple(map(len, sizes))
        LOG.warning('Go through %i combinations: %s',
                    reduce(lambda x, y: x * y, total_variations), total_variations)

        for combination in product(*sizes):
            if sum(combination) <= max_sum:
                yield combination
