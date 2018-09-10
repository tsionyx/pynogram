# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import pytest

from pynogram.core.color import ColorBlock
from pynogram.core.common import (
    SPACE_COLORED,
    NonogramError,
    BlottedBlock,
)
from pynogram.core.line.base import TrimmedSolver

space = SPACE_COLORED
BB = BlottedBlock


def f(*args, **kwargs):
    return TrimmedSolver.starting_solved(*args, **kwargs)


class TestTrimming(object):
    def test_empty_line(self):
        assert f([], [space] * 3) == (3, 0)

    def test_solved_fully_one_block(self):
        assert f(
            [ColorBlock(2, 2)],
            [2, 2]
        ) == (2, 1)

    def test_solved_fully_one_block_leading_spaces(self):
        assert f(
            [ColorBlock(2, 2)],
            [space] * 2 + [2, 2]
        ) == (4, 1)

    def test_solved_fully_one_block_surrounded_spaces(self):
        assert f(
            [ColorBlock(2, 2)],
            [space] * 2 + [2, 2] + [space]
        ) == (5, 1)

    def test_solved_fully_same_colors(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(1, 2)],
            [space, 2, 2, space, 2, space]
        ) == (6, 2)

    def test_solved_fully_different_colors_with_space(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(2, 4)],
            [space, 2, 2, space, 4, 4]
        ) == (6, 2)

    def test_solved_fully_different_colors_without_space(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(2, 4)],
            [space, 2, 2, 4, 4]
        ) == (5, 2)

    def test_solved_fully_three_colors(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(1, 4), ColorBlock(2, 8)],
            [space, 2, 2, 4, space, space, 8, 8] + [space] * 4
        ) == (12, 3)

    def test_solved_partial_one_block(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(1, 2)],
            [space] * 3 + [space | 2] * 3
        ) == (3, 0)

    def test_solved_partial_same_colors(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(1, 2)],
            [space, 2, 2, space, space | 2]
        ) == (4, 1)

    def test_solved_partial_same_colors_second_block_not_full(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(2, 2)],
            [2, 2, space, 2, space | 2]
        ) == (3, 1)

    def test_solved_partial_different_colors_with_space(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(1, 4)],
            [space, 2, 2, space, space | 4]
        ) == (4, 1)

    def test_solved_partial_different_colors_without_space(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(1, 4)],
            [2, 2, space | 4]
        ) == (2, 1)

    def test_solved_partial_three_blocks(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(1, 4), ColorBlock(2, 4), ColorBlock(2, 2)],
            [2, 2, 4, space, 4, 4, 2, space | 2]
        ) == (6, 3)

    def test_bad_no_description_but_has_colors(self):
        with pytest.raises(NonogramError, match='^Bad block index 0'):
            f(
                [],
                [space, 2, space],
            )

    def test_bad_not_enough_line_for_block(self):
        with pytest.raises(NonogramError, match='^The 0-th block .+ cannot be allocated'):
            f(
                [ColorBlock(2, 2)],
                [space, space, 2],
            )

    def test_bad_two_blocks(self):
        with pytest.raises(NonogramError, match='^The next .+ cannot be allocated'):
            f(
                [ColorBlock(2, 2), ColorBlock(1, 2)],
                [2, 2],
            )


class TestTrimmingBlotted(object):
    def test_solved_fully_one_block(self):
        assert f(
            [ColorBlock(BB, 2)],
            [2, 2]
        ) == (2, 1)

    def test_solved_fully_one_block_leading_spaces(self):
        assert f(
            [ColorBlock(BB, 2)],
            [space] * 2 + [2, 2]
        ) == (4, 1)

    def test_solved_fully_one_block_surrounded_spaces(self):
        assert f(
            [ColorBlock(BB, 2)],
            [space] * 2 + [2, 2] + [space]
        ) == (5, 1)

    def test_solved_fully_same_colors(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(BB, 2)],
            [space, 2, 2, space, 2, space]
        ) == (6, 2)

    def test_solved_fully_different_colors_with_space_first_blot(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(2, 4)],
            [space, 2, 2, space, 4, 4]
        ) == (6, 2)

    def test_solved_fully_different_colors_with_space_second_blot(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(BB, 4)],
            [space, 2, 2, space, 4, 4]
        ) == (6, 2)

    def test_solved_fully_different_colors_with_space_both_blots(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(BB, 4)],
            [space, 2, 2, space, 4, 4]
        ) == (6, 2)

    def test_solved_fully_different_colors_without_space(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(BB, 4)],
            [space, 2, 2, 4, 4]
        ) == (5, 2)

    def test_solved_fully_three_colors(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(1, 4), ColorBlock(BB, 8)],
            [space, 2, 2, 4, space, space, 8, 8] + [space] * 4
        ) == (12, 3)

    def test_solved_partial_one_block(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(1, 2)],
            [space] * 3 + [space | 2] * 3
        ) == (3, 0)

    def test_solved_partial_same_colors_second_blot(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(BB, 2)],
            [space, 2, 2, space, space | 2]
        ) == (4, 1)

    def test_solved_partial_same_colors_both_blots(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(BB, 2)],
            [space, 2, 2, space, space | 2]
        ) == (4, 1)

    def test_solved_partial_same_colors_second_block_not_full(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(BB, 2)],
            [2, 2, space, 2, space | 2]
        ) == (3, 1)

    def test_solved_partial_different_colors_with_space(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(BB, 4)],
            [space, 2, 2, space, space | 4]
        ) == (4, 1)

    def test_solved_partial_different_colors_without_space_first_blot(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(1, 4)],
            [2, 2, space | 4]
        ) == (2, 1)

    def test_solved_partial_different_colors_without_space_second_blot(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(BB, 4)],
            [2, 2, space | 4]
        ) == (2, 1)

    def test_solved_partial_three_blocks(self):
        assert f(
            [ColorBlock(2, 2), ColorBlock(BB, 4),
             ColorBlock(2, 4), ColorBlock(BB, 2)],
            [2, 2, 4, space, 4, 4, 2, space | 2]
        ) == (6, 3)

    def test_solved_partial_remove_prefix(self):
        assert f(
            [ColorBlock(BB, 2), ColorBlock(BB, 4)],
            [space, 2, 2, 3, space, 4, 4, space | 5]
        ) == (2, 0)
