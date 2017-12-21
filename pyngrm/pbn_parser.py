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


def get_puzzle_desc(_id):
    """Find and parse the columns and rows of a webpbn nonogram by id"""

    tree = etree.parse(_get_puzzle_xml(_id))
    if tree.xpath('count(//color)') > 2:
        raise NotImplementedError('Cannot solve multicolored nonograms')

    columns = [tuple(map(int, clue.xpath('count/text()')))
               for clue in tree.xpath('//clues[@type="columns"]/line')]
    rows = [tuple(map(int, clue.xpath('count/text()')))
            for clue in tree.xpath('//clues[@type="rows"]/line')]
    return columns, rows


if __name__ == '__main__':
    print(get_puzzle_desc(23))
