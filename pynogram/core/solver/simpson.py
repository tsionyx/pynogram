# -*- coding: utf-8 -*
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
    def push_left(cls, line, rule):
        """
        line, linelen and linestep, rule, rulelen and rulestep describe the
        line being solved.  The results will appear in pos[0],
        pos[posstep], ...  solid is workspace, an array of at least rulelen
        elements.  Return 0 if inconsistency detected; 1 if okay.
        """
        # my definitions
        linelen = len(line)
        linestep = 1
        rulelen = len(rule)
        rulestep = 1
        posstep = 1
        pos = [0] * rulelen
        solid = [-1] * rulelen

        # working variables
        # size_t i;
        # const nonogram_cell *cp, *cp2;
        # nonogram_sizetype posv, rulev;

        # initial state
        block = 0

        if rulelen > 0:
            pos[block * posstep] = 0

        ruledesc = [rule[rn * rulestep] for rn in range(rulelen)]
        LOG.info("Pushing rule: %s", ', '.join(map(str, ruledesc)))

        linedesc = []
        for rn in range(linelen):
            item = line[rn * linestep]
            linedesc.append(_SYMBOL_MAP.get(item, '?'))
        LOG.info("Pushing line: >%s<", ''.join(linedesc))

        while block < rulelen:
            # find first/next non-dot:
            # stop if block won't fit into remainder of line

            posv = pos[block * posstep]
            rulev = rule[block * rulestep]

            LOG.debug("     start %d >%s %d", block, posv, rulev)

            while posv + rulev < linelen:
                cp = line[posv * linestep]
                if cp != SPACE:
                    break

                posv += 1

            pos[block * posstep] = posv
            LOG.debug("     end %d >%s %d", block, posv, rulev)

            # no room left
            if (posv + rulev > linelen) or (line[posv * linestep] == SPACE):
                raise NonogramError("No room left: cannot fit %d-th block" % block)

            # assume current position doesn't cover a solid
            solid[block] = -1

            # check if the block fits in before the next dot;
            # monitor for passing over a solid
            i = 0
            while i < rulev:
                cp = line[(posv + i) * linestep]
                if cp == SPACE:
                    break

                if (solid[block] < 0) and (cp == BOX):
                    LOG.debug("     solid %d >%s#",
                              block, (posv + i))
                    solid[block] = i
                i += 1

            # if a dot was encountered...
            if i < rulev:
                LOG.debug("     dot %d >%s-", block, (posv + i))

                # if a solid is covered, get an earlier block to fit
                if solid[block] >= 0:
                    # find an earlier block that can be moved to cover the solid
                    # covered by the next block without uncovering its own
                    while True:
                        if block == 0:
                            raise NonogramError("All previous blocks cover solids")
                        block -= 1
                        if (solid[block] < 0) or (
                                pos[(block + 1) * posstep] + solid[block + 1]
                                - rule[block * rulestep] + 1 <=
                                pos[block * posstep] + solid[block]):
                            break

                    # set the block near to the position of the next block,
                    # so that it just overlaps the solid, and try again
                    next_pos = pos[(block + 1) * posstep]
                    next_solid = solid[block + 1]
                    pos[block * posstep] = next_pos + next_solid - rule[block * rulestep] + 1
                    continue

                # otherwise, simply move to the dot, and try again
                pos[block * posstep] += i
                continue

            # now check to see if the end of the current block touches an
            # existing solid - if so, the block must be shuffled further to
            # ensure it overlaps the solid, but no solid may emerge from the
            # other end
            posv = pos[block * posstep]

            if posv + rulev < linelen:
                cp2 = line[(posv + rulev) * linestep]

                if (cp2 == BOX) and (solid[block] < 0):
                    solid[block] = rulev

                while posv + rulev < linelen:
                    cp = line[posv * linestep]
                    if cp == BOX:
                        break
                    cp2 = line[(posv + rulev) * linestep]
                    if cp2 != BOX:
                        break

                    posv += 1
                    solid[block] -= 1

            pos[block * posstep] = posv

            LOG.debug("     shuffle %s >%s %d", block, posv, rulev)

            # if there's still a solid immediately after the block, there's
            # an error, so find an earlier block to move
            if posv + rulev < linelen:
                cp2 = line[(posv + rulev) * linestep]
                if cp2 == BOX:
                    LOG.debug("     stretched %d >%s#", block, (posv + i))

                    # find an earlier block that isn't covering a solid
                    error_block = block
                    while True:
                        if block == 0:
                            raise NonogramError(
                                "The %d-th block cannot be stretched" % error_block)
                        block -= 1
                        if (solid[block] < 0) or (
                                pos[(block + 1) * posstep] + solid[block + 1]
                                - rule[block * rulestep] + 1 <=
                                pos[block * posstep] + solid[block]):
                            break

                    # set the block near to the position of the next block,
                    # so that it just overlaps the solid, and try again
                    next_pos = pos[(block + 1) * posstep]
                    next_solid = solid[block + 1]
                    pos[block * posstep] = next_pos + next_solid - rule[block * rulestep] + 1
                    continue

            # the block is in place, so try the next
            posv = pos[block * posstep] + 1 + rule[block * rulestep]
            if block + 1 < rulelen:
                block += 1
                pos[block * posstep] = posv
            else:
                # no more blocks, so just check for any remaining solids
                while posv < linelen:
                    cp = line[posv * linestep]
                    if cp == BOX:
                        break

                    posv += 1

                # if a solid was found...
                if posv < linelen:
                    LOG.debug("     trailing >%s#", posv)

                    # move the block so it covers it, but check if solid
                    # becomes uncovered
                    if (solid[block] >= 0) and (
                            posv - rulev + 1 > pos[block * posstep] + solid[block]):
                        #  a solid was uncovered, so look for an earlier block

                        # find an earlier block that isn't covering a solid
                        while True:
                            if block == 0:
                                raise NonogramError("All previous blocks cover solids")
                            block -= 1
                            if (solid[block] < 0) or (
                                    pos[(block + 1) * posstep] +
                                    solid[block + 1]
                                    - rule[block * rulestep] + 1 <=
                                    pos[block * posstep] + solid[block]):
                                break

                        # set the block near to the position of the next block,
                        # so that it just overlaps the solid, and try again
                        next_pos = pos[(block + 1) * posstep]
                        next_solid = solid[block + 1]
                        pos[block * posstep] = next_pos + next_solid - rule[block * rulestep] + 1

                        continue
                    # if (solid[block] >= 0) ... }

                    # solid[block] -= posv - rulev + 1 - pos[block * posstep]
                    pos[block * posstep] = posv - rulev + 1
                    continue
                # if posv < linelen ... }
                # no solid found
                block += 1
            # if block + 1 < rulelen: else ... }
        # while block < rulelen ... }
        # all okay
        return pos

    @classmethod
    def push_right(cls, line, clue):
        """Move all the blocks to the right"""
        clue = clue[::-1]
        line = line[::-1]

        # res = []
        # for r in reversed(nonogram_push(line, clue)):
        #     res.append(len(line) - 1 - r)
        # return res

        return list(reversed(cls.push_left(line, clue)))

    @classmethod
    def solve(cls, rule, line):
        """
        Solve the given line with given rule (description)
        with left and right overlap algorithm
        """

        # pylint: disable=no-member
        solved = cls.solutions_cache.get((rule, line))
        if solved is not None:
            assert len(solved) == len(line)
            return solved

        # nonogram_size
        # size_t i, j, k;
        # nonogram_cell *cp;

        linelen = len(line)

        linestep = 1
        rulelen = len(rule)
        rulestep = 1

        LOG.debug("Line range = %s to %s",
                  0, (linelen - 1) * linestep)

        if (rulelen == 1) and rule[0] == 0:
            rulelen = 0

        lpos = cls.push_left(line, rule)

        left_desc = []
        for bl in range(rulelen):
            left_desc.append("(%s + %s)" % (lpos[bl], rule[bl * rulestep]))
        LOG.info("Left: %s", ' '.join(left_desc))
        left_desc = []
        for bl in range(rulelen):
            size_now = sum(map(len, left_desc))
            block = ('-' * (lpos[bl] - size_now)) + ('#' * rule[bl * rulestep])
            left_desc.append(block)

        x = len(''.join(left_desc))
        left_desc.append('-' * (linelen - x))
        LOG.info("Left: >%s<", ''.join(left_desc))

        middle_desc = []
        for x in range(linelen):
            item = line[x * linestep]
            middle_desc.append(_SYMBOL_MAP.get(item, '?'))
        LOG.info("Middle: >%s<", ''.join(middle_desc))

        LOG.info("Line range = %d to %d", 0, (linelen - 1) * linestep)

        rpos = cls.push_right(line, rule)

        right_desc = []
        for bl in range(rulelen):
            right_desc.append("(%s + %s)" % (rpos[bl], rule[bl * rulestep]))
        LOG.info("Right: %s", ' '.join(right_desc))
        right_desc = []
        for bl in range(rulelen):
            size_now = sum(map(len, right_desc))
            dots = '-' * (linelen - rpos[bl] - rule[bl * rulestep] - size_now)
            solids = '#' * (rule[bl * rulestep])
            block = dots + solids
            right_desc.append(block)

        x = len(''.join(right_desc))
        right_desc.append('-' * (linelen - x))
        LOG.info("Right: >%s<", ''.join(right_desc))

        work = list(line)

        j = 0
        for i in range(rulelen):
            rpos[i] = linelen - rpos[i] - rule[i * rulestep]

            k = lpos[i]
            work[j: k] = [SPACE] * (k - j)

            j = rpos[i]
            k = lpos[i] + rule[i * rulestep]

            work[j: k] = [BOX] * (k - j)

            j = rpos[i] + rule[i * rulestep]

        k = linelen
        work[j: k] = [SPACE] * (k - j)

        # pylint: disable=no-member
        cls.solutions_cache.save((rule, line), work)
        return work
