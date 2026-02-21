.. currentmodule:: gvdot

.. |br| raw:: html

   <br />

Discussion
==========

.. _class-dot:

Class Dot
---------

Graphviz is a family of programs for drawing graphs.  The input to these
programs is a graph expression written in the `DOT language
<https://graphviz.org/doc/info/lang.html>`_.  Class :class:`Dot` is a DOT
language builder.  To produce a diagram, applications create a Dot object then
use it to define and amend nodes, edges, subgraphs, and graph-level attributes.
Applications can also style diagrams with themes and roles.  Once complete,
applications convert the object to DOT language text or render it as SVG or an
image.  Notebook users can also interactively display Dot objects in Jupyter
notebooks.

The string representation of a Dot object is DOT language text, the same text
used when rendering the Dot object.  For example,

.. include:: _code/discussion/rollback.py.rst

produces

.. include:: _code/discussion/rollback.dot.rst

and

.. code-block:: python

    dot.save("rollback.svg")

renders that DOT language text as the SVG file

.. image:: _static/discussion/rollback.*
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
- One (non-multigraph) or more (multigraph) edge statements per node pair
  between which there is a defined edge.  Those node pairs are ordered for
  directed graphs and unordered otherwise.
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

    type ID = str | int | float | bool | Markup | Nonce

where :class:`Markup` is a gvdot class delineating HTML strings and
:class:`Nonce` is a placeholder for generated IDs described in a later section.

Regardless of how they appear, Graphviz does not differentiate between non-HTML
IDs; in DOT language, ``1.23`` and ``"1.23"`` are two ways to write the same
thing.  Accordingly, :class:`Dot` methods normalize non-Markup :type:`ID`
values to strings, making these two calls equivalent:

.. code-block:: python

    #
    # The first argument is a node identifier.  Graphviz allows any ID
    # to be used as a node identifier.
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

    a -- b [penwidth=0.25 color=red label="fine"]

HTML IDs `are` distinct from non-HTML IDs in DOT language.  Python :type:`ID`
values ``"the<br/>end"`` and ``Markup("the<br/>end")`` have the DOT language
representations ``"the<br/>end"`` and ``<the<br/>end>`` respectively.  When
used as a label, Graphviz renders the first as text containing angle brackets
and a slash, and the second as "the" and "end" on two lines.

For convenience, because some Graphviz attributes have boolean values specified
as ``true`` or ``false``, :class:`Dot` normalizes Python bool :type:`ID` values
to those lowercase forms.

Attributes
-----------

Applications specify graph, subgraph, node, and edge attributes as keyword
arguments to :class:`Dot` methods defining or amending those entities, defining
roles for those entities, or setting defaults for those entity types.

.. include:: _code/discussion/attrs.py.rst

Through a combination of gvdot functionality and Graphviz built-in behavior,
the attribute values assigned above are merged together to render the Dot
object as

.. image:: _static/discussion/attrs.*
    :align: center
    :alt: Combination of many attributes

|br| The DOT language representation of the Dot object is

.. include:: _code/discussion/attrs.dot.rst

Each keyword argument name except for ``role`` should be a Graphviz attribute
name and each value should be an :type:`ID` or ``None``.  Value ``None``
deletes the attribute from the target entity, role, or entity type default if
it was previously specified.  If the attribute was not previously specified,
the assignment to ``None`` has no effect.

Running the following as a cell in a notebook

.. include:: _code/discussion/change-mind.py.rst

displays two images:

.. image:: _static/discussion/change-mind-1.*
    :align: center
    :alt: Unsightly edge diagram

and

.. image:: _static/discussion/change-mind-2.*
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
edge attributes.  Using the special attribute ``role``, applications may
assign a role to a node, edge, or graph, causing that entity to inherit the
role's attribute values.  Suppose we are modeling projects with

.. include:: _code/discussion/project-model.py.rst

We can generate a project task diagram with

.. include:: _code/discussion/project-roles-code.py.rst

We assign a role to task nodes based on (and in this case with the same name
as) the task's status.  The presentation attributes of the node are captured by
the role.  The resulting diagram might look like

.. image:: _static/discussion/project-roles-image.*
    :align: center
    :alt: Task diagram with normal, at-risk, and critical tasks

|br|
Roles are not a DOT language feature, and other than the effect they have on
entity attributes do not appear in the DOT language representation.  The
attribute name ``role`` is reserved by gvdot.  Only graphs, nodes, and edges
can have attribute ``role``.

A role need not be defined before it is assigned.  However, :class:`Dot` raises
an exception if an assigned role is not defined when the application creates a
DOT language representation or rendering of a Dot object.

Themes
------

A theme is a normal :class:`Dot` object from which other Dot objects inherit
graph attributes, default attributes, and roles.  While a theme can have nodes,
edges, and subgraphs, those entities are ignored by Dot objects styled by the
theme.  Also, whether or not a theme is directed, multigraph, or strict is
irrelevant.

We can improve our task diagrammer above by pulling all presentation attributes
out of ``task_diagram()`` into a theme.

.. include:: _code/discussion/project-themes-theme1.py.rst

This simplifies our generator to

.. include:: _code/discussion/project-themes-code1.py.rst

The revised ``task_diagram()`` generates the same diagram while allowing the
caller to entirely specify the presentation via a theme.  Suppose that
sometimes we want to present project status in a vertically compact way.  All
we need is a new theme.

.. include:: _code/discussion/project-themes-theme2.py.rst

We only specified what differs because the compact theme inherits from the base
theme.  When we run

.. include:: _code/discussion/project-themes-code2.py.rst

in a notebook, we see

.. image:: _static/discussion/project-themes-image2.*
    :align: center
    :alt: Vertically compact task diagram

|br|

Subgraphs
---------

Class :class:`Block` is a scope for graph and default attribute assignments and
a container for node, edge, and subgraph definitions.  It is the base class of
:class:`Dot`, and most methods for building DOT language are actually
:class:`Block` methods.  You can think about class :class:`Block` as being an
analogue of ``graph`` and ``subgraph`` curly brackets in the DOT language.

Methods :meth:`~Block.subgraph` and :meth:`~Block.subgraph_define` return Block
objects.  A Dot object created by the :class:`Dot` constructor with descendant
Block objects created through methods :meth:`subgraph` or
:meth:`subgraph_define` form a tree.  That tree is mirrored by the ``subgraph``
statement hierarchy of the DOT language representation of the Dot object.

Node and edge identities are global within a Dot object.  They may only be
defined once, but can be amended any number of times through the Dot object or
any Block object in the tree.  The Block object through which a node or edge is
defined determines where it will appear in the subgraph hierarchy and,
therefore, the set of default attributes which apply to the node or edge.

.. code-block:: python

    dot = Dot(id="Root")
    sub = dot.subgraph(id="Sub")
    subsub = sub.subgraph(id="SubSub")

    assert type(dot) is Dot and isinstance(dot, Block)
    assert type(sub) is Block
    assert type(subsub) is Block

    dot.node("a")
    dot.edge("a","b")
    subsub.node("b")
    subsub.edge("b","c")

    dot.node_default(fontsize=10).edge_default(fontsize=10)
    sub.node_default(color="green").edge_default(color="green")
    subsub.node_default(penwidth=2).edge_default(penwidth=2)

The :class:`Dot` instance defined above has the DOT language representation

.. code-block:: graphviz

    graph Root {
        node [fontsize=10]
        edge [fontsize=10]
        a
        a -- b
        subgraph Sub {
            node [color=green]
            edge [color=green]
            subgraph SubSub {
                node [penwidth=2]
                edge [penwidth=2]
                b
                b -- c
            }
        }
    }

Node ``a`` and edge ``a -- b`` have ``fontsize`` 10 with ``color`` and
``penwidth`` unspecified, whereas node ``b`` and edge ``b -- c`` have
``fontsize`` 10, and also ``color`` green and ``penwidth`` 2.

If a subgraph is a cluster, some Graphviz layout engines (including the default
engine, dot) will place all nodes defined within the subgraph together in the
layout.  Therefore, the Block object through which a node is defined may
determine its placement.

Roles are also global within a Dot object.  They may be assigned to any entity
of the associated kind without regard to the Block object through which the
entity is defined.  However, roles may only be defined and amended through the
Dot object.

Subgraphs are scoped to their parent.  So, the assertions below all hold.

.. code:: python

    dot = Dot()
    sub1 = dot.subgraph(id="sub1")
    sub1_sub2 = sub1.subgraph(id="sub2")
    assert dot.subgraph(id="sub1") is sub1
    assert sub1.subgraph(id="sub2") is sub1_sub2
    assert dot.subgraph(id="sub2") is not sub1_sub2

Multigraphs
-----------

By default, the DOT language representation of a :class:`Dot` object has no
more than one edge statement for any pair of nodes (ordered pairs for directed
graphs).  In the code below

.. include:: _code/discussion/multigraph-stage1.py.rst

the second and third :meth:`~Block.edge` calls amend the edge ``a -- b``,
resulting in

.. list-table::
   :widths: 65 35
   :align: center
   :class: .gvdot-example-table

   * - .. include:: _code/discussion/multigraph-stage1.dot.rst

     - .. image:: _static/discussion/multigraph-stage1.*
          :alt: One edge amended twice

If we construct the :class:`Dot` object as a multigraph,

.. include:: _code/discussion/multigraph-stage2.py.rst

each :meth:`~Block.edge` call defines a new edge.  Now we get

.. list-table::
   :widths: 65 35
   :align: center
   :class: .gvdot-example-table

   * - .. include:: _code/discussion/multigraph-stage2.dot.rst

     - .. image:: _static/discussion/multigraph-stage2.*
        :align: center
        :alt: Three distinct edges

But what if we want to amend a multigraph edge?  For that we use
`discriminants`, a third component to edge identity used in multigraphs.  The
:meth:`~Block.edge` method is declared as

.. code-block:: python

    def edge(self, point1:ID|Port, point2:ID|Port,
             discriminant:ID|None=None, /, **attrs:ID|None) -> Dot:

The ``discriminant`` parameter is a value allowing an application to refer to
multigraph edges.  Discriminants are not required in multigraphs, and if
provided need only be unique among the edges of their associated node pair.

.. include:: _code/discussion/multigraph-stage3.py.rst

.. list-table::
   :widths: 65 35
   :align: center
   :class: .gvdot-example-table

   * - .. include:: _code/discussion/multigraph-stage3.dot.rst

     - .. image:: _static/discussion/multigraph-stage3.*
        :align: center
        :alt: The second is now amended

Discriminants are a gvdot feature.  As you can see, they don't appear in the
DOT language representation.  We used integer discriminants in this example
because it was convenient, but discriminants can be any :type:`ID`.

Nonces
------

Applications that generate Graphviz diagrams often need to synthesize
identifiers for nodes and sometimes subgraphs.  Consider the NFA example on
:doc:`the landing page <index>`.  To depict an arrow leading into the start
state,

.. image:: _static/discussion/nfa-init.*
    :alt: NFA start state
    :align: center

|br| we use an edge to the start state from an initial node assigned role
``"init"`` defined as

.. code-block:: python

    node_role("init", label="", shape="none", width=0, height=0)

The ``"init"`` role attributes make the initial node invisible.  We create the
initial node and edge at the bottom of the fragment below.

.. code-block:: python

    def nfa_diagram(nfa:NFA, title:str):

        dot = Dot(directed=True).use_theme(nfa_theme)
        dot.graph(label=Markup(f"<b>{title}<br/></b>"))

        init_id = ... # <-- What to put here?
        dot.node(init_id, role="init")
        dot.edge(init_id, nfa.start)
        ...

But what :type:`ID` should we assign to ``init_id``?  The remainder of the
generation code creates state nodes with identifiers that are the state name.
If we pick something like ``"_init_"``, we either must enforce a state name
restriction, complicate our generation code with some kind of indirection, or
hope the input source isn't malicious.

The gvdot solution is class :class:`Nonce`. A Nonce is a placeholder that
:class:`Dot` resolves to a unique DOT language ID when generating DOT language
representations.  Using :class:`Nonce`, the code above becomes

.. code-block:: python

    def nfa_diagram(nfa:NFA, title:str):

        dot = Dot(directed=True).use_theme(nfa_theme)
        dot.graph(label=Markup(f"<b>{title}<br/></b>"))

        init_id = Nonce()  # <-- Will resolve to a unique DOT language ID
        dot.node(init_id, role="init")
        dot.edge(init_id, nfa.start)
        ...

The DOT language representation of the NFA diagram includes the node and edge
statements

.. code-block:: graphviz

    _nonce_1 [label="" shape=none width=0 height=0]
    _nonce_1 -> s0

Suppose the NFA definition is modified so that one of the states is named
``"_nonce_1"``.  Then those statements would become

.. code-block:: graphviz

    _nonce_2 [label="" shape=none width=0 height=0]
    _nonce_2 -> s0

:class:`Dot` chooses a different ID for the Nonce to avoid a conflict with
``_nonce_1``.

:class:`Nonce` is a member of the :type:`ID` type union, so instances can be
used everywhere in the gvdot API where :type:`ID` is accepted.

Both the :doc:`er-diagram` and :doc:`rb-trees` examples in this document use
Nonces.  The ER Diagram generator uses :class:`Nonce` to synthesize identifiers
for nodes representing entity attributes.  Entity attribute names can't be
used because they are not unique within a model.  The red-black tree generator
creates phantom nodes with :class:`Nonce` identifiers to steer Graphviz toward
a good tree layout.

Rendering
---------

Package gvdot executes Graphviz programs to render :class:`Dot` objects.  The
input to these programs is the DOT language representation you can see with

.. code-block:: python

    dot = task_diagram(project)
    print(dot)

or in a notebook

.. code-block:: python

    dot = task_diagram(project)
    dot.show_source()

Method :meth:`Dot.to_rendered` is the core rendering method.  It accepts
several optional arguments including the program to run and the output format
desired.  If the execution succeeds, it returns the raw bytes the program
writes to stdout.

.. code-block:: python

    dot = task_diagram(project)
    data = dot.to_rendered(dpi=300)
    assert type(data) is bytes

Here we ran the default program ``dot`` to render the task diagram into the
default format ``png``.   We specified the image should be generated with a
resolution of 300 dots per inch.

:class:`Dot` includes three other rendering methods which all call :meth:`~Dot.to_rendered`:

- :meth:`Dot.to_svg` renders to SVG and returns the result as a string.
- :meth:`Dot.save` renders and saves to a file.
- :meth:`Dot.show` renders and displays the result in a notebook.


Defining and Amending
---------------------

The terms "define", "establish", and "amend" are used throughout the
:ref:`reference-doc`, sometimes together as "define or amend" or "establish or
amend".  In the context of gvdot method descriptions,

- `define` means create a node, edge, subgraph, or role and assign initial
  attribute values if applicable.  Defined nodes, edges, and subgraphs will
  appear as statements in the DOT language representation.  Defined roles are
  recorded for resolution in that representation.

- `establish` means assign initial graph, default graph, default node, or
  default edge attribute values.

- `amend` means make additional attribute value assignments to already defined
  or established entities, roles, and defaults, overwriting existing
  assignments with the same attribute names.  In the case of edges, amend also
  means potentially changing an endpoint's :class:`port specification <Port>`.
  In the case of subgraphs, the :ref:`reference-doc` uses the phrase "prepare
  to amend" because the relevant methods return a reference through which the
  application may modify the subgraph.

The core methods for building out the structure of a diagram are
:meth:`~Block.node`, :meth:`~Block.edge`, and :meth:`~Block.subgraph`.  These
methods are "define or amend" --- they define an entity if it doesn't exist,
and amend it otherwise.  Variants :meth:`~Block.node_define`,
:meth:`~Block.edge_define`, and :meth:`~Block.subgraph_define` raise exceptions
if the entity is already defined, while :meth:`~Block.node_update`,
:meth:`~Block.edge_update`, and :meth:`~Block.subgraph_update` raise exceptions
if it is not.  The "define and amend" versions have the advantage of giving
code a clean, declarative feel.  The ``..._define`` and ``..._update`` variants
can make buggy code fail faster.
