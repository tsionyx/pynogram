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
python pyngrm

python pyngrm --board=winter --draw-final
```

### Demo web-server
```
python pyngrm/web/app.py
```


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
# http://webpbn.com/pbnsolve.html
for i in 1611 1694 6739 4645 2040 2712 6574 8098 2556; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    # swap outputs to grep only logs, not image
    # https://stackoverflow.com/a/2381643/1177288
    time python pyngrm --pbn $i --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done

echo "MLP"
time python pyngrm --board MLP --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
    grep -i contradict
```

Currently it gives these numbers on the fast (_Intel(R) Xeon(R) CPU E3-1275 v5 @ 3.60GHz_)
and slower (_Intel(R) Core(TM) i5 CPU  M 560  @ 2.67GHz_) CPUs:

| #         | Fast CPU, sec | Slow CPU, sec | Contradiction rounds | Solution rate, % |
|-----------|--------------:|--------------:|:--------------------:|-----------------:|
| 1611      | 3.6           | 6.3           | 1                    | 100              |
| 1694      | 19            | 42            | 5                    | 100              |
| **6739**  | 16            | 31            | 6                    | **98.56**        |
| 4645      | 19            | 36            | 1                    | 100              |
| 2040      | 72            | 144           | 4                    | 100              |
| **2712**  | 57            | 112           | 5                    | **54.78**        |
| **6574**  | 8.1           | 17            | 6                    | **29.6**         |
| **8098**  | 1.1           | 2.1           | 1                    | **0**            |
| **2556**  | 3.4           | 6.8           | 2                    | **92.72**        |
|-- Local --                                                                          |
| MLP       | 38            | 76            | 3                    | 100              |
