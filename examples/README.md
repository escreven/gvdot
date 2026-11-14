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

* **[registration.sql](registration.sql)** — Creates the
  **registration.sqlite** sample database.

* **registration.sqlite** - A sample SQLite database read by
  **[sqlite-schema.ipynb](sqlite-schema.ipynb)**.

* **[sqlite-schema.ipynb](sqlite-schema.ipynb)** — Generates schema diagrams
  from SQLite databases.  It uses `gvdot.markup` to display database tables as
  nodes and assigns multiple roles to edges to depict foreign keys.


### Directory `images/`

When run, the example notebooks save generated images to directory
`images/` if it exists.

### Requirements

All notebooks require Graphviz program `dot` to be on `PATH` and configured to
produce SVG output.  [er-diagram.ipynb](er-diagram.ipynb) and
[sqlite-schema.ipynb](sqlite-schema.ipynb) use the `neato` layout engine.
[sqlite-schema.ipynb](sqlite-schema.ipynb) uses the normally built-in `sqlite3`
module.

The `neato` layout engine is not always installed with Graphviz on Linux,
including recent versions of Ubuntu.  To enable these notebooks on Ubuntu 26.04
or later, install Graphviz with

```bash
$ sudo apt-get install --yes graphviz libgvplugin-neato-layout8
```
