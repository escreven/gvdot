.. code-block:: python

    from gvdot import Dot, Port
    from gvdot.markup import Table, TR, TD, BR

    dot = Dot(directed=True, id="structs")
    dot.node_default(shape="plaintext")

    dot.node("struct1", label=Table(
        border=0, cellborder=1, cellspacing=0).add(
        TR(TD("left"), TD("mid dle", port="f1"), TD("right", port="f2")),
    ))

    dot.node("struct2", label=Table(
        border=0, cellborder=1, cellspacing=0).add(
        TR(TD("one", port="f0"), TD("two")),
    ))

    dot.node("struct3", label=Table(
        border=0, cellborder=1, cellspacing=0, cellpadding=4).add(
        TR(TD("hello", BR(), "world", rowspan=3),
        TD("b", colspan=3),
        TD("g", rowspan=3),
        TD("h", rowspan=3)),
        TR(TD("c"), TD("d", port="here"), TD("e")),
        TR(TD("f", colspan=3)),
    ))

    dot.edge(Port("struct1", "f1"), Port("struct2", "f0"))
    dot.edge(Port("struct1", "f2"), Port("struct3", "here"))
