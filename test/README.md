## Organization

### Test support

| File | Description
| - | -
| [main.py](main.py) | Command line test runner
| [utility.py](utility.py) | Test predicates and setup of mock Graphviz programs

Tests are run by executing [main.py](main.py) from the command line.

```bash
$ python3 test/main.py
```

Use option `-h` to see usage.


### Test definition

| File | Functional Area
| - | -
| [core.py](core.py) | Defining and amending structural elements
| [frontend.py](frontend.py) | Display through notebook frontends
| [dotcopy.py](dotcopy.py) | Dot object deep copy
| [identifiers.py](identifiers.py) | IDs and their forms, including Nonces
| [impose_order.py](impose_order.py) | The impose_order() function
| [internals.py](internals.py) | Aspects that are hard to test through the public API
| [render.py](render.py) | Rendering to files, image bytes, and SVG
| [show.py](show.py) | Showing Dot object images and source in notebooks
| [styling.py](styling.py) | Roles and themes


Test definition modules include one or more functions

```
def test_<name>():
    ...
```

The test runner [main.py](main.py) executes these functions.

Both [show.py](show.py) and [frontend.py](frontend.py) test `gvdot` notebook functionality.  The
difference is that [show.py](show.py) injects a mock IPython interface to test
`Dot.show()` and `Dot.show_source()` behavior, while [frontend.py](frontend.py) acts as an
IPython frontend, running `gvdot` in a real IPython kernel verifying that
images, code blocks, and markdown blocks displayed by those methods are
actually transmitted to the frontend.

## Requirements

[render.py](render.py) includes tests that invoke the `dot` and `neato`
programs to generate both SVG and PNG output.  By default, [main.py](main.py)
probes the Graphviz installation before running any tests, verifying that `dot`
and `neato` can be invoked and support the SVG and PNG output formats.

The `neato` layout engine is not always installed with Graphviz on Linux,
including recent versions of Ubuntu.  To enable these tests on Ubuntu 26.04 or
later, install Graphviz with

```bash
$ sudo apt-get install --yes graphviz libgvplugin-neato-layout8
```
