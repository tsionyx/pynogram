# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

from io import StringIO

import pytest
import time

from pyngrm.board import AsciiBoard, BaseBoard
from pyngrm.demo import p_board
from pyngrm.renderer import AsciiRendererWithBold


@pytest.fixture
def tested_board(board_cls=BaseBoard, **kwargs):
    """
    Simple example with 'P' letter

    https://en.wikipedia.org/wiki/Nonogram#Example
    """
    return p_board(board_cls, **kwargs)


class TestBoard(object):
    @pytest.fixture
    def board(self):
        return tested_board()

    def test_rows(self, board):
        assert board.horizontal_clues == tuple([
            (),
            (4,),
            (6,),
            (2, 2),
            (2, 2),
            (6,),
            (4,),
            (2,),
            (2,),
            (2,),
            (),
        ])

    def test_columns(self, board):
        assert board.vertical_clues == tuple([
            (),
            (9,),
            (9,),
            (2, 2),
            (2, 2),
            (4,),
            (4,),
            (),
        ])

    def test_bad_renderer(self):
        with pytest.raises(TypeError) as ei:
            tested_board(renderer=True)

        assert str(ei.value) == 'Bad renderer: True'

    def test_bad_row_value(self):
        with pytest.raises(ValueError) as ei:
            BaseBoard(columns=[2.0, 1], rows=[1, 2])

        assert str(ei.value), 'Bad row: 2.0'

    def test_columns_and_rows_does_not_match(self):
        with pytest.raises(ValueError) as ei:
            BaseBoard(columns=[1, 1], rows=[1, 2])

        assert str(ei.value), \
            'Number of boxes differs: 3 (rows) and 2 (columns)'

    def test_row_does_not_fit(self):
        with pytest.raises(ValueError) as ei:
            BaseBoard(columns=[1, 1], rows=[1, [1, 1]])

        assert str(ei.value), \
            'Cannot allocate row [1, 1] in just 2 cells'


class TestSolution(object):
    @pytest.fixture
    def stream(self):
        return StringIO()

    @pytest.fixture
    def board(self, stream):
        return tested_board(AsciiBoard, stream=stream)

    def test_solve(self, board, stream):
        board.solve()
        board.draw()

        assert stream.getvalue().rstrip() == '\n'.join([
            '+---+---++---+---+---+---+---+---+---+---+',
            '| # | # ||   |   |   | 2 | 2 |   |   |   |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| # | # || 0 | 9 | 9 | 2 | 2 | 4 | 4 | 0 |',
            '|===+===++===+===+===+===+===+===+===+===|',
            '|   | 0 || . | . | . | . | . | . | . | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 4 || . | X | X | X | X | . | . | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 6 || . | X | X | X | X | X | X | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| 2 | 2 || . | X | X | . | . | X | X | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '| 2 | 2 || . | X | X | . | . | X | X | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 6 || . | X | X | X | X | X | X | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 4 || . | X | X | X | X | . | . | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 || . | X | X | . | . | . | . | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 || . | X | X | . | . | . | . | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 2 || . | X | X | . | . | . | . | . |',
            '|---+---++---+---+---+---+---+---+---+---|',
            '|   | 0 || . | . | . | . | . | . | . | . |',
            '+---+---++---+---+---+---+---+---+---+---+',
        ])
        assert board.solved

    def test_several_solutions(self, stream):
        columns = [3, None, 1, 1]
        rows = [
            1,
            '1 1',
            '1 1',
        ]

        board = AsciiBoard(columns, rows, stream=stream)
        board.solve(rows_first=False)
        board.draw()

        assert stream.getvalue().rstrip() == '\n'.join([
            '+---+---++---+---+---+---+',
            '| # | # || 3 | 0 | 1 | 1 |',
            '|===+===++===+===+===+===|',
            '|   | 1 || X | . | . | . |',
            '|---+---++---+---+---+---|',
            '| 1 | 1 || X | . |   |   |',
            '|---+---++---+---+---+---|',
            '| 1 | 1 || X | . |   |   |',
            '+---+---++---+---+---+---+',
        ])

        assert board.solution_rate * 3 == 2.0
        assert board.solved

    def test_bold_lines(self, stream):
        """
        M letter
        """
        columns = [5, 1, 1, 1, 5]
        rows = ['1 1', '2 2', '1 1 1', '1 1', '1 1']

        renderer = AsciiRendererWithBold(stream=stream)
        renderer.BOLD_LINE_EVERY = 2
        board = BaseBoard(columns, rows, renderer=renderer)
        board.solve()
        board.draw()

        assert stream.getvalue().rstrip() == '\n'.join([
            '+---+---+---+++---+---++---+---++---+',
            '| # | # | # ||| 5 | 1 || 1 | 1 || 5 |',
            '|===+===+===+++===+===++===+===++===|',
            '|   | 1 | 1 ||| X | . || . | . || X |',
            '|---+---+---+++---+---++---+---++---|',
            '|   | 2 | 2 ||| X | X || . | X || X |',
            '|===+===+===+++===+===++===+===++===|',
            '| 1 | 1 | 1 ||| X | . || X | . || X |',
            '|---+---+---+++---+---++---+---++---|',
            '|   | 1 | 1 ||| X | . || . | . || X |',
            '|===+===+===+++===+===++===+===++===|',
            '|   | 1 | 1 ||| X | . || . | . || X |',
            '+---+---+---+++---+---++---+---++---+',
        ])

    def test_callbacks(self):
        # 'L' letter
        columns = [3, 1]
        rows = [1, 1, 2]

        board = BaseBoard(columns, rows)
        rows_updated = []
        cols_updated = []
        rounds = []

        board.on_row_update = lambda **kwargs: rows_updated.append(kwargs['row_index'])
        board.on_column_update = lambda **kwargs: cols_updated.append(kwargs['column_index'])
        board.on_solution_round_complete = lambda **kwargs: rounds.append(1)
        board.solve()

        # draw the lower '_' in L
        assert rows_updated == [2]
        # draw the vertical '|' in L
        # and fill the spaces on the second column
        assert cols_updated == [0, 1]

        # it takes only one round to solve that
        assert sum(rounds) == 1

    # @pytest.mark.skip('Too hard for unit tests')
    def test_various_modes(self):
        solutions = dict()

        for parallel in (False, True):
            for rows_first in (False, True):
                stream = StringIO()
                board = p_board(stream=stream)
                start = time.time()

                board.solve(rows_first=rows_first, parallel=parallel)
                solutions[(rows_first, parallel)] = (
                    stream.getvalue().rstrip(), time.time() - start)

        assert len(solutions) == 4
        assert len(set(v[0] for v in solutions.values())) == 1

        # multiprocessing should be faster in general
        # but on the small board like this it could be slower also
        #
        # solutions = {k: v[1] for k, v in solutions.items()}
        # mp = solutions[(True, True)] + solutions[(True, False)]
        # sp = solutions[(False, True)] + solutions[(False, False)]
        # assert mp < sp
