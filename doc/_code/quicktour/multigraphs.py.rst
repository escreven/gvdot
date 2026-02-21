.. code-block:: python

    dot = Dot(multigraph=True).graph(rankdir="LR")
    dot.edge("a", "b", label="One")
    dot.edge("a", "b", label="Two", color="red")
    dot.edge("a", "b", "x", label="Three", style="dashed")
    dot.edge("a", "b", "x", color="blue", penwidth=2.5) # Amend third edge
