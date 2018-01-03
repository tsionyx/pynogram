# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import time
from io import StringIO

import pytest

from pyngrm.core.board import Board
from pyngrm.core.solve import line_solver, contradiction_solver
from pyngrm.input.reader import examples_file, read
from pyngrm.renderer import AsciiRendererWithBold, AsciiBoard
from pyngrm.utils.other import is_close


@pytest.fixture
def tested_board(board_cls=Board, **kwargs):
    """
    Very simple demonstration board with the 'P' letter

    source: https://en.wikipedia.org/wiki/Nonogram#Example
    """
    columns = [[], 9, [9], [2, 2], (2, 2), 4, '4', '']
    rows = [
        None,
        4,
        6,
        '2 2',
        [2] * 2,
        6,
        4,
        2,
        [2],
        2,
        0,
    ]
    return board_cls(columns, rows, **kwargs)


class TestBoard(object):
    @pytest.fixture
    def board(self):
        return tested_board()

    def test_rows(self, board):
        assert board.rows_descriptions == tuple([
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
        assert board.columns_descriptions == tuple([
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
            Board(columns=[2.0, 1], rows=[1, 2])

        assert str(ei.value), 'Bad row: 2.0'

    def test_columns_and_rows_does_not_match(self):
        with pytest.raises(ValueError) as ei:
            Board(columns=[1, 1], rows=[1, 2])

        assert str(ei.value), \
            'Number of boxes differs: 3 (rows) and 2 (columns)'

    def test_row_does_not_fit(self):
        with pytest.raises(ValueError) as ei:
            Board(columns=[1, 1], rows=[1, [1, 1]])

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
        line_solver.solve(board)
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
        # currently simple `solve` method does not mark the board as solved
        # assert board.solved

    def test_repeat_solutions(self, board):
        line_solver.solve(board)
        assert board.solution_rate == 1
        line_solver.solve(board)
        assert board.solution_rate == 1

    def test_several_solutions(self, stream):
        columns = [3, None, 1, 1]
        rows = [
            1,
            '1 1',
            '1 1',
        ]

        board = AsciiBoard(columns, rows, stream=stream)
        line_solver.solve(board)
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
        # currently simple `solve` method does not mark the board as solved
        # assert board.solved

    def test_bold_lines(self, stream):
        """
        M letter
        """
        columns = [5, 1, 1, 1, 5]
        rows = ['1 1', '2 2', '1 1 1', '1 1', '1 1']

        renderer = AsciiRendererWithBold(stream=stream)
        renderer.BOLD_LINE_EVERY = 2
        board = Board(columns, rows, renderer=renderer)
        line_solver.solve(board)
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

        board = Board(columns, rows)
        rows_updated = []
        cols_updated = []
        rounds = []

        board.on_row_update = lambda **kwargs: rows_updated.append(kwargs['row_index'])
        board.on_column_update = lambda **kwargs: cols_updated.append(kwargs['column_index'])
        board.on_solution_round_complete = lambda **kwargs: rounds.append(1)
        line_solver.solve(board)

        # the solution will go like following:
        # 1. draw the lower '_' in L (row 2)
        # 2. the column 0 updated
        #   3. during that update the row 0 updated
        #     4. during that update the column 1 updated

        assert rows_updated == [2, 0]
        # draw the vertical '|' in L
        # and fill the spaces on the second column
        assert cols_updated == [0, 1]

        # it takes only one round to solve that
        assert sum(rounds) == 1

    # @pytest.mark.skip('Too hard for unit tests')
    def test_various_modes(self):
        solutions = dict()

        for parallel in (False, True):
            for contradiction_mode in (False, True):
                stream = StringIO()
                board = self.board(stream=stream)
                start = time.time()

                line_solver.solve(board, parallel=parallel,
                                  contradiction_mode=contradiction_mode)
                solutions[(parallel, contradiction_mode)] = (
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


class TestContradictions(object):
    # TODO: more tests on simple contradictions boards

    def test_smile(self):
        with open(examples_file('smile.txt')) as _file:
            columns, rows = read(_file)

        board = Board(columns, rows)

        line_solver.solve(board)
        assert is_close(board.solution_rate, 0.6)
        # assert is_close(board.solution_rate, 407.0 / 625)

        contradiction_solver.solve(board, propagate_on_row=True)
        assert board.solution_rate == 1

    def test_simple(self):
        board = tested_board()
        contradiction_solver.solve(board)
        assert board.solution_rate == 1
        assert board.solved

    def test_many_solutions(self):
        # source: https://en.wikipedia.org/wiki/Nonogram#Contradictions
        columns = [3, 1, 2, 2, '1 1', '1 1']
        rows = ['1 2', 1, 1, 3, 2, 2]

        board = Board(columns, rows)

        line_solver.solve(board)
        assert board.solution_rate == 0

        contradiction_solver.solve(board)
        assert is_close(board.solution_rate, 7.0 / 9)

    def test_chessboard(self):
        """Just trying all the choices for full coverage"""

        # The real chessboard could be defined like this
        #
        # `columns = rows = [[1, 1, 1, 1]] * 8`
        #
        # but it really slows down the test.
        #
        # So we just use simple 2x2 chessboard here
        # with the same effect on test coverage

        columns = rows = [1, 1]
        board = Board(columns, rows)

        line_solver.solve(board)
        assert board.solution_rate == 0

        contradiction_solver.solve(board, by_rows=False)
        assert board.solution_rate == 0

        contradiction_solver.solve(board, propagate_on_row=True)
        assert board.solution_rate == 0

        contradiction_solver.solve(board, by_rows=False, propagate_on_row=True)
        assert board.solution_rate == 0
