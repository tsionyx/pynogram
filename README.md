[![pipeline status](https://gitlab.com/tsionyx/pyngrm/badges/dev/pipeline.svg)](https://gitlab.com/tsionyx/pyngrm/pipelines)
[![coverage report](https://gitlab.com/tsionyx/pyngrm/badges/dev/coverage.svg?job=test)](https://gitlab.com/tsionyx/pyngrm/commits/dev)


# Nonogram solver

### Install
```
mkvirtualenv pyngrm --python /usr/bin/python3
python setup.py install
```

### See the demo
```
python -m pyngrm

python -m pyngrm --board=winter --draw-final
```

### Demo web-server
```
python -m pyngrm.web
```

enjoy the solution process:

_http://localhost:3145/board/2_
_http://localhost:3145/board/2040_


## Tests

Currently there is no ability to run `setup.py test` to install
tests requirements (see comments in _setup.py_). Just do
`pip install tox` instead.

### Run tests

```
tox
```

### Lint the project

```
tox -e lint
```

### Benchmark on complex puzzles (remove `2>/dev/null` to see the picture)

```
# use redirection tricks to swap outputs to grep only logs, not the picture
# https://stackoverflow.com/a/2381643/1177288

# http://webpbn.com/pbnsolve.html
for i in 1611 1694 6739 4645 2040 2712 6574 8098 2556; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    time python -m pyngrm --pbn $i --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done

for i in football intermediate MLP; do
    echo "Solving local puzzle $i ..."
    time python -m pyngrm --board $i --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done
```

Currently it gives these numbers on the fast (_Intel(R) Xeon(R) CPU E3-1275 v5 @ 3.60GHz_)
and slower (_Intel(R) Core(TM) i5 CPU  M 560  @ 2.67GHz_) CPUs:

| #         | Fast CPU, sec | Slow CPU, sec | Contradiction rounds | Solution rate, % |
|-----------|--------------:|--------------:|:--------------------:|-----------------:|
| 1611      | 3.6           | 6             | 1                    | 100              |
| 1694      | 9.9           | 18            | 5                    | 100              |
| **6739**  | 7.8           | 14            | 6                    | **98.56**        |
| 4645      | 16            | 31            | 1                    | 100              |
| 2040      | 42            | 77            | 4                    | 100              |
| **2712**  | 33            | 60            | 5                    | **54.78**        |
| **6574**  | 3.6           | 6.3           | 6                    | **29.6**         |
| **8098**  | 0.9           | 1.5           | 1                    | **0**            |
| **2556**  | 1.7           | 2.9           | 2                    | **92.72**        |
|-- Local --                                                                          |
| football  | 0.7           | 1.1           | 1                    | 100              |
| intermediate | 0.8        | 1.3           | 0                    | 100              |
| MLP       | 24            | 47            | 3                    | 100              |
