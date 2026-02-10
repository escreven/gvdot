.. code-block:: python

    dot = Dot(multigraph=True).graph(rankdir="LR")
    dot.edge("a", "b", 1, color="red", label="first")
    dot.edge("a", "b", 2, color="green", label="second")
    dot.edge("a", "b", 3, color="blue", label="third")
    
    # Amend the green edge
    dot.edge("a", "b", 2, style="dashed")
