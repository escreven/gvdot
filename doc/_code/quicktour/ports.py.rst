.. code-block:: python

    dot = Dot(directed=True)
    dot.graph(rankdir="LR")
    dot.node_default(shape="record")
    dot.node("node1", label="First|<link>next")
    dot.node("node2", label="Second|<link>next")
    dot.node("node3", label="Third|<link>next")
    sub = dot.subgraph()
    sub.edge(Port("node1","link", "s"), Port("node2", cp="w"))
    sub.edge(Port("node2","link"), Port("node3", cp="s"))
    sub.edge(Port("node3","link"), Port("node1", cp="ne"))
