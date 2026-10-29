### Files

* **[er-diagram.ipynb](er-diagram.ipynb)** — Begins with a transcription of a
  [Graphviz gallery](https://graphviz.org/gallery) Entity Relationship Diagram,
  then shows how to generate equivalent diagrams from models using themes,
  roles, and nonces.

* **[nfa.ipynb](nfa.ipynb)** — Demonstrates nondeterministic finite automata
  diagram generation from an NFA definition.

* **[quicktour.ipynb](quicktour.ipynb)** — Walks concisely through gvdot.

* **[red-black-tree.ipynb](red-black-tree.ipynb)** — Uses an included red-black
  tree implementation to produce illustrations for students.  The generator
  relies on nonces to create phantom nodes steering Graphviz toward better tree
  layouts.


### Directory `images/`

When run, the example notebooks save generated images to directory
`images/` if it exists.

### Requirements

Notebooks [nfa.ipynb](nfa.ipynb), [quicktour.ipynb](quicktour.ipynb),
and [red-black-tree.ipynb](red-black-tree.ipynb) require Graphviz program
`dot` to be on the path, while [er-diagram.ipynb](er-diagram.ipynb)
requires `neato` to be on the path.  Both Graphviz programs must be configured
to produce SVG output.

The `neato` layout engine is not always installed with Graphviz on Linux,
including recent versions of Ubuntu.  To enable these notebooks on Ubuntu 26.04
or later, install Graphviz with

```bash
$ sudo apt-get install --yes graphviz libgvplugin-neato-layout8
```
