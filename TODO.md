- contradictions:
  - try all the choices for every cell at once, then go to another cell
  - find next cell for contradiction search on some criterion
  - try until it stalls for all the choices
  - if one of the choices comes to full solution
    but another choices all to contradictions:
    Hooray! It's the only solution we search.
  - if no contradiction, then save repeated solutions
    for all the possible choices and extract intersection
    of that solution
  - check on pbn=16838

- SVG:
  - fill=white
  - class for every color (use in clues)
  - shorter class and id names
  - collapse contiguous block into one long block


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
