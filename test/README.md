## Organization

### Test support

| File | Description
| - | -
| [main.py](main.py) | Command line test runner
| [utility.py](utility.py) | Test predicates and setup of mock Graphviz programs

Tests are run by executing `main.py` from the command line.

```bash
$ python3 test/main.py
```

Use option `-h` to see usage.


### Test definition

| File | Functional Area
| - | -
| [core.py](core.py) | Defining and amending structural elements
| [dotcopy.py](dotcopy.py) | Dot object deep copy
| [identifiers.py](identifiers.py) | IDs and their forms, including Nonces
| [internals.py](internals.py) | Aspects that are hard to test through the public API
| [render.py](render.py) | Rendering to files, image bytes, and SVG
| [show.py](show.py) | Showing Dot object images and source in notebooks
| [styling.py](styling.py) | Roles and themes


Test definition modules include one or more functions

```
def test_<name>():
    ...
```

The test runner (`main.py`) executes these functions.
