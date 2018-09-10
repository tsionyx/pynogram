# -*- coding: utf-8 -*-
"""Define nonogram solving operations"""

from __future__ import unicode_literals, print_function

import logging

from six import (
    iteritems, itervalues,
    add_metaclass,
)

from pynogram.core.common import (
    NonogramError,
    SPACE_COLORED,
    BlottedBlock,
)
from pynogram.utils.cache import Cache
from pynogram.utils.other import two_powers

LOG = logging.getLogger(__name__)


class TwoLayerCache(Cache):
    """
    Special cache for storing nonograms line solutions.
    The keys are pairs (clue, partial_solution)
    """

    def __len__(self):
        return sum(len(lines) for lines in itervalues(self._storage))

    def _save(self, name, value, **kwargs):
        clue, prev_line = name
        if clue not in self._storage:
            self._storage[clue] = dict()

        self._storage[clue][prev_line] = value

    def _get(self, name):
        clue, prev_line = name
        clue_solutions = self._storage.get(clue)
        if clue_solutions is None:
            return None

        return clue_solutions.get(prev_line)

    def delete(self, name):
        clue, prev_line = name
        clue_solutions = self._storage.get(clue)
        if clue_solutions is None:
            return False

        return bool(clue_solutions.pop(prev_line, False))


class LineSolutionsMeta(type):
    """
    A metaclass for line solvers.
    It adds the solutions_cache to the solver class.
    """

    registered_caches = {}

    def __new__(mcs, *args, **kwargs):
        new_cls = super(LineSolutionsMeta, mcs).__new__(mcs, *args, **kwargs)
        new_cls.solutions_cache = Cache(increase=True)
        mcs.registered_caches[new_cls.__name__] = new_cls.solutions_cache
        return new_cls


def cache_info():
    """Cache size and hit rate for different solvers"""
    return {
        class_name: (len(cache), cache.hit_rate)
        for class_name, cache in iteritems(LineSolutionsMeta.registered_caches)
    }


@add_metaclass(LineSolutionsMeta)
class BaseLineSolver(object):
    """
    Basic line nonogram solver which provides
    facilities to save and extract solutions using cache
    """

    def __init__(self, description, line):
        self.description = description
        self.line = line

    @classmethod
    def _error_message(cls, description, line, additional_info=''):
        """Solve the line (or use cached value)"""
        description, line = tuple(description), tuple(line)
        return '{}: Failed to solve line {!r} with clues {!r}{}'.format(
            cls.__name__, line, description, additional_info)

    @classmethod
    def solve(cls, description, line):
        """Solve the line (or use cached value)"""
        if not line:
            return line

        description, line = tuple(description), tuple(line)

        solved = cls.solutions_cache.get((description, line))

        if solved is False:
            raise NonogramError(
                cls._error_message(description, line, additional_info=' (cached)'))

        if solved is not None:
            assert len(solved) == len(line)
            return solved

        solver = cls(description, line)
        try:
            solved = tuple(solver._solve())
        except NonogramError as ex:
            cls.save_in_cache((description, line), False)
            raise NonogramError(
                cls._error_message(description, line, additional_info=': {}'.format(ex)))

        assert len(solved) == len(line)
        cls.save_in_cache((description, line), solved)
        return solved

    @classmethod
    def save_in_cache(cls, original, solved):
        """
        Put the solution in local cache.
        Use solved=False to show that the line is not solvable.
        """
        cls.solutions_cache.save(original, solved)

    def _solve(self):
        """
        Override this function with actual solving algorithm.
        You should return something iterable (tuple, list or even generator!).
        """
        return self.line


class TrimmedSolver(BaseLineSolver):
    """Define some helpers for colored puzzle solvers"""

    @classmethod
    def prefix_size(cls, line, item):
        """
        How many items appear at the beginning of the line
        """
        for spaces_size, cell in enumerate(line):
            if cell != item:
                return spaces_size

        return len(line)

    @classmethod
    def _trim_spaces(cls, line):  # pragma: no cover
        space = SPACE_COLORED
        head_size = cls.prefix_size(line, space)
        tail_size = cls.prefix_size(list(reversed(line)), space)

        if tail_size:
            line = line[head_size: -tail_size]
        else:
            line = line[head_size:]

        space_tuple = (space,)

        return space_tuple * head_size, line, space_tuple * tail_size

    @classmethod
    def starting_solved(cls, description, line):
        """
        Trim off the solved cells from the beginning of the line.
        Also fix the description respectively.

        Return the pair (number of solved cells, number of solved blocks)
        """
        space = SPACE_COLORED

        block_index = 0
        last_block = len(description) - 1

        pos = 0
        last_pos = len(line) - 1

        while pos <= last_pos:
            # skip definite spaces
            if line[pos] == space:
                pos += 1
                continue

            cell = line[pos]
            cell_colors = two_powers(cell)
            if len(cell_colors) > 1:
                break

            color = cell_colors[0]

            if block_index > last_block:
                raise NonogramError(
                    'Bad block index {} '
                    'for description {!r}'.format(block_index, description))

            block = description[block_index]
            if color != block.color:
                raise NonogramError(
                    'Color {!r} at the position {!r} of the line {!r}'
                    'does not match the color of the corresponding block {!r} '
                    'in description {!r}'.format(
                        color, pos, line, block, description))

            size = block.size
            if size == BlottedBlock:

                end_pos = pos + 1
                while end_pos <= last_pos and line[end_pos] == color:
                    end_pos += 1

                if end_pos <= last_pos:
                    cell_colors = two_powers(line[end_pos])
                    # can't say definitely whether the blotted block ends here
                    if color in cell_colors:
                        # the partially solved blotted block can be reduced to one cell
                        pos = end_pos - 1
                        break

                pos = end_pos
                block_index += 1

            else:
                if pos + size > last_pos + 1:
                    raise NonogramError(
                        'The {}-th block {!r} cannot be allocated in the line {!r}'.format(
                            block_index, block, line))

                if line[pos: pos + size] != [color] * size:
                    break

                if block_index < last_block:
                    next_block = description[block_index + 1]
                    if next_block.color == color:
                        try:
                            if line[pos + size] != space:
                                break
                        except IndexError:
                            raise NonogramError(
                                'The next ({}-th) block {!r} '
                                'cannot be allocated in the line {!r}'.format(
                                    block_index + 1, next_block, line))
                pos += size
                block_index += 1

        return pos, block_index

    @classmethod
    def _trim_solved_blocks(cls, description, line):
        LOG.info('Trying to trim off solved cells: %r, %r', description, line)

        beg_solved, beg_blocks = cls.starting_solved(list(description), list(line))
        fin_solved, fin_blocks = cls.starting_solved(
            list(reversed(description)), list(reversed(line)))

        start = tuple(line[:beg_solved])

        if fin_solved:
            end = tuple(line[-fin_solved:])
            line = line[beg_solved: -fin_solved]
        else:
            end = ()
            # hack to do foo[a: b] == foo[a:]: just assign b = -len(foo)
            # fin_solved = -len(line)
            line = line[beg_solved:]

        if fin_blocks:
            description = description[beg_blocks: -fin_blocks]
        else:
            description = description[beg_blocks:]

        if not line and description:
            raise NonogramError('Some blocks left after trimming the whole line')

        return description, line, (start, end)

    @classmethod
    def solve(cls, description, line):
        """Optimize line solving by trimming off the spaces and solved blocks"""
        # head, line, tail = cls._trim_spaces(line)
        # if not line:  # if consists only of spaces
        #     return head

        description, line, edges = cls._trim_solved_blocks(description, line)
        if any(edges):
            LOG.info('Trimmed edges: %r, %r', *edges)
            LOG.info('What is left after trimming: description %r and line %r',
                     description, line)
        if not line:  # all the cells are solved
            solved = edges[0]
        else:
            solved = super(TrimmedSolver, cls).solve(description, line)
            solved = edges[0] + solved + edges[1]

        # # restore the spaces
        # if head or tail:
        #     solved = head + solved + tail

        return solved
