# -*- coding: utf-8 -*-
"""
Defines basic finite state machine
"""

from __future__ import unicode_literals, print_function

import logging
import os

from six import iteritems, text_type

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


class FiniteStateMachine(object):
    """
    Represents a simple deterministic automaton that can be
    only in a single state in every single moment

    https://en.wikipedia.org/wiki/Finite-state_machine
    """

    __slots__ = ['initial_state', '_state', 'state_map', 'final_state']

    def __init__(self, initial_state, state_map, final=None):
        self.initial_state = initial_state
        self._state = initial_state
        self.state_map = dict(state_map)
        self.final_state = final

        # the assertion never failed but took too long, so just switch it off
        # assert self.current_state in self.states

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

        return self.state_map.get((current_state, action))

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
            for (state, action), new_state in sorted(iteritems(self.state_map))])

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
