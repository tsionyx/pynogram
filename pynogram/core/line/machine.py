# -*- coding: utf-8 -*-
"""
Nonogram solver using finite state machine

See source article (in russian):
http://window.edu.ru/resource/781/57781
"""

from __future__ import unicode_literals, print_function

import logging

from six import (
    iteritems, itervalues,
)
from six.moves import range

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE, SPACE_COLORED,
    normalize_description, normalize_row,
    is_list_like,
    NonogramError,
)
from pynogram.core.line.base import BaseLineSolver
from pynogram.core.line.simpson import FastSolver
from pynogram.utils import fsm
from pynogram.utils.cache import Cache
from pynogram.utils.other import (
    two_powers, from_two_powers,
    get_named_logger,
)

LOG = get_named_logger(__name__, __file__)

fsm.LOG.setLevel(logging.WARNING)


class NonogramFSM(fsm.FiniteStateMachine):
    """
    Represents a special class of a FSM
    used to solve a nonogram
    """

    def __init__(self, description, state_map):
        self.description = description
        initial_state = state_map[0][1]
        final = state_map[-1][1]
        super(NonogramFSM, self).__init__(initial_state, state_map, final=final)

    @classmethod
    def _space(cls):
        return SPACE

    @classmethod
    def _can_be_space(cls, cell):
        """
        Whether the cell can be a space
        """
        return cell in (UNKNOWN, cls._space())

    @classmethod
    def _can_be_empty(cls, row):
        """
        Whether the row can contain only spaces
        """
        return all(cls._can_be_space(cell) for cell in row)

    @classmethod
    def _optional_space(cls, state):
        return (state, cls._space()), state

    @classmethod
    def _required_color(cls, state, color):
        return (state, color), state + 1

    @classmethod
    def _required_box(cls, state):
        return cls._required_color(state, BOX)

    @classmethod
    def _required_space(cls, state):
        return cls._required_color(state, cls._space())

    INITIAL_STATE = 1

    @classmethod
    def state_map_from_description(cls, description):
        """
        Construct the machine's state map
        from the description
        given in a nonogram definition
        """
        LOG.debug('Clues: %s', description)

        state_counter = cls.INITIAL_STATE
        state_map = []

        prev_color = None
        for block in description:
            if is_list_like(block):
                value, color = block
            else:
                value, color = block, BOX

            # it SHOULD be a space before block
            # if it is not a first block AND the previous block was of the same color
            if prev_color == color:
                trans, state_counter = cls._required_space(state_counter)
                LOG.debug('Add transition: %s -> %s', trans, state_counter)
                state_map.append((trans, state_counter))

            # it CAN be multiple spaces before every block
            trans, state_counter = cls._optional_space(state_counter)
            LOG.debug('Add transition: %s -> %s', trans, state_counter)
            state_map.append((trans, state_counter))

            # the block of some color
            for _ in range(value):
                trans, state_counter = cls._required_color(state_counter, color)
                LOG.debug('Add transition: %s -> %s', trans, state_counter)
                state_map.append((trans, state_counter))

            prev_color = color

        # at the end of the line can be optional spaces
        trans, state_counter = cls._optional_space(state_counter)
        LOG.debug('Add transition: %s -> %s', trans, state_counter)
        state_map.append((trans, state_counter))

        return state_map

    def partial_match(self, row):
        """
        Verify if the row of (possibly partly unsolved) cells
        can be matched against the current machine
        i.e. that the row can be a partial solution of a nonogram
        """
        row = normalize_row(row)

        # save the state in case of something change it
        save_state = self.current_state

        try:
            possible_states = {self.initial_state}

            for i, cell in enumerate(row):
                step_possible_states = []
                for state in possible_states:
                    if cell in (BOX, UNKNOWN):
                        LOG.debug('Check the ability to insert BOX')

                        next_step = self.reaction(BOX, current_state=state)
                        if next_step is None:
                            LOG.debug('Cannot go from state %r with BOX', state)
                        else:
                            step_possible_states.append(next_step)

                    if cell in (SPACE, UNKNOWN):
                        LOG.debug('Check the ability to insert SPACE')

                        next_step = self.reaction(SPACE, current_state=state)
                        if next_step is None:
                            LOG.debug('Cannot go from state %r with SPACE', state)
                        else:
                            step_possible_states.append(next_step)

                if not step_possible_states:
                    return False

                LOG.debug('Possible states after step %s: %s', i, step_possible_states)
                possible_states = set(step_possible_states)

            LOG.debug('Possible states after full scan: %s', possible_states)
            return self.final_state in possible_states
        finally:
            self._state = save_state

    def solve_with_partial_match(self, row):
        """
        Solve the nonogram `row` using the FSM and `self.partial_match` logic
        """
        original_row = normalize_row(row)

        if not self.description and self._can_be_empty(row):
            return (self._space(),) * len(row)

        # do not change original
        solved = list(original_row)
        for i, cell in enumerate(original_row):
            if cell in (BOX, SPACE):
                continue

            LOG.debug('Trying to guess the %s cell', i)

            temp_row = list(original_row)
            temp_row[i] = BOX
            can_be_box = self.partial_match(temp_row)
            LOG.debug('The %s cell can%s be a BOX',
                      i, '' if can_be_box else 'not')

            temp_row[i] = SPACE
            can_be_space = self.partial_match(temp_row)
            LOG.debug('The %s cell can%s be a SPACE',
                      i, '' if can_be_space else 'not')

            if can_be_box:
                if not can_be_space:
                    solved[i] = BOX
            elif can_be_space:
                solved[i] = SPACE
            else:
                raise NonogramError(
                    'The {} cell ({}) in a row {!r} cannot be neither space nor box'.format(
                        i, cell, original_row))
        return solved

    @classmethod
    def _types_for_cell(cls, cell):
        if cell in (BOX, SPACE):
            return cell,

        if cell == UNKNOWN:
            return BOX, SPACE

        return ()

    def _make_transition_table(self, row):
        # for each read cell store a list of StepState
        # plus O-th for the state before any read cells
        transition_table = TransitionTable.with_capacity(len(row) + 1)
        transition_table.append_transition(0, self.initial_state)

        def _shift_one_cell(cell_type, trans_index,
                            previous_step_state, previous_state, desc_cell=None):
            if desc_cell:  # pragma: no cover
                LOG.debug('Add states with %s transition', desc_cell)

            new_state = self.reaction(cell_type, previous_state)
            if new_state is None:
                if desc_cell:  # pragma: no cover
                    LOG.debug('Cannot go from %s with the %s cell', previous_state, desc_cell)
            else:
                transition_table.append_transition(
                    trans_index, new_state, previous_step_state, cell_type)

        # optimize lookups
        _types_for_cell = self._types_for_cell

        for i, cell in enumerate(row):
            transition_index = i + 1

            for prev_state, prev in iteritems(transition_table[i]):
                for _type in _types_for_cell(cell):
                    _shift_one_cell(_type, transition_index,
                                    prev, prev_state)

        return transition_table

    @classmethod
    def _cell_value_from_solved(cls, states):
        assert states

        if len(states) == 1:
            return states[0]

        return UNKNOWN

    def solve_with_reverse_tracking(self, row):
        """
        Solve the nonogram `row` using the FSM and reverse tracking
        """
        if not self.description and self._can_be_empty(row):
            return (self._space(),) * len(row)

        transition_table = self._make_transition_table(row)

        # print(transition_table)
        if self.final_state not in transition_table[-1]:
            raise NonogramError('Bad transition table: final state {!r} not found'.format(
                self.final_state))

        reversed_states = list(transition_table.reverse_tracking(self.final_state))
        solved_row = (
            self._cell_value_from_solved(states)
            for states in reversed(reversed_states))

        return solved_row

    def match(self, word):
        # special case for an empty description
        if not self.description:
            word = tuple(set(word))
            if len(word) == 1:
                space = word[0]
                if space == self._space():
                    return True

        return super(NonogramFSM, self).match(word)


class _StepState(object):
    """
    Stores state of the machine,
    the link to the previous StepState object
    and the list of transitions which led to this state
    """

    __slots__ = ['state', 'previous_states']

    def __init__(self, state, prev=None, cell_type=None):
        # self.id = id(self)
        self.state = state
        self.previous_states = dict()
        self.add_previous_state(prev, cell_type)

    def add_previous_state(self, prev, cell_type):
        """
        Add transition which led to the current StepState.
        As a result it could be one or more pairs (StepState, cell_type).
        """
        if prev is not None:
            self.previous_states[prev] = cell_type

    def __str__(self):
        previous_states = sorted(
            iteritems(self.previous_states),
            key=lambda x: x[0].state)

        return '({}): [{}]'.format(
            # self.id,
            self.state,
            ', '.join('{}<-{}'.format(prev.state, cell_type)
                      for prev, cell_type in previous_states))


class TransitionTable(list):
    """
    Stores the map of all the transitions that
    can be made with given automaton for given input row
    """

    @classmethod
    def with_capacity(cls, capacity):
        """Generates a list of dicts with given capacity"""
        return TransitionTable([dict() for _ in range(capacity)])

    def append_transition(self, cell_index, state, prev=None, cell_type=None):
        """
        Add transition that shifts from `prev` StepState
        after reading `cell_index`-th cell from a row
        (which value is `cell_type`)
        to the new StepState of given `state`
        """
        transition_row = self[cell_index]
        if state in transition_row:
            # LOG.debug('State %s already exists in transition table for cell %s',
            #           state, cell_index)
            transition_row[state].add_previous_state(prev, cell_type)
        else:
            transition_row[state] = _StepState(state, prev, cell_type)

    def __str__(self):
        res = []
        for i, states in enumerate(self):
            if i > 0:
                res.append('')
            res.append(i)
            res.extend(sorted(itervalues(states), key=lambda x: x.state))
            # for state, step in iteritems(states):
            #     res.append('({}): {}'.format(state, step))

        return '\n'.join(map(str, res))

    def reverse_tracking(self, final_state):
        """
        Find all the possible reverse ways.

        Yield the actions that the machine can do
        on each step from final to initial.
        """
        possible_states = {final_state}

        # ignore the first row, it's for pre-read state
        for row in reversed(self[1:]):
            step_possible_cell_types = set()
            step_possible_states = set()

            for state in possible_states:
                step = row[state]
                for prev, cell_type in iteritems(step.previous_states):
                    step_possible_cell_types.add(cell_type)
                    step_possible_states.add(prev.state)

            possible_states = step_possible_states
            yield tuple(step_possible_cell_types)


class NonogramFSMColored(NonogramFSM):
    """
    FSM-based line solver for colored puzzles
    """

    @classmethod
    def _space(cls):
        return SPACE_COLORED

    @classmethod
    def _can_be_space(cls, cell):
        return bool(cell & cls._space())

    @classmethod
    def _types_for_cell(cls, cell):
        return two_powers(cell)

    @classmethod
    def _cell_value_from_solved(cls, states):
        # assert states.size
        return from_two_powers(states)

    def match(self, word):
        one_color_word = []

        for letter in word:
            letter = two_powers(letter)
            if len(letter) == 1:
                letter = letter[0]

            one_color_word.append(letter)

        return super(NonogramFSMColored, self).match(one_color_word)


class BaseMachineSolver(BaseLineSolver):
    """
    Nonogram line solver that uses finite state machine
    """

    def __init__(self, description, line):
        super(BaseMachineSolver, self).__init__(description, line)
        self.nfsm = self.make_nfsm(description)

    NFSM_CLASS = NonogramFSM
    FSM_CACHE = Cache(1000)

    @classmethod
    def get_state_map(cls, description):
        """
        Construct a state map
        (collection of available FSM transitions)
        from the nonogram description.
        Use cached value if available.
        """
        nfsm_cls = cls.NFSM_CLASS

        # if description and is_list_like(description[0]):
        #     nfsm_cls = NonogramFSMColored

        state_map = cls.FSM_CACHE.get(description)
        if state_map is None:
            state_map = nfsm_cls.state_map_from_description(description)
            cls.FSM_CACHE.save(description, state_map)

        return state_map

    @classmethod
    def make_nfsm(cls, *description):
        """
        Produce the black-and-white or colored
        finite state machine for nonogram solving
        """

        if len(description) == 1:
            description = description[0]
        description = normalize_description(description)

        state_map = cls.get_state_map(description)

        return cls.NFSM_CLASS(description, state_map)


class PartialMatchSolver(BaseMachineSolver):
    """
    FSM Nonogram solver that uses 'partial match' method (slow)
    """

    def _solve(self):
        return self.nfsm.solve_with_partial_match(self.line)


class BaseReverseTrackingSolver(BaseMachineSolver):
    """
    FSM Nonogram solver that uses 'reverse tracking' method (fast)
    """

    def _solve(self):
        return self.nfsm.solve_with_reverse_tracking(self.line)


class ReverseTrackingSolver(BaseReverseTrackingSolver):
    """
    FSM Nonogram solver for black and white puzzles
    """

    @classmethod
    def save_in_cache(cls, original, solved):
        super(ReverseTrackingSolver, cls).save_in_cache(original, solved)

        # it's a complete solution, so other solvers can use it too
        FastSolver.save_in_cache(original, solved)


class ReverseTrackingColoredSolver(BaseReverseTrackingSolver):
    """
    FSM Nonogram solver for colored puzzles
    """
    NFSM_CLASS = NonogramFSMColored


def assert_match(row_desc, row):
    """
    Verifies that the given row matches the description
    """

    nfsm = BaseMachineSolver.make_nfsm(row_desc)
    if not nfsm.match(row):
        raise NonogramError('The row {!r} cannot fit in clue {!r}'.format(row, row_desc))
