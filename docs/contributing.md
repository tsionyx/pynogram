## Install

```
mkvirtualenv pynogram --python /usr/bin/python3
python setup.py develop
```


## Tests

You can run the old-school `setup.py test` or simply `tox`.

Unfortunately tests requirements do not install
automatically (see comments in _setup.py_) for now.
Just do `pip install tox` before you run test suite.


#### Lint the project

```
tox -e lint
```

Strive to keep the score 9.5 or higher.
