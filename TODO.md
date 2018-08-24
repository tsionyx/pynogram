- rewrite backtracking:
  - https://ieeexplore.ieee.org/document/6476646/
  - extract probing to another module
  - flag to choose next candidates without probing
  - backjumping (too many repeating dead ends: `grep 'false' 9892.log | sed 's/^[[:space:]]*//' | sort | uniq -c | sort -nr | head`)

  - refactor names according to https://en.wikipedia.org/wiki/Backtracking and https://en.wikipedia.org/wiki/Look-ahead_(backtracking)
  - if too many dead ends found, just lower this path priority and try the next (see 3620):
    - add counter of dead ends for any path. If the path becomes dead_end itself, clear the counter for all its children.
  - re-evaluate the order of candidates after every found dead candidate and applying the partial solution
  - if for path P the pair (cell X, color C) leads to contradiction and all the other colors for X are explored fully
    (not stopped because of some limits but really fully explored!), then the P can be considered fully explored too (see 8098).
  - take into account the color to search for (see 3620, 2498, 3883, 5380)

- solve blotted:
  19407, 19440, 19629, 19686, 19887, 20742, 20758, 20796, 21151, 21339, 22035, 22385, 22591

- refactor board (extract matrix operations)

- find valid range for every color

- bgu: speed up set_line_block, can_place_block

- refactoring:
  - use https://codebeat.co
  - check docstrings (+grammarly)

- 2-SAT

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

- profile memory usage

- export to PBM, SVG, GIF (cli-options)
- import from different formats

- crypto? (easy in one direction, hard in the other)
