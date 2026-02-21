.. code-block:: python

    dot = Dot(directed=True)
    dot.graph(rankdir="LR")
    dot.all_default(color="limegreen")
    dot.edge("a", "b", color="blue", style="dashed")
    dot.show()
    
    # That edge looks terrible.  Let's just use the default.
    dot.edge("a", "b", color=None)
    dot.show()
