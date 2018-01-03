# -*- coding: utf-8 -*
"""
Grab the examples from http://webpbn.com/
"""

from __future__ import unicode_literals, print_function

from lxml import etree
from six.moves.urllib.request import urlopen

URL = 'http://webpbn.com'


def _get_puzzle_xml(_id):
    # noinspection SpellCheckingInspection
    full_url = '{}/XMLpuz.cgi?id={}'.format(URL, _id)
    return urlopen(full_url)


def _parse_clue(clue, default_color=None):
    if default_color:
        return tuple((int(block.text), block.attrib.get('color', default_color))
                     for block in clue.xpath('count'))

    return tuple(map(int, clue.xpath('count/text()')))


def get_puzzle_desc(_id):
    """Find and parse the columns and rows of a webpbn nonogram by id"""
    tree = etree.parse(_get_puzzle_xml(_id))

    colors = {color.attrib['name']: (color.text, color.attrib['char'])
              for color in tree.xpath('//color')}

    if len(colors) > 2:
        default_color = tree.xpath('//puzzle[@type="grid"]/@defaultcolor')[0]
    else:
        default_color = None

    columns = [_parse_clue(clue, default_color)
               for clue in tree.xpath('//clues[@type="columns"]/line')]
    rows = [_parse_clue(clue, default_color)
            for clue in tree.xpath('//clues[@type="rows"]/line')]

    if len(colors) > 2:
        return columns, rows, colors

    return columns, rows


if __name__ == '__main__':
    print(get_puzzle_desc(23))
    print(get_puzzle_desc(898))
