#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import os

from setuptools import setup, find_packages

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION = (0, 0, 1)
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


setup(
    name=NAME,
    version='.'.join(map(str, VERSION)),
    packages=find_packages(),
    install_requires=['six'],

    # PyPI metadata
    author="Tsionyx",
    author_email="tsionyx@gmail.com",
    description="Solve nanograms automatically",
    license="MIT",
    keywords="game nanogram",
    url="https://gitlab.com/tsionyx/{}".format(NAME),

    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Topic :: Game",
        "License :: OSI Approved :: MIT License",
    ],
)
