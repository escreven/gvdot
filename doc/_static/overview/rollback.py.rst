.. code-block:: python

    dot = Dot(directed=True)
    dot.graph(rankdir="LR", labelloc="t", label="Rolling Back")
    dot.node("old", color="green", label=Markup("d<sub>k</sub>"))
    dot.node("new", color="red", label=Markup("d<sub>k+1</sub>"))
    dot.edge("old", "new", label="apply")
    dot.edge(Port("new",cp="s"), Port("old",cp="s"), label="undo")
    print(dot)
