- store colors as a set of numbers (for colored), as one of 0, 1, -16(UNKNOWN) for black-and-white. Use `np.array(dtype=np.int8)`

- check that it always a set, get rid of `is_list_like` as much as possible
- more abstractions! Make the named tuples Cell, Clue, State

- simpson refactoring: use regexp, `assert_match` with it
- coverage!
- pylint in CI
- clean:
  - check docstrings
  - check for " (replace with ')
- tornado: respond asynchronously (not in the main solving process)

- searching:
  - if too many dead ends found, just lower this path priority and try the next (see 3620):
    - add counter of dead ends for any path. If the path becomes dead_end itself,
    clear the counter for all its children.
  - found real contradictions and do not resolve them (see 3073)
  - take into account the color to search for (see 3620, 2498, 3883, 5380)
  - check on pbn=16838

- SVG:
  - fill=white
  - class for every color (use in clues)
  - shorter class and id names
  - collapse contiguous block into one long block
  - show the search in progress (dead ends, successful paths with the rate)
  - add link to the new solution page when another unique solution found
  (show the search path, compare with other solutions)

- tests for Web UI
- load board from file
- load clues from solved board (check for complexity)
- add heuristics:
  - use multiprocessing?

- solve blotted:
  19440, 19629, 19686, 19887, 20742, 20758, 20796, 21151, 21339, 22035, 22385, 22591

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
