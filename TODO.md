- pretty SVG and console (e.g. curses-based) renderers
- tests for Web UI
- profile and improve bottlenecks:

```bash
$ time python -m cProfile -o hot.prof pyngrm/__main__.py --pbn 2040 --draw-final
```

```
p = pstats.Stats('non.prof')
p.sort_stats('time').print_stats('fsm', 20)
p.sort_stats('ncalls').print_stats('fsm', 20)
```

- add heuristics:
  - which directions to solve first: rows or columns
  - use multiprocessing?
- import from different formats
- export to PBM, BMP
- make user interaction scripts
- update README with images and examples
- colored nonograms
