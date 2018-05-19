# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [0.0.3] - 2018-01-11
### Added
- Initial release!
- Solve the black-and-white nonograms using several methods
- Print out the solving process on the console or the web-page (SVG)

## [0.1.0] - 2018-01-12
### Fixed
- examples distribution

## [0.1.1] - 2018-01-18
### Added
- color puzzles solver

## [0.1.2] - 2018-01-30
### Added
- choose the renderer in URL
- compress the page with gzip
- documentation with examples and references

### Fixed
- requirements for python3 (futures)
- suppress any WARNING by default (use -v)

### Removed
- demo boards
- lxml dependency (use standard XML parser)

## [0.2.0] - 2018-05-19
### Added
- adapt [Ben-Gurion University solver (BGU)](https://www.cs.bgu.ac.il/~benr/nonograms/) for better line solver
- searching-backtracking algorithm
- support for pypy (both 2 and 3). This significantly improved
the performance of terminal-based solver. However, the web version
becomes more unresponsive on any pypy interpreter, so it's recommended
to use py3 for `pynogram-web` and pypy3 for `pynogram`
- use numpy for black and white boards if available
- read local PBN-formatted puzzles
- use tornado log formatter if tornado package is available
- statistics on the most time-consuming boards (webpbn.com). See docs/benchmarks.md for details
- show the search tree at the end of solving difficult puzzles
- [Faase](http://www.iwriteiam.nl/D0601.html#3) (one of the most difficult known board) and [n-dom](http://webpbn.com/survey/dom.html) boards
- list of local boards to the web UI (_/board/local/_, _/board/local/source_)
- test for colored SVG puzzle

### Fixed
- improved some bottlenecks by profiling:
  - commenting some debug logs
  - add \_\_slots\_\_
  - do as less as possible type conversions (set to list to tuple, etc)
  - replace string color names in `ColoredBoard.cells` with their integer codes
- use named tuples `CellPosition` and `CellState`
instead of pairs and triples
- do not manipulate `Board.cells` directly anymore, use helper methods now
- [cache is more intelligent now](http://webpbn.com/survey/caching.html)
- refactor the Simpson line solver
- flake8 now checks everything
