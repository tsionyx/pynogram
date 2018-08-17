# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

from copy import copy

import pytest

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE, SPACE_COLORED,
    normalize_row,
    NonogramError,
)
from pynogram.core.line import solve_line
from pynogram.core.line.machine import (
    BaseMachineSolver,
    assert_match,
)
from pynogram.utils.fsm import (
    StateMachineError,
    FiniteStateMachine,
)
from .cases import CASES

# TODO: more solved rows
CASES = CASES + [
    ('3 2', '_0__X____', [SPACE, SPACE, UNKNOWN, BOX, BOX, UNKNOWN, UNKNOWN, BOX, UNKNOWN]),
    ('2 2', '___.X_____', [UNKNOWN, UNKNOWN, UNKNOWN, SPACE, BOX, BOX, SPACE,
                           UNKNOWN, UNKNOWN, UNKNOWN]),
]


class TestFiniteStateMachine(object):
    @pytest.fixture
    def fsm(self):
        """
        https://medium.com/@brianray_7981/tutorial-write-a-finite-state-machine-to-parse-a-custom-language-in-pure-python-1c11ade9bd43
        """
        return FiniteStateMachine('home', [
            (('bed', 'wake'), 'home'),
            (('home', 'take train'), 'work'),
            (('work', 'take train'), 'home'),
            (('home', 'sleep'), 'bed'),
        ])

    def test_basic(self, fsm):
        assert fsm.current_state == 'home'
        fsm.transition('sleep')
        assert fsm.current_state == 'bed'

    def test_bad_action(self, fsm):
        with pytest.raises(StateMachineError,
                           match="Action 'eat' not available") as ie:
            fsm.transition('eat')

        exc = ie.value
        assert exc.code == 2

    def test_bad_transition(self, fsm):
        fsm.transition('take train')
        assert fsm.current_state == 'work'
        with pytest.raises(StateMachineError,
                           match="Cannot do 'sleep' from the state 'work'") as ie:
            fsm.transition('sleep')

        exc = ie.value
        assert exc.code == 1

    def test_str(self, fsm):
        # states are in alphabetical order

        assert str(fsm) == '\n'.join([
            'FiniteStateMachine(home);',
            'All states: [bed, home, work];',
            'All actions: [sleep, take train, wake];',
            'States map:',
            'bed, wake -> home',
            'home, sleep -> bed',
            'home, take train -> work',
            'work, take train -> home',
        ])

    def test_match_not_available_when_final_undefined(self, fsm):
        with pytest.raises(RuntimeError, match='Cannot match: no final state defined'):
            fsm.match(['sleep', 'wake'])

    def test_copy_all_but_current_state(self, fsm):
        fsm.transition('sleep')
        assert fsm.current_state == 'bed'
        another = copy(fsm)
        assert another.current_state == 'home'
        assert another.state_map == fsm.state_map


class TestNonogramFiniteStateMachine(object):
    @classmethod
    def fsm(cls, *description):
        return BaseMachineSolver.make_nfsm(*description)

    @pytest.fixture
    def nfsm(self):
        return self.fsm(3, 2)

    def test_basic(self, nfsm):
        assert nfsm.current_state == 1
        assert nfsm.states == tuple(range(1, 8))
        assert nfsm.actions == (SPACE, BOX)
        assert dict(nfsm.state_map) == {
            (1, SPACE): 1,
            (1, BOX): 2,
            (2, BOX): 3,
            (3, BOX): 4,
            (4, SPACE): 5,
            (5, SPACE): 5,
            (5, BOX): 6,
            (6, BOX): 7,
            (7, SPACE): 7,
        }

        nfsm.transition(SPACE)
        assert nfsm.current_state == 1

        nfsm.transition(BOX)
        assert nfsm.current_state == 2

        nfsm.transition(BOX)
        assert nfsm.current_state == 3

        with pytest.raises(StateMachineError) as ie:
            nfsm.transition(SPACE)

        assert ie.value.code == 1

    def test_from_list(self):
        for nfsm in (
                BaseMachineSolver.make_nfsm([1, 1]),
                BaseMachineSolver.make_nfsm(1, 1),
                BaseMachineSolver.make_nfsm('1 1'),
        ):
            assert nfsm.current_state == 1
            assert nfsm.states == (1, 2, 3, 4)
            assert nfsm.actions == (SPACE, BOX)
            assert dict(nfsm.state_map) == {
                (1, SPACE): 1,
                (1, BOX): 2,
                (2, SPACE): 3,
                (3, SPACE): 3,
                (3, BOX): 4,
                (4, SPACE): 4,
            }

    def test_str(self, nfsm):
        assert str(nfsm) == '\n'.join([
            'NonogramFSM(1);',
            'All states: [1, 2, 3, 4, 5, 6, 7];',
            'All actions: [False, True];',
            'States map:',
            '1, False -> 1',
            '1, True -> 2',
            '2, True -> 3',
            '3, True -> 4',
            '4, False -> 5',
            '5, False -> 5',
            '5, True -> 6',
            '6, True -> 7',
            '7, False -> 7',
            'Final state: 7.',
        ])

    def test_empty(self):
        nfsm = self.fsm()
        assert nfsm.current_state == nfsm.final_state == 1
        assert nfsm.states == (1,)
        assert len(nfsm.actions) == 1

        # if the description is empty, the previous state_map
        # from the ColoredNfsm can be cached, so we can receive SPACE_COLORED here
        action = nfsm.actions[0]
        assert action in (SPACE, SPACE_COLORED)
        assert dict(nfsm.state_map) == {(1, action): 1}

    def test_matches(self, nfsm):
        assert nfsm.match([BOX, BOX, BOX, SPACE, BOX, BOX])

    def test_not_matches(self, nfsm):
        assert not nfsm.match([BOX, BOX, SPACE, BOX, BOX, BOX])

    def test_match_not_in_initial(self, nfsm):
        nfsm.transition(BOX)
        with pytest.raises(RuntimeError, match="Only run 'match' when in initial state"):
            nfsm.match([BOX, BOX, BOX, SPACE, BOX, BOX])


class TestNonogramFSMPartialMatch(TestNonogramFiniteStateMachine):
    def test_basic(self, nfsm):
        assert nfsm.partial_match(
            [UNKNOWN, SPACE, UNKNOWN, UNKNOWN, BOX] + [UNKNOWN] * 4)

        assert nfsm.partial_match('_.__X____')

    def test_not_match_too_many_spaces(self, nfsm):
        assert not nfsm.partial_match(
            [UNKNOWN, UNKNOWN, SPACE, SPACE] + [UNKNOWN] * 5)

        assert not nfsm.partial_match('  00     ')

    def test_not_match_too_many_boxes(self, nfsm):
        assert not nfsm.partial_match(
            [BOX] * 4 + [UNKNOWN] * 5)

        assert not nfsm.partial_match('++++?????')

    def test_current_state_saved(self, nfsm):
        nfsm.transition(SPACE, BOX, BOX)
        assert nfsm.current_state == 3

        assert nfsm.partial_match([UNKNOWN] * 9)
        assert nfsm.partial_match('*********')

        assert nfsm.current_state == 3

    def test_bad_informal_representation(self, nfsm):
        with pytest.raises(ValueError) as ie:
            nfsm.partial_match('_.0_X____')

        exc = ie.value
        assert str(exc) == ("Cannot contain different representations '., 0' "
                            "of the same state 'False' in a single row "
                            "'_.0_X____'")

    def test_solve_with_partial_match_bad_row(self, nfsm):
        with pytest.raises(NonogramError) as ie:
            nfsm.solve_with_partial_match('_0__0____')

        exc = ie.value
        assert str(exc) == ('The 0 cell (None) in a row '
                            '(None, False, None, None, False, None, None, None, None) '
                            'cannot be neither space nor box')

    @pytest.mark.parametrize('description,input_row,expected', CASES)
    def test_solve(self, description, input_row, expected):
        # both arguments passes work
        # assert solve_row((description, input_row)) == expected
        assert solve_line(description, input_row, method='partial_match') == tuple(expected)

    FULLY_SOLVED = [(d, e) for (d, i, e) in CASES if UNKNOWN not in e]

    @pytest.mark.parametrize('description,solved', FULLY_SOLVED)
    def test_assert_match(self, description, solved):
        assert_match(description, solved)


class TestNonogramFSMReverseTracking(TestNonogramFiniteStateMachine):
    @pytest.mark.parametrize('description,input_row,expected', CASES)
    def test_solve(self, description, input_row, expected):
        # both arguments passes work
        # assert solve_line((description, input_row)) == tuple(expected)
        assert solve_line(description, input_row, method='reverse_tracking') == tuple(expected)

    def test_transition_table(self):
        description, row = '2 2', '___0X_____'
        nfsm = BaseMachineSolver.make_nfsm(description)

        row = normalize_row(row)
        # noinspection PyProtectedMember
        transition_table = nfsm._make_transition_table(row)
        # TODO: assert string representation
        assert str(transition_table) == '\n'.join([
            '0',
            '(1): []',
            '',
            '1',
            '(1): [1<-False]',
            '(2): [1<-True]',
            '',
            '2',
            '(1): [1<-False]',
            '(2): [1<-True]',
            '(3): [2<-True]',
            '',
            '3',
            '(1): [1<-False]',
            '(2): [1<-True]',
            '(3): [2<-True]',
            '(4): [3<-False]',
            '',
            '4',
            '(1): [1<-False]',
            '(4): [3<-False, 4<-False]',
            '',
            '5',
            '(2): [1<-True]',
            '(5): [4<-True]',
            '',
            '6',
            '(3): [2<-True]',
            '(6): [5<-True]',
            '',
            '7',
            '(4): [3<-False]',
            '(6): [6<-False]',
            '',
            '8',
            '(4): [4<-False]',
            '(5): [4<-True]',
            '(6): [6<-False]',
            '',
            '9',
            '(4): [4<-False]',
            '(5): [4<-True]',
            '(6): [5<-True, 6<-False]',
            '',
            '10',
            '(4): [4<-False]',
            '(5): [4<-True]',
            '(6): [5<-True, 6<-False]',
        ])

    def test_solve_bad_row(self):
        with pytest.raises(NonogramError) as ie:
            solve_line('1 1', '__.', method='reverse_tracking')

        assert str(ie.value) == ('ReverseTrackingSolver: Failed to solve line '
                                 '(None, None, False) with clues (1, 1): '
                                 'Bad transition table: final state 4 not found')

    def test_solve_bad_method(self):
        with pytest.raises(KeyError) as ie:
            solve_line('1 1', '___', method='brute_force')

        assert str(ie.value.args[0]) == "Cannot find solver 'brute_force'"
