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

from six import iteritems, text_type
from six.moves import range

from pyngrm.base import BOX, SPACE, UNSURE, normalize_clues, normalize_row

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


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

        try:
            return self.state_map[(current_state, action)]
        except KeyError:
            return None

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

        return cls(cls.INITIAL_STATE, state_map, final=state_counter)

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


def solve_row(*args):
    """
    Utility for row solving that can be used in multiprocessing map
    """
    if len(args) == 1:
        # mp's map supports only one iterable, so this weird syntax
        args = args[0]

    clues, row = args
    nfsm = NonogramFSM.from_clues(clues)
    return nfsm.solve_with_partial_match(row)
