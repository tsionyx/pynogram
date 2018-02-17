- simpson refactoring
- coverage!
- pylint in CI
- clean:
  - check docstrings
  - check for " (replace with ')

- contradictions:
  - if no contradiction, then save repeated solutions
    for all the possible choices and extract intersection
    of that solution
  - check on pbn=16838

- SVG:
  - fill=white
  - class for every color (use in clues)
  - shorter class and id names
  - collapse contiguous block into one long block

- tests for Web UI
- load board from file
- load clues from solved board (check for complexity)
- add heuristics:
  - use multiprocessing?

- profile and improve bottlenecks:

```bash
$ time python -m cProfile -o hot.prof pynogram/__main__.py --pbn 2040 --draw-final
```

```
import pstats

p = pstats.Stats('hot.prof')
p.sort_stats('cumtime').print_stats('solver', 20)
p.sort_stats('ncalls').print_stats('solver', 20)
p.sort_stats('time').print_stats(50)
```

- export to PBM, SVG (cli-options)
- crypto? (easy in one direction, hard in the other)
- import from different formats
