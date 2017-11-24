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
