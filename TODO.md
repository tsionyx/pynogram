- find a way to include examples in the distribution
- improve docs:
  - more info in README: links to other solvers, publications
  - images and examples

- clean:
  - check docstrings
  - check for " (replace with ')

- tests for Web UI

-- github, [PyPi](http://the-hitchhikers-guide-to-packaging.readthedocs.io/en/latest/quickstart.html)

- load board from file
- load clues from solved board (check for complexity)
- find next point or line to solve based on some score
- add heuristics:
  - which directions to solve first: rows or columns
  - use multiprocessing?

- colored nonograms
- profile and improve bottlenecks:

```bash
$ time python -m cProfile -o hot.prof pynogram/__main__.py --pbn 2040 --draw-final
```

```
import pstats

p = pstats.Stats('hot.prof')
p.sort_stats('time').print_stats('sover', 20)
p.sort_stats('ncalls').print_stats('solver', 20)
```

- export to PBM, SVG (cli-options)
- crypto? (easy in one direction, hard in the other)
- import from different formats
