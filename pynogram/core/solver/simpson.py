# -*- coding: utf-8 -*-
"""
Simple algorithm to solve nonograms using left and right overlaps

See details:
http://www.lancaster.ac.uk/~simpsons/nonogram/ls-fast
"""

from __future__ import unicode_literals, print_function

import logging

from six import add_metaclass
from six.moves import range

from pynogram.core.common import (
    BOX, SPACE, UNKNOWN,
)
from pynogram.core.solver.common import (
    NonogramError,
    LineSolutionsMeta,
)

LOG = logging.getLogger(__name__)

_SYMBOL_MAP = {
    UNKNOWN: ' ',
    SPACE: '-',
    BOX: '#',
}


@add_metaclass(LineSolutionsMeta)
class FastSolver(object):
    """
    Nonogram line solver, that uses left and right overlap algorithm.
    The algorithm gets most of the solution, but sometimes not complete one.
    """

    @classmethod
    def push_left(cls, line, clue):
        """
        Move all the blocks to the left.
        Raise NonogramError if inconsistency detected.
        """

        line_size = len(line)
        clue_size = len(clue)
        res = [0] * clue_size
        solid = [-1] * clue_size

        # initial state
        current_block = 0

        if clue_size > 0:
            res[current_block] = 0

        LOG.info("Pushing clue: %s", ', '.join(map(str, clue)))
        LOG.info("Pushing line: >%s<", ''.join(
            _SYMBOL_MAP.get(cell, '?') for cell in line))

        while current_block < clue_size:
            # find first/next non-dot:
            # stop if current_block won't fit into remainder of line

            pos = res[current_block]
            block_size = clue[current_block]

            LOG.debug("     start %d >%s %d", current_block, pos, block_size)

            while pos < line_size - block_size:
                cell = line[pos]
                if cell != SPACE:
                    break

                pos += 1

            res[current_block] = pos
            LOG.debug("     end %d >%s %d", current_block, pos, block_size)

            # no room left
            if (pos + block_size > line_size) or (line[pos] == SPACE):
                raise NonogramError("No room left: cannot fit %d-th block" % current_block)

            # assume current position doesn't cover a solid
            solid[current_block] = -1

            # check if the current_block fits in before the next dot;
            # monitor for passing over a solid
            i = 0
            while i < block_size:
                cell = line[pos + i]
                if cell == SPACE:
                    break

                if (solid[current_block] < 0) and (cell == BOX):
                    LOG.debug("     solid %d >%s#",
                              current_block, (pos + i))
                    solid[current_block] = i
                i += 1

            # if a dot was encountered...
            if i < block_size:
                LOG.debug("     dot %d >%s-", current_block, (pos + i))

                # if a solid is covered, get an earlier current_block to fit
                if solid[current_block] >= 0:
                    # find an earlier current_block that can be moved to cover the solid
                    # covered by the next current_block without uncovering its own
                    while True:
                        if current_block == 0:
                            raise NonogramError("All previous blocks cover solids")
                        current_block -= 1
                        if (solid[current_block] < 0) or (
                                res[current_block + 1] + solid[current_block + 1] -
                                clue[current_block] + 1 <=
                                res[current_block] + solid[current_block]):
                            break

                    # set the current_block near to the position of the next current_block,
                    # so that it just overlaps the solid, and try again
                    next_pos = res[current_block + 1]
                    next_solid = solid[current_block + 1]
                    res[current_block] = next_pos + next_solid - clue[current_block] + 1
                    continue

                # otherwise, simply move to the dot, and try again
                res[current_block] += i
                continue

            # now check to see if the end of the current current_block touches an
            # existing solid - if so, the current_block must be shuffled further to
            # ensure it overlaps the solid, but no solid may emerge from the
            # other end
            pos = res[current_block]

            if pos + block_size < line_size:
                end_block_cell = line[pos + block_size]

                if (end_block_cell == BOX) and (solid[current_block] < 0):
                    solid[current_block] = block_size

                while pos + block_size < line_size:
                    cell = line[pos]
                    if cell == BOX:
                        break
                    end_block_cell = line[pos + block_size]
                    if end_block_cell != BOX:
                        break

                    pos += 1
                    solid[current_block] -= 1

            res[current_block] = pos

            LOG.debug("     shuffle %s >%s %d", current_block, pos, block_size)

            # if there's still a solid immediately after the current_block, there's
            # an error, so find an earlier current_block to move
            if pos + block_size < line_size:
                end_block_cell = line[pos + block_size]
                if end_block_cell == BOX:
                    LOG.debug("     stretched %d >%s#", current_block, (pos + i))

                    # find an earlier current_block that isn't covering a solid
                    error_block = current_block
                    while True:
                        if current_block == 0:
                            raise NonogramError(
                                "The %d-th block cannot be stretched" % error_block)
                        current_block -= 1
                        if (solid[current_block] < 0) or (
                                res[current_block + 1] + solid[current_block + 1] -
                                clue[current_block] + 1 <=
                                res[current_block] + solid[current_block]):
                            break

                    # set the current_block near to the position of the next current_block,
                    # so that it just overlaps the solid, and try again
                    next_pos = res[current_block + 1]
                    next_solid = solid[current_block + 1]
                    res[current_block] = next_pos + next_solid - clue[current_block] + 1
                    continue

            # the current_block is in place, so try the next
            pos = res[current_block] + 1 + clue[current_block]
            if current_block + 1 < clue_size:
                current_block += 1
                res[current_block] = pos
            else:
                # no more blocks, so just check for any remaining solids
                while pos < line_size:
                    cell = line[pos]
                    if cell == BOX:
                        break

                    pos += 1

                # if a solid was found...
                if pos < line_size:
                    LOG.debug("     trailing >%s#", pos)

                    # move the current_block so it covers it, but check if solid
                    # becomes uncovered
                    if (solid[current_block] >= 0) and (
                            pos - block_size + 1 > res[current_block] + solid[current_block]):
                        #  a solid was uncovered, so look for an earlier current_block

                        # find an earlier current_block that isn't covering a solid
                        while True:
                            if current_block == 0:
                                raise NonogramError("All previous blocks cover solids")
                            current_block -= 1
                            if (solid[current_block] < 0) or (
                                    res[current_block + 1] +
                                    solid[current_block + 1] - clue[current_block] + 1 <=
                                    res[current_block] + solid[current_block]):
                                break

                        # set the current_block near to the position of the next current_block,
                        # so that it just overlaps the solid, and try again
                        next_pos = res[current_block + 1]
                        next_solid = solid[current_block + 1]
                        res[current_block] = next_pos + next_solid - clue[current_block] + 1

                        continue
                    # if (solid[current_block] >= 0) ... }

                    # solid[current_block] -= pos - block_size + 1 - res[current_block]
                    res[current_block] = pos - block_size + 1
                    continue
                # if pos < line_size ... }
                # no solid found
                current_block += 1
            # if current_block + 1 < clue_size: else ... }
        # while current_block < clue_size ... }
        # all okay
        return res

    @classmethod
    def push_right(cls, line, clue):
        """Move all the blocks to the right"""
        clue = clue[::-1]
        line = line[::-1]

        return list(reversed(cls.push_left(line, clue)))

    @classmethod
    def solve(cls, clue, line):
        """
        Solve the given line with given clue (description)
        using left and right overlap algorithm
        """

        # pylint: disable=no-member
        solved = cls.solutions_cache.get((clue, line))
        if solved is not None:
            assert len(solved) == len(line)
            return solved

        line_size = len(line)
        clue_size = len(clue)

        LOG.debug("Line range = %s to %s", 0, line_size - 1)

        if (clue_size == 1) and clue[0] == 0:
            clue_size = 0

        left_positions = cls.push_left(line, clue)

        left_desc = []
        for block in range(clue_size):
            left_desc.append("(%s + %s)" % (left_positions[block], clue[block]))
        LOG.info("Left: %s", ' '.join(left_desc))
        left_desc = []
        for block in range(clue_size):
            size_now = sum(map(len, left_desc))
            block = ('-' * (left_positions[block] - size_now)) + ('#' * clue[block])
            left_desc.append(block)

        desc_size = len(''.join(left_desc))
        left_desc.append('-' * (line_size - desc_size))
        LOG.info("Left: >%s<", ''.join(left_desc))

        middle_desc = [_SYMBOL_MAP.get(cell, '?') for cell in line]
        LOG.info("Middle: >%s<", ''.join(middle_desc))

        LOG.info("Line range = %d to %d", 0, line_size - 1)

        right_positions = cls.push_right(line, clue)

        right_desc = []
        for block in range(clue_size):
            right_desc.append("(%s + %s)" % (right_positions[block], clue[block]))
        LOG.info("Right: %s", ' '.join(right_desc))
        right_desc = []
        for block in range(clue_size):
            size_now = sum(map(len, right_desc))
            dots = '-' * (line_size - right_positions[block] - clue[block] - size_now)
            solids = '#' * (clue[block])
            block = dots + solids
            right_desc.append(block)

        desc_size = len(''.join(right_desc))
        right_desc.append('-' * (line_size - desc_size))
        LOG.info("Right: >%s<", ''.join(right_desc))

        work = list(line)

        j = 0
        for i in range(clue_size):
            right_positions[i] = line_size - right_positions[i] - clue[i]

            k = left_positions[i]
            work[j: k] = [SPACE] * (k - j)

            j = right_positions[i]
            k = left_positions[i] + clue[i]

            work[j: k] = [BOX] * (k - j)

            j = right_positions[i] + clue[i]

        k = line_size
        work[j: k] = [SPACE] * (k - j)

        work = tuple(work)
        # pylint: disable=no-member
        cls.solutions_cache.save((clue, line), work)
        return work
