# -*- coding: utf-8 -*
"""
Defines finite state machine to solve nonograms

See source article here (in russian):
http://window.edu.ru/resource/781/57781
"""

from __future__ import unicode_literals, print_function

import logging
import os
from collections import OrderedDict

from six import iteritems, text_type, itervalues
from six.moves import range

from pyngrm.base import BOX, SPACE, UNSURE, normalize_clues, normalize_row
from pyngrm.cache import Cache

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)

SOLUTIONS_CACHE = Cache()


class StateMachineError(ValueError):
    """
    Represents an error occurred when trying
    to make bad transition with a FSM
    """
    BAD_TRANSITION = 1
    BAD_ACTION = 2

    def __init__(self, *args, **kwargs):
        self.code = kwargs.pop('code', None)
        super(StateMachineError, self).__init__(*args)


class NonogramError(ValueError):
    """
    Represents an error occurred when trying
    to solve 'unsolvable' nonogram
    """
    pass


class FiniteStateMachine(object):
    """
    Represents a simple deterministic automaton that can be
    only in a single state in every single moment

    https://en.wikipedia.org/wiki/Finite-state_machine
    """

    def __init__(self, initial_state, state_map, final=None):
        self.initial_state = initial_state
        self._state = initial_state
        self.state_map = OrderedDict(state_map)
        self.final_state = final

        assert self.current_state in self.states

    def transition(self, *actions):
        """
        Change the state of a machine by consequently applying
        one or more `actions`
        """
        state = None
        for action in actions:
            state = self.transition_one(action)

        return state

    def transition_one(self, action):
        """
        Change the state of a machine according to the
        `self.state_map` by applying an `action`
        """
        LOG.debug("Current state: '%s'", self.current_state)
        LOG.debug("Action: '%s'", action)

        if action not in self.actions:
            raise StateMachineError("Action '{}' not available".format(
                action), code=StateMachineError.BAD_ACTION)

        new_state = self.reaction(action)
        if new_state is None:
            raise StateMachineError("Cannot do '{}' from the state '{}'".format(
                action, self.current_state), code=StateMachineError.BAD_TRANSITION)
        else:
            self._state = new_state
            LOG.debug("New state: '%s'", self.current_state)
            return self.current_state

    def reaction(self, action, current_state=None):
        """
        Returns the state in which the machine would be
        if the `action` will apply to it
        (without actual changing of the state).

        If the `current_state` is given, pretend that
        the machine is in this state before action.
        """
        if current_state is None:
            current_state = self.current_state

        return self.state_map.get((current_state, action), None)

    @property
    def current_state(self):
        """
        The current state of a machine
        """
        return self._state

    @property
    def states(self):
        """
        All the possible states of a machine
        """
        return tuple(set(state for state, action in self.state_map))

    @property
    def actions(self):
        """
        All the possible actions that can be applied to a machine
        """
        return tuple(set(action for state, action in self.state_map))

    def __str__(self):
        res = [
            '{}({});'.format(self.__class__.__name__, self.current_state),
            'All states: [{}];'.format(', '.join(sorted(map(text_type, self.states)))),
            'All actions: [{}];'.format(', '.join(sorted(map(text_type, self.actions)))),
            'States map:',
        ]
        res.extend([
            '{}, {} -> {}'.format(state, action, new_state)
            for (state, action), new_state in iteritems(self.state_map)])

        if self.final_state is not None:
            res.append('Final state: {}.'.format(self.final_state))
        return '\n'.join(res)

    def match(self, word):
        """
        Verify if the machine can accept the `word`
        i.e. reach the `self.final_state` by applying
        the words' letters one by one
        """
        if self.current_state != self.initial_state:
            raise RuntimeError("Only run '{}' when in initial state '{}'".format(
                self.match.__name__, self.initial_state))

        if self.final_state is None:
            raise RuntimeError('Cannot match: no final state defined')

        for letter in word:
            LOG.debug("Match letter '%s' of word '%s'", letter, word)
            try:
                prev = self.current_state
                self.transition(letter)
                LOG.info("Transition from '%s' to '%s' with action '%s'",
                         prev, self.current_state, letter)
            except StateMachineError:
                LOG.info("Cannot do action '%s' in the state '%s'",
                         letter, self.current_state)
                return False

        return self.current_state == self.final_state

    def __copy__(self):
        new_one = type(self)(self.initial_state, self.state_map, final=self.final_state)
        return new_one


class NonogramFSM(FiniteStateMachine):
    """
    Represents a special class of a FSM
    used to solve a nonogram
    """

    def __init__(self, clues, initial_state, state_map, final=None):
        self.clues = clues
        super(NonogramFSM, self).__init__(initial_state, state_map, final=final)

    @classmethod
    def _optional_space(cls, state):
        return (state, SPACE), state

    @classmethod
    def _required_box(cls, state):
        return (state, BOX), state + 1

    @classmethod
    def _required_space(cls, state):
        return (state, SPACE), state + 1

    INITIAL_STATE = 1

    @classmethod
    def from_clues(cls, *clues):
        """
        Construct the machine from the clues
        given in a nonogram definition
        """
        if len(clues) == 1:
            clues = clues[0]
        clues = normalize_clues(clues)
        LOG.debug('Clues: %s', clues)

        state_counter = cls.INITIAL_STATE
        state_map = []

        trans, state_counter = cls._optional_space(state_counter)
        LOG.debug('Add transition: %s -> %s', trans, state_counter)
        state_map.append((trans, state_counter))

        for i, clue in enumerate(clues):
            for _ in range(clue):
                trans, state_counter = cls._required_box(state_counter)
                LOG.debug('Add transition: %s -> %s', trans, state_counter)
                state_map.append((trans, state_counter))

            if i < len(clues) - 1:  # all but last
                trans, state_counter = cls._required_space(state_counter)
                LOG.debug('Add transition: %s -> %s', trans, state_counter)
                state_map.append((trans, state_counter))

            trans, state_counter = cls._optional_space(state_counter)
            LOG.debug('Add transition: %s -> %s', trans, state_counter)
            state_map.append((trans, state_counter))

        return cls(clues, cls.INITIAL_STATE, state_map, final=state_counter)

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
                    if cell in (BOX, UNSURE):
                        LOG.debug('Check the ability to insert BOX')

                        next_step = self.reaction(BOX, current_state=state)
                        if next_step is None:
                            LOG.debug("Cannot go from state '%s' with BOX", state)
                        else:
                            step_possible_states.append(next_step)

                    if cell in (SPACE, UNSURE):
                        LOG.debug('Check the ability to insert SPACE')

                        next_step = self.reaction(SPACE, current_state=state)
                        if next_step is None:
                            LOG.debug("Cannot go from state '%s' with SPACE", state)
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
                    "The {} cell ({}) in a row '{}' cannot be neither space nor box".format(
                        i, cell, original_row))
        return solved

    def _make_transition_table(self, row):
        row = normalize_row(row)

        # for each read cell store a list of StepState
        # plus O-th for the state before any read cells
        transition_table = TransitionTable.with_capacity(len(row) + 1)
        transition_table.append_transition(0, self.INITIAL_STATE)

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

        for i, cell in enumerate(row):
            transition_index = i + 1

            for prev_state, prev in iteritems(transition_table[i]):
                if cell in (BOX, UNSURE):
                    _shift_one_cell(BOX, transition_index,
                                    prev, prev_state)

                if cell in (SPACE, UNSURE):
                    _shift_one_cell(SPACE, transition_index,
                                    prev, prev_state)

        return transition_table

    def solve_with_reverse_tracking(self, row):
        """
        Solve the nonogram `row` using the FSM and reverse tracking
        """
        original_row, row = row, normalize_row(row)

        solved_row = SOLUTIONS_CACHE.get((self.clues, row))
        if solved_row is not None:
            assert len(solved_row) == len(row)
            return solved_row

        transition_table = self._make_transition_table(row)

        if self.final_state not in transition_table[-1]:
            raise NonogramError("The row '{}' cannot fit".format(original_row))
        # print(transition_table)

        solved_row = []
        for states in reversed(list(
                transition_table.reverse_tracking(self.final_state))):
            assert states

            if len(states) == 1:
                solved_row.append(states[0])
            else:
                solved_row.append(UNSURE)

        assert len(solved_row) == len(row)
        SOLUTIONS_CACHE.save((self.clues, row), solved_row)
        return solved_row


class _StepState(object):  # pylint: disable=too-few-public-methods
    """
    Stores state of the machine,
    the link to the previous StepState object
    and the list of transitions which led to this state
    """

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
            res.extend(itervalues(states))
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


def solve_row(*args, **kwargs):
    """
    Utility for row solving that can be used in multiprocessing map
    """
    method = kwargs.pop('method', 'reverse_tracking')

    if len(args) == 1:
        # mp's map supports only one iterable, so this weird syntax
        args = args[0]

    clues, row = args
    nfsm = NonogramFSM.from_clues(clues)

    method_func = getattr(nfsm, 'solve_with_' + method, None)
    if not method_func:
        raise AttributeError("Cannot find solving method '%s'" % method)

    return method_func(row)
