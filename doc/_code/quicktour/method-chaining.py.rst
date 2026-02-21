.. code-block:: python

    dot = Dot().graph(rankdir="LR").node_default(width=0, height=0)
    dot.node("a", shape="circle").node("b",shape="diamond")
    dot.edge("a","b")
