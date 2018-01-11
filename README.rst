|Build Status| |Coverage Status|


Nonogram solver
===============

Solve the `nonogram puzzles`_ while seeing the process.
Currently supports black-and-white puzzles
(see file format in ``examples/hello.txt``)
with the size up to 99x99. Also you can solve puzzles
from http://webpbn.com that have thousands of them.

Install
-------

.. code-block::

    pip install pynogram

Usage
-----

Console
~~~~~~~

.. code-block::

    pynogram

    pynogram --board=winter --draw-final

    pynogram --pbn=2040

Browser
~~~~~~~

-  start the server: ``pynogram-web``

-  enjoy the solutions:

   http://localhost:3145/demo/1

   http://localhost:3145/demo/2

   http://localhost:3145/board/local/einstein

   http://localhost:3145/board/pbn/2040


.. |Build Status| image:: https://img.shields.io/travis/tsionyx/pynogram.svg
    :target: https://travis-ci.org/tsionyx/pynogram
.. |Coverage Status| image:: https://img.shields.io/coveralls/github/tsionyx/pynogram.svg
    :target: https://coveralls.io/github/tsionyx/pynogram

.. _nonogram puzzles: https://en.wikipedia.org/wiki/Nonogram


-----

The software developed and tested on Ubuntu 16.04 LTS using python versions 2.7 and 3.5.
If you have any issues, drop a line to the
`project site <https://github.com/tsionyx/pynogram/issues>`_.
