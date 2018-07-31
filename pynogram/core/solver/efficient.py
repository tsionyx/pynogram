# -*- coding: utf-8 -*-
"""
Dynamic programming algorithm from the work
'An Efficient Approach to Solving Nonograms'

https://ir.nctu.edu.tw/bitstream/11536/22772/1/000324586300005.pdf
"""

from __future__ import unicode_literals

import logging

from six import add_metaclass
from six.moves import zip

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE,
)
from pynogram.core.solver.common import (
    LineSolutionsMeta,
    NonogramError
)
from pynogram.utils.cache import memoized_instance

LOG = logging.getLogger(__name__)


@add_metaclass(LineSolutionsMeta)
class EfficientSolver(object):
    def __init__(self, description, line):
        self.description = description
        self.line = line

        self.minimum_lengths = self.min_lengths(self.description)
        self.additional_space = self._set_additional_space()

    def _set_additional_space(self):
        space = self.empty_cell()
        if self.line[0] != space:
            self.line = (space,) + self.line
            return True
        return False

    @classmethod
    def min_lengths(cls, description):
        """
        The mimimum line sizes in which can squeeze from 0 to i-th block
        """

        if not description:
            return []

        minimum_lengths = [description[0] - 1]
        for block in description[1:]:
            prev = minimum_lengths[-1]
            # at least one space + block size
            minimum_lengths.append(prev + 1 + block)

        return minimum_lengths

    @memoized_instance
    def _fix(self, i, j):
        """
        Determine whether S[:i+1] is fixable with respect to D[:j+1]
        :param i: line size
        :param j: block number
        """

        if j < 0:
            assert j == -1

            # NB: improvement
            # if no more blocks left, but some BOX pixels still appear
            return BOX not in self.line[:i + 1]

        # reached the beginning of the line
        if i < 0:
            assert i == -1

            # no more blocks to fill
            if j < 0:
                return True
            else:
                return False

        if i < self.minimum_lengths[j]:
            return False

        res = self._fix0(i, j) or self._fix1(i, j)
        return res

    def _fix0(self, i, j):
        """
        Determine whether S[:i+1] is fixable with respect to D[:j+1]
        in assumption that S[i] can be 0
        :param i: line size
        :param j: block number
        """

        if self.line[i] in (SPACE, UNKNOWN):
            return self._fix(i - 1, j)

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
                return self._fix(i - block_size - 1, j - 1)

        return False

    @classmethod
    def _is_space_with_block(cls, s):
        if s[0] in (SPACE, UNKNOWN):
            if all(pixel in (BOX, UNKNOWN) for pixel in s[1:]):
                return True

        return False

    @classmethod
    def _space_with_block(cls, block_size):
        return (cls.empty_cell(),) + (BOX,) * block_size

    @classmethod
    def empty_cell(cls):
        return SPACE

    def paint(self, i, j):
        if i < 0:
            return ()

        if j < 0:
            return tuple([self.empty_cell()] * (i + 1))

        return self._paint(i, j)

    @memoized_instance
    def _paint(self, i, j):
        fix0 = self._fix0(i, j)
        fix1 = self._fix1(i, j)

        if fix0:
            if fix1:
                return self._paint_both(i, j)
            else:
                return self._paint0(i, j)
        else:
            if fix1:
                return self._paint1(i, j)
            else:
                raise NonogramError('Block %r not fixable at position %r' % (j, i))

    def _paint0(self, i, j):
        return self.paint(i - 1, j) + (self.empty_cell(),)

    def _paint1(self, i, j):
        block_size = self.description[j]
        return self.paint(i - block_size - 1, j - 1) + self._space_with_block(block_size)

    @classmethod
    def _merge_iter(cls, s1, s2):
        for pixel1, pixel2 in zip(s1, s2):
            if pixel1 == pixel2:
                yield pixel1
            else:
                yield UNKNOWN

    def _paint_both(self, i, j):
        return tuple(self._merge_iter(
            self._paint0(i, j),
            self._paint1(i, j)
        ))

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

        solver = cls(clue, line)
        try:
            solved = solver._solve()
            # pylint: disable=no-member
            cls.solutions_cache.save((clue, line), solved)
            return solved
        except NonogramError:
            cls.solutions_cache.save((clue, line), False)
            raise NonogramError("Failed to solve line '{}' with clues '{}'".format(line, clue))

    def _solve(self):
        res = self.paint(len(self.line) - 1, len(self.description) - 1)
        if self.additional_space:
            res = res[1:]

        return res


@add_metaclass(LineSolutionsMeta)
class EfficientColorSolver(EfficientSolver):
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

    @memoized_instance
    def _fix(self, i, j):
        """
        Determine whether S[:i+1] is fixable with respect to D[:j+1]
        :param i: line size
        :param j: block number
        """

        if j < 0:
            assert j == -1

            if i < 0:
                return True

            # NB: improvement
            # return any(len(cell) == 1 and cell[0] in self.colors for cell in self.line[:i + 1])
            # spaces should be allowed for the rest of the line
            for cell in self.line[:i + 1]:
                if SPACE not in cell:
                    return False
            return True

        # reached the beginning of the line
        if i < 0:
            assert i == -1

            # no more blocks to fill
            if j < 0:
                return True
            else:
                return False

        if i < self.minimum_lengths[j]:
            return False

        color = self.description[j].color
        return self._fix0(i, j) or self._fix_colored(i, j, color)

    def _fix0(self, i, j):
        """
        Determine whether S[:i+1] is fixable with respect to D[:j+1]
        in assumption that S[i] can be 0
        :param i: line size
        :param j: block number
        """

        if SPACE in self.line[i]:
            return self._fix(i - 1, j)

        return False

    def _precede_with_space(self, j):
        current_color = self.description[j].color

        if j > 0:
            prev_color = self.description[j - 1].color
            if prev_color == current_color:
                return True

        return False

    def _fix_colored(self, i, j, color):
        """
        Determine whether S[:i+1] is fixable with respect to D[:j+1]
        in assumption that S[i] can be of specified color
        :param i: line size
        :param j: block number
        """

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
                return self._fix(i - block_size, j - 1)

        return False

    @classmethod
    def _can_be_colored(cls, s, color, preceding_space=True):
        if preceding_space:
            if SPACE in s[0]:
                # ignore the space header
                s = s[1:]
            else:
                return False

        return all(color in cell for cell in s)

    @classmethod
    def _color_block(cls, block_size, color, preceding_space=True):
        if preceding_space:
            block = (cls.empty_cell(),)
            block_size -= 1
        else:
            block = ()

        block += ({color},) * block_size
        return block

    @classmethod
    def empty_cell(cls):
        return {SPACE}

    @memoized_instance
    def _paint(self, i, j):
        fix0 = self._fix0(i, j)

        fix_colors = []
        for color in self.colors:
            if self._fix_colored(i, j, color):
                fix_colors.append(color)

        if fix0:
            if fix_colors:
                fix_colors.append(SPACE)
                return self._paint_all(i, j, fix_colors)
            else:
                return self._paint0(i, j)
        else:
            if fix_colors:
                return self._paint_all(i, j, fix_colors)
            else:
                raise NonogramError('Block %r not fixable at position %r' % (j, i))

    def _paint0(self, i, j):
        return self.paint(i - 1, j) + (self.empty_cell(),)

    def _paint_color(self, i, j):
        size, color = self.description[j]

        preceding_space = self._precede_with_space(j)

        if preceding_space:
            block_size = size + 1
        else:
            block_size = size

        return self.paint(i - block_size, j - 1) + self._color_block(
            block_size, color, preceding_space=preceding_space)

    @classmethod
    def _merge_iter(cls, *s):
        for cells in zip(*s):
            # print(s)
            # print(cells)
            yield set([color for cell in cells for color in cell])

    def _paint_all(self, i, j, colors):
        lines = []
        if SPACE in colors:
            lines.append(self._paint0(i, j))

        lines.append(self._paint_color(i, j))

        if len(lines) == 1:
            return lines[0]
        return tuple(self._merge_iter(*lines))

    def _solve(self):
        res = super(EfficientColorSolver, self)._solve()
        res_tuple = []
        for cell in res:
            res_tuple.append(tuple(cell))

        return tuple(res_tuple)
