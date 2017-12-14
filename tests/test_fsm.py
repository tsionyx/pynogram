# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from copy import copy

import pytest

from pyngrm.base import BOX, SPACE, UNSURE
from pyngrm.fsm import (
    StateMachineError,
    FiniteStateMachine,
    NonogramFSM,
    NonogramError,
    solve_row,
)


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
        assert str(fsm) == '\n'.join([
            'FiniteStateMachine(home);',
            'All states: [bed, home, work];',
            'All actions: [sleep, take train, wake];',
            'States map:',
            'bed, wake -> home',
            'home, take train -> work',
            'work, take train -> home',
            'home, sleep -> bed',
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
    def fsm(cls, *clues):
        return NonogramFSM.from_clues(*clues)

    @pytest.fixture
    def nfsm(self):
        return self.fsm(3, 2)

    def test_basic(self, nfsm):
        assert nfsm.current_state == 1
        assert nfsm.states == tuple(range(1, 8))
        assert nfsm.actions == (False, True)
        assert dict(nfsm.state_map) == {
            (1, False): 1,
            (1, True): 2,
            (2, True): 3,
            (3, True): 4,
            (4, False): 5,
            (5, False): 5,
            (5, True): 6,
            (6, True): 7,
            (7, False): 7,
        }

        nfsm.transition(False)
        assert nfsm.current_state == 1

        nfsm.transition(True)
        assert nfsm.current_state == 2

        nfsm.transition(True)
        assert nfsm.current_state == 3

        with pytest.raises(StateMachineError) as ie:
            nfsm.transition(False)

        assert ie.value.code == 1

    def test_from_list(self):
        for nfsm in (
                NonogramFSM.from_clues([1, 1]),
                NonogramFSM.from_clues(1, 1),
                NonogramFSM.from_clues('1 1'),
        ):
            assert nfsm.current_state == 1
            assert nfsm.states == (1, 2, 3, 4)
            assert nfsm.actions == (False, True)
            assert dict(nfsm.state_map) == {
                (1, False): 1,
                (1, True): 2,
                (2, False): 3,
                (3, False): 3,
                (3, True): 4,
                (4, False): 4,
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
        assert nfsm.actions == (False,)
        assert dict(nfsm.state_map) == {(1, False): 1}

    def test_matches(self, nfsm):
        assert nfsm.match([True, True, True, False, True, True])

    def test_not_matches(self, nfsm):
        assert not nfsm.match([True, True, False, True, True, True])

    def test_match_not_in_initial(self, nfsm):
        nfsm.transition(True)
        with pytest.raises(RuntimeError, match="Only run 'match' when in initial state"):
            nfsm.match([True, True, True, False, True, True])


INFORMAL_REPRESENTATIONS = {
    UNSURE: ('_', ' ', '?', '*'),
    SPACE: ('.', '0', 'O', '-'),
    BOX: ('X', '+'),
}


class TestNonogramFSMPartialMatch(TestNonogramFiniteStateMachine):
    def test_basic(self, nfsm):
        assert nfsm.partial_match(
            [UNSURE, SPACE, UNSURE, UNSURE, BOX] + [UNSURE] * 4)

        assert nfsm.partial_match('_.__X____')

    def test_not_match_too_many_spaces(self, nfsm):
        assert not nfsm.partial_match(
            [UNSURE, UNSURE, SPACE, SPACE] + [UNSURE] * 5)

        assert not nfsm.partial_match('  00     ')

    def test_not_match_too_many_boxes(self, nfsm):
        assert not nfsm.partial_match(
            [BOX] * 4 + [UNSURE] * 5)

        assert not nfsm.partial_match('++++?????')

    def test_current_state_saved(self, nfsm):
        nfsm.transition(False, True, True)
        assert nfsm.current_state == 3

        assert nfsm.partial_match([UNSURE] * 9)
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
        assert str(exc) == ("The 0 cell (None) in a row "
                            "'[None, False, None, None, False, None, None, None, None]' "
                            "cannot be neither space nor box")

    # TODO: more solved rows
    SOLVED_ROWS = [
        ('3 2', '_0__X____', [SPACE, SPACE, UNSURE, BOX, BOX, UNSURE, UNSURE, BOX, UNSURE]),
    ]

    @pytest.mark.parametrize("clues,input_row,expected", SOLVED_ROWS)
    def test_solve(self, clues, input_row, expected):
        # both arguments passes work
        assert solve_row((clues, input_row)) == expected
        assert solve_row(clues, input_row) == expected
