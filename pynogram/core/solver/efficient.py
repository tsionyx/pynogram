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
    UNKNOWN, BOX, SPACE
)
from pynogram.core.solver.common import (
    LineSolutionsMeta,
    NonogramError
)
from pynogram.utils.cache import memoized

LOG = logging.getLogger(__name__)


@add_metaclass(LineSolutionsMeta)
class EfficientSolver(object):
    def __init__(self, description, line):
        self.description = description
        self.line = line

        self.additional_space = False
        if self.line[0] != SPACE:
            self.line = (SPACE,) + self.line
            self.additional_space = True

        # the mimimum line in which can squeeze from 0 to i-th block
        self.minimum_lengths = [self.description[0] - 1]
        for block in self.description[1:]:
            prev = self.minimum_lengths[-1]
            # at least one space + block size
            self.minimum_lengths.append(prev + 1 + block)

    @memoized
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
        return (SPACE,) + (BOX,) * block_size

    def paint(self, i, j):
        if i < 0:
            return ()

        return self._paint(i, j)

    @memoized
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
        return self.paint(i - 1, j) + (SPACE,)

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
