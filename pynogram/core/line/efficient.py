# -*- coding: utf-8 -*-
"""
Dynamic programming algorithm to solve nonograms (using recursion)

See details in the work 'An Efficient Approach to Solving Nonograms':
https://ir.nctu.edu.tw/bitstream/11536/22772/1/000324586300005.pdf
"""

from __future__ import unicode_literals

import logging

from six.moves import zip

from pynogram.core.common import (
    UNKNOWN, BOX,
    SPACE, SPACE_COLORED,
)
from pynogram.core.line.base import (
    BaseLineSolver,
    NonogramError,
)
from pynogram.utils.other import from_two_powers

LOG = logging.getLogger(__name__)


class EfficientSolver(BaseLineSolver):
    """
    Recursive nonogram line solver.
    Adapted from the work 'An Efficient Approach to Solving Nonograms'
    """

    def __init__(self, description, line):
        super(EfficientSolver, self).__init__(description, line)

        self.minimum_lengths = self.min_lengths(self.description)
        self.additional_space = self._set_additional_space()

        self._cache_width = len(self.description) + 1
        self._fix_table = self._init_tables()
        self._paint_table = self._init_tables()

    def _init_tables(self):
        cache_height = len(self.line) + 1
        return [None] * (self._cache_width * cache_height)

    def _linear_index(self, i, j):
        return (i + 1) * self._cache_width + (j + 1)

    def _set_additional_space(self):
        space = self.empty_cell()
        if self.line[0] != space:
            self.line = (space,) + self.line
            return True
        return False

    @classmethod
    def min_lengths(cls, description):
        """
        The minimum line sizes in which can squeeze from 0 to i-th block
        """

        if not description:
            return []

        minimum_lengths = [description[0] - 1]
        for block in description[1:]:
            prev = minimum_lengths[-1]
            # at least one space + block size
            minimum_lengths.append(prev + 1 + block)

        return minimum_lengths

    def fix(self, i, j):
        """
        Verify whether blocks from 0 to (j-1)-th
        can be resided inside a substring line[:i+1]
        """

        fixable = self._fix_table[self._linear_index(i, j)]
        if fixable is None:
            fixable = self._fix(i, j)
            self._fix_table[self._linear_index(i, j)] = fixable
        return fixable

    @classmethod
    def _can_be_space(cls, cell):
        return cell in (SPACE, UNKNOWN)

    def _fix_border_conditions(self, i, j):
        if j < 0:
            assert j == -1

            if i < 0:
                return True

            # NB: improvement
            return all(map(self._can_be_space, self.line[:i + 1]))

        # reached the beginning of the line
        if i < 0:
            assert i == -1

            # no more blocks to fill
            return j < 0

        if i < self.minimum_lengths[j]:
            return False

        return None

    def _fix(self, i, j):
        """
        Determine whether S[:i+1] is fixable with respect to D[:j+1]
        :param i: line size
        :param j: block number
        """
        res = self._fix_border_conditions(i, j)
        if res is not None:
            return res

        res = self._fix0(i, j) or self._fix1(i, j)
        return res

    def _fix0(self, i, j):
        """
        Determine whether S[:i+1] is fixable with respect to D[:j+1]
        in assumption that S[i] can be 0
        :param i: line size
        :param j: block number
        """

        if self._can_be_space(self.line[i]):
            return self.fix(i - 1, j)

        return False

    def _fix1(self, i, j):
        """
        Determine whether S[:i+1] is fixable with respect to D[:j+1]
        in assumption that S[i] can be 1
        :param i: line size
        :param j: block number
        """
        block_size = self.description[j]
        if j >= 0 and i >= block_size:
            block = self.line[i - block_size: i + 1]
            if self._is_space_with_block(block):
                return self.fix(i - block_size - 1, j - 1)

        return False

    @classmethod
    def _is_space_with_block(cls, line):
        if cls._can_be_space(line[0]):
            if all(pixel in (BOX, UNKNOWN) for pixel in line[1:]):
                return True

        return False

    @classmethod
    def _space_with_block(cls, block_size):
        return [cls.empty_cell()] + ([BOX] * block_size)

    @classmethod
    def empty_cell(cls):
        """
        Represent a single line symbol that is empty (no color)
        """
        return SPACE

    def paint(self, i, j):
        """
        Paint unsolved cells of line[:i+1]
        using blocks from 0 to (j+1)-th as description
        """
        if i < 0:
            return []

        painted = self._paint_table[self._linear_index(i, j)]
        if painted is None:
            if j < 0:
                if all(map(self._can_be_space, self.line[:i + 1])):
                    painted = [self.empty_cell()] * (i + 1)
                else:
                    raise NonogramError('Excess cells found at the beginning')
            else:
                painted = self._paint(i, j)

            self._paint_table[self._linear_index(i, j)] = painted

        return painted

    def _paint(self, i, j):
        fix0 = self._fix0(i, j)
        fix1 = self._fix1(i, j)

        if fix0:
            if fix1:
                return self._paint_both(i, j)

            return self._paint0(i, j)

        if fix1:
            return self._paint1(i, j)

        raise NonogramError('Block %r not fixable at position %r' % (j, i))

    def _paint0(self, i, j):
        return self.paint(i - 1, j) + [self.empty_cell()]

    def _paint1(self, i, j):
        block_size = self.description[j]
        return self.paint(i - block_size - 1, j - 1) + self._space_with_block(block_size)

    @classmethod
    def _merge_iter(cls, line1, line2):
        for pixel1, pixel2 in zip(line1, line2):
            if pixel1 == pixel2:
                yield pixel1
            else:
                yield UNKNOWN

    def _paint_both(self, i, j):
        return list(self._merge_iter(
            self._paint0(i, j),
            self._paint1(i, j)
        ))

    def _solve(self):
        res = self.paint(len(self.line) - 1, len(self.description) - 1)
        if self.additional_space:
            res = res[1:]

        return res


class EfficientColorSolver(EfficientSolver):
    """Recursive nonogram solver for colored puzzles"""

    def __init__(self, description, line):
        super(EfficientColorSolver, self).__init__(description, line)

        self.colors = set(color for size, color in self.description)

    def _set_additional_space(self):
        return False

    @classmethod
    def min_lengths(cls, description):
        if not description:
            return []

        minimum_lengths = [description[0].size - 1]
        for i, block in enumerate(description[1:], 1):
            size, color = block

            prev = minimum_lengths[-1]
            if description[i - 1].color == color:
                # at least one space + block size
                current = prev + 1 + size
            else:
                # only block size, can be no delimited space
                current = prev + size

            minimum_lengths.append(current)

        return minimum_lengths

    @classmethod
    def empty_cell(cls):
        return SPACE_COLORED

    @classmethod
    def _can_be_space(cls, cell):
        # not (len(cell) == 1 and cell[0] in self.colors)
        return cls.empty_cell() & cell

    def _fix(self, i, j):
        res = self._fix_border_conditions(i, j)
        if res is not None:
            return res

        color = self.description[j].color
        return self._fix0(i, j) or self._fix_colored(i, j, color)

    def _precede_with_space(self, j):
        current_color = self.description[j].color

        if j > 0:
            prev_color = self.description[j - 1].color
            if prev_color == current_color:
                return True

        return False

    def _fix_colored(self, i, j, color):
        if j < 0:
            return False

        size, desc_color = self.description[j]
        if color != desc_color:
            return False

        preceding_space = self._precede_with_space(j)

        if preceding_space:
            block_size = size + 1
        else:
            block_size = size

        if i >= block_size - 1:
            block = self.line[i - block_size + 1: i + 1]

            if self._can_be_colored(block, color, preceding_space=preceding_space):
                return self.fix(i - block_size, j - 1)

        return False

    @classmethod
    def _can_be_colored(cls, line, color, preceding_space=True):
        if preceding_space:
            if cls._can_be_space(line[0]):
                # ignore the space header
                line = line[1:]
            else:
                return False

        return all(color & cell for cell in line)

    @classmethod
    def _color_block(cls, block_size, color, preceding_space=True):
        block = []
        if preceding_space:
            block = [cls.empty_cell()]
            block_size -= 1

        block += [color] * block_size
        return block

    def _paint(self, i, j):
        fix0 = self._fix0(i, j)

        fix_colors = []
        for color in self.colors:
            if self._fix_colored(i, j, color):
                fix_colors.append(color)

        if fix0:
            if fix_colors:
                fix_colors.append(self.empty_cell())
                return self._paint_all(i, j, fix_colors)

            return self._paint0(i, j)

        if fix_colors:
            return self._paint_all(i, j, fix_colors)

        raise NonogramError('Block %r not fixable at position %r' % (j, i))

    def _paint_color(self, i, j):
        size, color = self.description[j]

        preceding_space = self._precede_with_space(j)

        if preceding_space:
            block_size = size + 1
        else:
            block_size = size

        prev = self.paint(i - block_size, j - 1)
        this = self._color_block(block_size, color, preceding_space=preceding_space)
        return prev + this

    @classmethod
    def _merge(cls, *s):
        if len(s) == 1:
            return s[0]

        res = []
        for cells in zip(*s):
            res.append(from_two_powers(cells))

        return res

    def _paint_all(self, i, j, colors):
        lines = []
        if self.empty_cell() in colors:
            lines.append(self._paint0(i, j))

        lines.append(self._paint_color(i, j))

        return self._merge(*lines)
