#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import os
import sys

from setuptools import setup, find_packages, Command

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION = (0, 0, 2)
NAME = os.path.basename(CURRENT_DIR)


def read(file_name, base_dir=None):
    """
    Utility function to read the README file.
    Used for the long_description.  It's nice, because now
    1) we have a top level README file and
    2) it's easier to type in the README file than to put a raw string in below
    """
    if not base_dir:
        base_dir = CURRENT_DIR
    return open(os.path.join(base_dir, file_name)).read()


class ToxTest(Command):
    user_options = []

    def initialize_options(self):
        pass

    @classmethod
    def finalize_options(cls):
        if 'test' in sys.argv:
            sys.argv.remove('test')

    # noinspection PyPackageRequirements
    @classmethod
    def run(cls):
        import tox
        tox.cmdline()


if __name__ == '__main__':
    setup(
        name=NAME,
        version='.'.join(map(str, VERSION)),
        packages=find_packages(),
        install_requires=['six', 'numpy', 'futures', 'tornado', 'svgwrite'],
        tests_require=['tox', 'coverage', 'pytest', 'flake8'],

        # PyPI metadata
        author="Tsionyx",
        author_email="tsionyx@gmail.com",
        description="Solve nonograms automatically",
        license="MIT",
        keywords="game nonogram",
        url="https://gitlab.com/tsionyx/{}".format(NAME),

        long_description=read('README.md'),
        classifiers=[
            "Development Status :: 1 - Alpha",
            "Topic :: Game",
            "License :: OSI Approved :: MIT License",
        ],
        # TODO: force tests_require to install on test
        # try to inherit ToxTest from setuptools.command.test
        cmdclass={
            'test': ToxTest
        }
    )
