# -*- coding: utf-8 -*

from __future__ import unicode_literals, print_function


def use_test_instance(test_case_cls):
    try:
        # https://stackoverflow.com/a/28612437/
        test_case_cls.runTest = lambda x: None
        test = test_case_cls()
        test.setUp()
        return test
    finally:
        del test_case_cls.runTest


def merge_dicts(*dict_args, **kwargs):
    """
    Thanks Aaron Hall http://stackoverflow.com/a/26853961/
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    _type = kwargs.get('type', dict)
    # noinspection PyCallingNonCallable
    result = _type()
    for dictionary in dict_args:
        result.update(dictionary)
    return result
