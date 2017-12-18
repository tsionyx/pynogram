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
