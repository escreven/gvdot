.. code-block:: python

    dot = Dot(directed=True)
    dot.graph(label="Basic Construction", rankdir="LR")
    dot.node("a", label="Node A", shape="box")
    dot.node("b", label="Node B")
    dot.edge("a", "b", style="dashed", color="blue")
    dot.edge("b", "c", label=" B/C ")
    block = dot.subgraph("cluster_1")
    block.graph(style="rounded", color="orange")
    block.node("c", style="filled", color="orange")
    block.edge("c","d")
    dot.node("b", penwidth=1.75)        # Amend node b
    dot.edge("b", "c", labelfloat=True) # Amend b -> c
