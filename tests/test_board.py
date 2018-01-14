# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function

import time
from io import StringIO

import pytest

from pynogram.core.board import Board, make_board, ColoredBoard
from pynogram.core.solver import (
    line as line_solver,
    contradiction as contradiction_solver,
)
from pynogram.reader import read_example
from pynogram.renderer import (
    BaseAsciiRenderer,
    AsciiRenderer,
    AsciiRendererWithBold,
)
from pynogram.utils.other import is_close


@pytest.fixture
def tested_board(renderer=BaseAsciiRenderer, **kwargs):
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
    return Board(columns, rows, renderer=renderer, **kwargs)


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
            # noinspection PyTypeChecker
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
        return tested_board(AsciiRenderer, stream=stream)

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

        board = Board(columns, rows, renderer=AsciiRenderer, stream=stream)
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
        columns, rows = read_example('smile.txt')
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


def color_board_def():
    columns = [['1r', (1, 'b')]] * 3
    rows = ['3r', 0, '3b']
    colors = {'r': ('red', 'X'), 'b': ('blue', '*')}

    return columns, rows, colors


@pytest.fixture
def color_board(renderer=BaseAsciiRenderer, **kwargs):
    return make_board(*color_board_def(), renderer=renderer, **kwargs)


class TestMakeBoard(object):
    def test_black_and_white(self):
        columns = [3, None, 1, 1]
        rows = [
            1,
            '1 1',
            '1 1',
        ]

        b = make_board(columns, rows)
        assert isinstance(b, Board)

    # noinspection PyShadowingNames
    def test_colored(self, color_board):
        assert isinstance(color_board, ColoredBoard)

    def test_bad_make_board(self):
        with pytest.raises(ValueError, match='Bad number of \*args'):
            make_board(color_board_def()[0])


class TestColorBoard(object):
    @pytest.fixture
    def board(self):
        board_def = read_example('uk')
        return make_board(*board_def)

    def test_rows(self, board):
        assert len(board.rows_descriptions) == 15

        assert board.rows_descriptions[:2] == board.rows_descriptions[-1:-3:-1] == tuple([
            ((3, 'r'), (11, 'b'), (3, 'r'), (11, 'b'), (3, 'r')),
            ((2, 'b'), (3, 'r'), (9, 'b'), (3, 'r'), (9, 'b'), (3, 'r'), (2, 'b'))
        ])

        assert set(board.rows_descriptions[6:9]) == {((31, 'r'),)}

    def test_columns(self, board):
        assert len(board.columns_descriptions) == 31

        assert board.columns_descriptions[:2] == board.columns_descriptions[-1:-3:-1] == tuple([
            ((1, 'r'), (5, 'b'), (3, 'r'), (5, 'b'), (1, 'r')),
            ((1, 'r'), (5, 'b'), (3, 'r'), (5, 'b'), (1, 'r'))
        ])

        assert set(board.columns_descriptions[14:17]) == {((15, 'r'),)}

    def test_colors(self):
        board = make_board(*color_board_def())
        assert board.char_for_color('r') == 'X'
        assert board.rgb_for_color('b') == 'blue'

    def test_colors_conflict(self):
        columns, rows, colors = color_board_def()
        rows[0] = '3g'
        with pytest.raises(ValueError, match='Colors differ'):
            make_board(columns, rows, colors)

    def test_color_not_defined(self):
        columns, rows, colors = color_board_def()
        del colors['r']
        with pytest.raises(ValueError, match='Some colors not defined:'):
            make_board(columns, rows, colors)

    def test_color_boxes_differ(self):
        columns, rows, colors = color_board_def()
        rows[0] = '2r'
        with pytest.raises(ValueError, match='Color boxes differ:'):
            make_board(columns, rows, colors)

    def test_same_boxes_in_a_row(self):
        columns = [['1r', (1, 'b'), (1, 'b')]] * 3
        rows = ['3r', '3b', '3b']
        colors = {'r': ('red', 'X'), 'b': ('blue', '*')}

        with pytest.raises(ValueError, match='Cannot allocate row .+ in just 3 cells'):
            make_board(columns, rows, colors)

    def test_normalize(self):
        columns = [['1r', 1]] * 3
        rows = [((3, 'r'),), 0, '3']
        colors = {'r': ('red', 'X')}

        board = make_board(columns, rows, colors)

        assert board.rows_descriptions == (
            ((3, 'r'),),
            (),
            ((3, 'black'),),
        )
        assert board.columns_descriptions == (
            ((1, 'r'), (1, 'black')),
            ((1, 'r'), (1, 'black')),
            ((1, 'r'), (1, 'black')),
        )

    def test_bad_description(self):
        columns = [(('1', 'r', 1),)]
        rows = [((1, 'r'),), 0, '1']
        colors = {'r': ('red', 'X')}

        with pytest.raises(ValueError, match='Bad description block:'):
            make_board(columns, rows, colors)

    @pytest.fixture
    def stream(self):
        return StringIO()

    def test_color_renderer(self, stream):
        columns = [['1r', 1]] * 3
        rows = [((3, 'r'),), 0, '3']
        colors = {'r': ('red', '%')}

        renderer = BaseAsciiRenderer(stream=stream)
        board = make_board(columns, rows, colors, renderer=renderer)
        for i in range(3):
            board.cells[0][i] = 'r'
            board.cells[2][i] = 'black'
        # cannot do simply:
        # board.cells[2] = [True, True, True]
        # because of
        # ValueError: could not broadcast input array from shape (3) into shape (3,2)

        board.draw()

        assert stream.getvalue().rstrip() == '\n'.join([
            '# 1 1 1',
            '# 1 1 1',
            '3 % % %',
            '0 _ _ _',
            '3 X X X',
        ])

    def test_solve(self, board):
        contradiction_solver.solve(board)
        assert board.solution_rate == 1
        assert board.solved
