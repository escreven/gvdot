.. code-block:: python

    dot = Dot().graph(rankdir="LR")
    dot.edge("a", "b", color="red", label="first")
    dot.edge("a", "b", color="green", label="second")
    dot.edge("a", "b", color="blue", label="third")
