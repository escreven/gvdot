.. currentmodule:: gvdot

.. |br| raw:: html

   <br />

Overview
========

.. _class-dot:

Class Dot
---------

The DOT language defines the input format accepted by Graphviz, a family of
programs for drawing graphs.  Class :class:`Dot` is a DOT language graph
expression.  To produce a diagram, applications create a dot object then use it
to define and amend nodes, edges, subgraphs, and graph-level attribute.
Applications can also style diagrams with themes and roles.

Once complete, applications convert the dot object to DOT language text or
render it as SVG or an image.  Notebook users can also interactively display
dot objects in Jupyter notebooks.

The string representation of a dot object is DOT language text, the same text
used when rendering the dot object.  For example,

.. include:: _static/overview/rollback.py.rst

produces

.. include:: _static/overview/rollback.dot.rst

and

.. code-block:: python

    with open("rollback.svg", "w") as f:
        print(dot.to_svg(),file=f)

renders that DOT language text as the SVG file

.. image:: _static/overview/rollback.*
    :align: center
    :alt: Example rollback diagram

|br| :class:`Dot` always produces DOT language statements and other lines in
the following order, regardless of the order in which defining :class:`Dot`
methods are called.

- Optional comment lines.
- The graph header and opening bracket (Example: ``graph mygraph {``)
- At most one graph default attributes statement.
- At most one node default attributes statement.
- At most one edge default attributes statement.
- All graph attribute assignments, excluding "label".
- One node statement per defined node.
- One (non-multigraph) or more (multigraph) edge statements per defined edge.
- Subgraphs.  Each subgraph consists of multiple lines following the same
  order as this list, except that subgraphs do not have comments and begin
  with a subgraph header.
- The graph "label" attribute, if any.  (The reason for this special case is
  that a Graphviz graph label assignment is inherited by any subgraph that
  follows it, which is undesirable.)
- The graph closing bracket

:class:`Dot` takes steps to produce readable DOT language representations:
it indents reasonably, avoids unnecessary :type:`ID` quoting (see below), and
separates sections with blank lines unless there are few statements.

IDs
---

The DOT language grammar uses non-terminal `ID` for both entity identifiers and
attribute values.  Lexically, an `ID` can be an unquoted character sequence
that looks like a number or programming language identifier, a quoted string,
or a Graphviz HTML string.  Package gvdot defines type :type:`ID` to represent
`ID` values:

.. code-block:: python

    type ID = str | int | float | bool | Markup

where :class:`Markup` is a gvdot class delineating HTML strings.

Regardless of how they appear, Graphviz does not differentiate between non-HTML
IDs; in DOT language, ``1.23`` and ``"1.23"`` are two ways to write the same
thing.  Accordingly, :class:`Dot` methods normalize non-Markup :type:`ID`
values to strings, making these two :meth:`Dot.node` calls equivalent:

.. code-block:: python

    #
    # The first argument is a node id.  Graphviz allows any ID to be
    # used as a node identifier.
    #
    dot.node(100, fontsize=12, margin=0.25, color="green")
    dot.node("100", fontsize="12", margin="0.25", color="green")

No matter how you specify :type:`ID` values, string or otherwise, :type:`Dot`
avoids unnecessary quoting.  The DOT language representation of a node defined
by either call above is

.. code-block:: graphviz

    100 [fontsize=12 margin=0.25 color=green]

The exception is that attributes that have general text values, such as labels,
are always quoted.

.. code-block:: python

    dot.edge("a", "b", penwidth=0.25, color="red", label="fine")

has the representation

.. code-block:: graphviz

    a -- b [ penwidth=0.25 color=red label="fine" ]

HTML IDs are distinct from non-HTML IDs in DOT language.  Python :type:`ID`
values ``"the<br/>end"`` and ``Markup("the<br/>end")`` have the DOT language
representations ``"the<br/>end"`` and ``<the<br/>end>`` respectively.  When
used as a label, Graphviz renders the first as text containing angle brackets
and a slash, and the second as "the" and "end" on two lines.

For convenience, because some Graphiz attributes have boolean values specified
as ``true`` or ``false``, :class:`Dot` normalizes Python bool :type:`ID` values
to those lowercase forms.

Attributes
-----------

Applications specify graph, subgraph, node, and edge attributes as keyword
arguments to dot object methods defining or amending those entities, defining
roles for those entities, or setting defaults for those entity types.

.. include:: _static/overview/attrs.py.rst

Through a combination of gvdot functionality and Graphviz built-in behavior,
the attributes values assigned above are merged together to render the diagram
as

.. image:: _static/overview/attrs.*
    :align: center
    :alt: Combination of many attributes

|br|
The DOT language representation of that dot object is

.. include:: _static/overview/attrs.dot.rst

Each keyword argument name except for ``role`` should be a Graphviz attribute
name and each value should be an :type:`ID` or ``None``.  Value ``None``
deletes the attribute from the target entity, role, or entity type default if
it was previously specified, and is ignored if not.

Running the following as a cell in a notebook

.. include:: _static/overview/change-mind.py.rst

displays two images:

.. image:: _static/overview/change-mind-1.*
    :align: center
    :alt: Unsightly edge diagram

and

.. image:: _static/overview/change-mind-2.*
    :align: center
    :alt: Better edge diagram

|br|
One Graphviz attribute, ``class``, is also a Python reserved name.  To enable
applications to specify a value for ``class`` and any future conflicting
attribute, :class:`Dot` strips one trailing underscore character from attribute
keywords if present.  Example:

.. code-block:: python

    dot.node("a", class_="important", shape_="circle")

Node ``a`` will have SVG element class ``"important"`` and shape ``"circle"``.
The underscore is required for class, and superfluous for shape.


Roles
-----

If you're familiar with Graphviz, you may wonder if gvdot's fixed statement
order precludes a common technique: restating default attributes to avoid
explicitly assigning attributes to particular nodes or edges.  Something like

- writing ``node [color="#10a010"]`` (green), then
- writing statements naming nodes deemed "normal", then
- writing ``node [color="#c00000", fontcolor="#e8e8e8"]`` (dark red with
  white text), then
- writing statements naming nodes deemed "critical", and so on.

The answer is yes --- by design.  Having to group nodes or edges together to
share a set of attribute values is awkward if the structure of the input
driving the generation does not coincide with that grouping.  Instead, gvdot
applications can assemble diagrams in any sequence that is convenient and
assign common attributes using roles.

A role is a named collection of attribute values similar to default node or
edge attributes.  Using the special attribute ```role```, applications may
assign a role to a node, edge, or graph, causing that entity to inherit the
role's attribute values.  Suppose we are modeling projects with

.. include:: _static/overview/tasks-model.py.rst

We can generate a project task diagram with

.. include:: _static/overview/tasks-gen.py.rst

We assign a role to task nodes based on (and in this case with the same name
as) the task's status.  The presentation attributes of the node are captured by
the role.  The resulting diagram might look like

.. image:: _static/overview/tasks-gen.*
    :align: center
    :alt: Task diagram with normal, at-risk, and critical tasks

|br|
Roles are not a DOT language feature, and other than the effect they have on
entity attributes do not appear in the DOT language representation.  The
attribute name ``role`` is reserved by gvdot.  Only graphs, nodes, and edges
can have attribute ``role``.

A role need not be defined before it is assigned.  However, :class:`Dot` raises
an exception if an assigned role is not defined when the application creates a
DOT language representation or rendering of a dot object.


Themes
------

A theme is a normal :class:`Dot` object from which other dot objects inherit
graph attributes, default attributes, and roles.  While a theme can have nodes,
edges, and subgraphs, those elements are ignored by :class:`Dot` objects styled
by the theme.

We can improve our task diagrammer above by pulling all presentation attributes
out of ``task_diagram()`` into a theme.

.. include:: _static/overview/theme-theme1.py.rst

This simplifies our generator to

.. include:: _static/overview/theme-code1.py.rst

Function ``task_diagram()`` generates the same diagram, but it allows the
caller to entirely specify the presentation via a theme.  Suppose that
sometimes we want to present project status in a vertically compact way.  All
we need is a new theme.

.. include:: _static/overview/theme-theme2.py.rst

We only needed to specify what differs because the compact theme inherited from
the base theme.  If we run

.. include:: _static/overview/theme-code2.py.rst

in a notebook, we see

.. image:: _static/overview/theme-image2.*
    :align: center
    :alt: Vertically compact task diagram

Edge Identity
-------------

Consistent with the DOT language, only the `id` portion of a
:class:`Port` is relevant to edge identification.  In the code below,
the first statement defines an edge, and the second amends the same
edge's attributes.

.. code-block:: python

    dot = Dot()
    dot.edge(Port("a",cp="n"), Port("b","output","s"), color="blue")
    dot.edge("a","b",style="dashed")

The outcome of calling `edge()` with the endpoint node IDs of an
already defined edge depends on the constructor `multigraph` parameter
and whether or not a discriminant is specified.

- Non-multigraph: the defined edge is amended.
- Multigraph, no discriminant: a new edge is defined
- Multigraph, distinct discriminant: a new edge is defined
- Multigraph, same discriminant: the defined edge is amended

Scoping
-------

In DOT, node identifiers are scoped to the root graph, so nodes and
edges cannot be redefined within a child.  Also, nodes and edge
attributes can be amended through any dot object in the hierarchy,
regardless of the dot object through which they were defined.

Roles are similarly scoped to the root graph.  Role specifications or
amendments made through a subgraph dot object are visible throughout
the graph.

Subgraphs, on the other hand, are scoped to their parent.  So, the
assertions below all hold.

.. code:: python

    dot = Dot()
    sub1 = dot.subgraph(id="sub1")
    sub1_sub2 = sub1.subgraph(id="sub2")
    assert dot.subgraph(id="sub1") is sub1
    assert sub1.subgraph(id="sub2") is sub1_sub2
    assert dot.subgraph(id="sub2") is not sub1_sub2

Rendering
---------

`_define` and `_update`
-----------------------
