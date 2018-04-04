- backjumping:
    (many repeating dead ends: `grep 'false' 9892.log | sed 's/^[[:space:]]*//' | sort | uniq -c | sort -nr | head`)
- implement 'bgu' for colored (http://myweb.npu.edu.tw/~tcga2017/Paper_Submission_pdf/2017_TCGA_paper_5.pdf)

- Use `np.array(dtype=np.int8)` for board
- check that it always a set, get rid of `is_list_like` as much as possible
- more abstractions! Make the named tuples Cell, Clue, State

- profile and improve bottlenecks:

```bash
$ time python -m cProfile -o 2556.pypy.prof pynogram/__main__.py --pbn 2556 --draw-final
```

```
import pstats

p = pstats.Stats('9892.pypy.prof')
p_c = pstats.Stats('16838.pypy.prof')
p.sort_stats('time').print_stats(20)
p_c.sort_stats('cumtime').print_stats(20)
```

- simpson refactoring: use regexp, `assert_match` with it
- coverage!
- pylint in CI
- clean:
  - check docstrings
  - check for " (replace with ')
- tornado: respond asynchronously (not in the main solving thread)

- searching:
  - refactor according to https://en.wikipedia.org/wiki/Backtracking and https://en.wikipedia.org/wiki/Look-ahead_(backtracking)
  - if too many dead ends found, just lower this path priority and try the next (see 3620):
    - add counter of dead ends for any path. If the path becomes dead_end itself,
    clear the counter for all its children.
  - re-evaluate the order of candidates after every found dead candidate and applying the partial solution
  - if for path P the pair (cell X, color C) leads to contradiction and all the other colors for X are explored fully (not stopped because of some limits but really fully explored!), then the P can be considered fully explored too (see 8098).
  - take into account the color to search for (see 3620, 2498, 3883, 5380)

- profile memory usage


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

- solve blotted:
  19440, 19629, 19686, 19887, 20742, 20758, 20796, 21151, 21339, 22035, 22385, 22591
- export to PBM, SVG (cli-options)
- crypto? (easy in one direction, hard in the other)
- import from different formats
