# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

from pynogram.core.common import (
    BOX, SPACE,
)

# TODO: more solved rows
CASES = [
    ([], '???', [SPACE, SPACE, SPACE]),
    ([1, 1, 5], '---#--         -      # ', [
        SPACE, SPACE, SPACE, BOX, SPACE, SPACE, None, None,
        None, None, None, None, None, None, None, SPACE,
        None, None, None, BOX, BOX, BOX, BOX, None]),
    ([9, 1, 1, 1], '   --#########-------   #- - ', [
        SPACE, SPACE, SPACE, SPACE, SPACE, BOX, BOX, BOX,
        BOX, BOX, BOX, BOX, BOX, BOX, SPACE, SPACE,
        SPACE, SPACE, SPACE, SPACE, SPACE, None, None, SPACE,
        BOX, SPACE, None, SPACE, None]),
    ([5, 6, 3, 1, 1], '               #- -----      ##-      ---   #-', [
        None, None, None, None, None, None, None, None,
        None, SPACE, None, BOX, BOX, BOX, BOX, BOX,
        SPACE, SPACE, SPACE, SPACE, SPACE, SPACE, SPACE, SPACE,
        SPACE, None, None, None, BOX, BOX, BOX, SPACE,
        None, None, None, None, None, None, SPACE, SPACE,
        SPACE, None, None, SPACE, BOX, SPACE]),
    ([4, 2], ' #   .  ', [
        None, BOX, BOX, BOX, None, SPACE, BOX, BOX]),
    ([4, 2], ' #  .   ', [
        BOX, BOX, BOX, BOX, SPACE, None, BOX, None]),
    ((1, 1, 2, 1, 1, 3, 1),
     [
         BOX, SPACE, SPACE, None, None, SPACE, None, BOX,
         None, SPACE, SPACE, BOX, None, None, None, None,
         None, BOX, None, None, None, None], [
         BOX, SPACE, SPACE, None, None, SPACE, None, BOX,
         None, SPACE, SPACE, BOX, SPACE, None, None, None,
         None, BOX, None, None, None, None]),
]

BAD_CASES = [
    ([4, 2], ' # .    '),
    ([4, 2], ' #   .# #'),
    ((5, 3, 2, 2, 4, 2, 2),
     '-#####----###-----------##-                          ###   '),
]
