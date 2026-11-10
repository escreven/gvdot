.. code-block:: python

    from gvdot.markup import Table, TR, TD, Font, Bold

    def tagged_label(tag:str, label:str):
        return Table(
            cellspacing=0, cellborder=0, border=1).add(
            TR(TD(Font(tag, point_size=8), bgcolor="#ddd"),
               TD(Font(Bold(label), color="#448"), bgcolor="#fff")))

    dot = Dot(directed=True)
    dot.graph_default(bgcolor="darkolivegreen3")
    dot.node_default(shape="plain", fontsize=10, fontname="sans-serif")
    dot.edge_default(dir="back")
    dot.node(1, label=tagged_label("abstract","Mapping"))
    dot.node(2, label=tagged_label("abstract","MutableMapping"))
    dot.node(3, label=tagged_label("concrete","MappingProxyType"))
    dot.edge(1,2).edge(1,3)
