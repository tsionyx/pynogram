[![pipeline status](https://gitlab.com/tsionyx/pyngrm/badges/dev/pipeline.svg)](https://gitlab.com/tsionyx/pyngrm/pipelines)
[![coverage report](https://gitlab.com/tsionyx/pyngrm/badges/dev/coverage.svg?job=test)](https://gitlab.com/tsionyx/pyngrm/commits/dev)


# Nonogram solver

## Install

```
mkvirtualenv pyngrm --python /usr/bin/python3
python setup.py install
```

## Usage

### See the demo in terminal

```
python -m pyngrm

python -m pyngrm --board=winter --draw-final
```

### Web demo

- start the server: `python -m pyngrm.web`
- enjoy the solutions:

  _http://localhost:3145/demo/2_

  _http://localhost:3145/board/local/einstein_

  _http://localhost:3145/board/pbn/2040_


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

for i in football einstein MLP; do
    echo "Solving local puzzle $i ..."
    time python -m pyngrm --board $i --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done
```

Currently it gives these numbers on the fast (_Intel(R) Xeon(R) CPU E3-1275 v5 @ 3.60GHz_)
and slower (_Intel(R) Core(TM) i5 CPU  M 560  @ 2.67GHz_) CPUs:

| Name      | Fast CPU, sec | Slow CPU, sec | Contradiction rounds | Solution rate, % |
|-----------|--------------:|--------------:|:--------------------:|-----------------:|
|-- webpbn.com --                                                                     |
| 1611      | 1.21          | 2.15          | 1                    | 100              |
| 1694      | 8.91          | 16.20         | 5                    | 100              |
| **6739**  | 7.62          | 13.96         | 7                    | **98.56**        |
| 4645      | 6.34          | 12.01         | 1                    | 100              |
| 2040      | 36.04         | 67.02         | 4                    | 100              |
| **2712**  | 34.02         | 61.39         | 6                    | **54.78**        |
| **6574**  | 3.82          | 6.84          | 7                    | **29.6**         |
| **8098**  | 0.86          | 1.32          | 1                    | **0**            |
| **2556**  | 1.83          | 3.12          | 3                    | **92.72**        |
|-- Local --                                                                          |
| [football](examples/football.txt) | 0.63  | 1.04  | 1            | 100              |
| [einstein](examples/einstein.txt) | 0.86  | 1.58  | 0            | 100              |
| [MLP](examples/MLP.txt)           | 18.90 | 35.08 | 3            | 100              |
