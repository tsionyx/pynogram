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

from pyngrm.base import BOX, SPACE, normalize_clues

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


class FiniteStateError(ValueError):
    BAD_TRANSITION = 1
    BAD_ACTION = 2

    def __init__(self, *args, **kwargs):
        self.code = kwargs.pop('code', None)
        super(FiniteStateError, self).__init__(*args)


class FiniteStateMachine(object):
    def __init__(self, initial_state, state_map, final=None):
        self.initial_state = initial_state
        self._state = initial_state
        self.state_map = OrderedDict(state_map)
        self.final_state = final

        assert self.current_state in self.states

    def transition(self, *actions):
        state = None
        for action in actions:
            state = self.transition_one(action)

        return state

    def transition_one(self, action):
        LOG.debug("Current state: '%s'", self.current_state)
        LOG.debug("Action: '%s'", action)

        if action not in self.actions:
            raise FiniteStateError("Action '{}' not available".format(
                action), code=FiniteStateError.BAD_ACTION)

        try:
            self._state = self.state_map[(self.current_state, action)]
            LOG.debug("New state: '%s'", self.current_state)
            return self.current_state
        except KeyError:
            raise FiniteStateError("Cannot do '{}' from the state '{}'".format(
                action, self.current_state), code=FiniteStateError.BAD_TRANSITION)

    @property
    def current_state(self):
        return self._state

    @property
    def states(self):
        return tuple(set(state for state, action in self.state_map))

    @property
    def actions(self):
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
            except FiniteStateError:
                LOG.info("Cannot do action '%s' in the state '%s'",
                         letter, self.current_state)
                return False

        return self.current_state == self.final_state

    def __copy__(self):
        new_one = type(self)(self.initial_state, self.state_map, final=self.final_state)
        return new_one


class NonogramFSM(FiniteStateMachine):
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
