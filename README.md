# Solve nonograms automatically

### Install
```
mkvirtualenv pyngrm --python /usr/bin/python3
python setup.py install
```

### See the demo
```
python pyngrm
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
