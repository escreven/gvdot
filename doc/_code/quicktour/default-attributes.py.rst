.. code-block:: python

    dot = Dot()
    dot.graph_default(labelloc="t", rankdir="LR", bgcolor="antiquewhite")
    dot.node_default(shape="circle", fontsize=10, margin=0)
    dot.edge_default(fontsize=8, fontcolor="green")
    dot.graph(label="Choices")
    dot.node(1, label="First")
    dot.node(2, label="Second")
    dot.node(3, label="Third")
    dot.node("distraction", shape="diamond")
    dot.edge(1, 2, label="steady")
    dot.edge(2, 3, label="progress")
    dot.edge(1, "distraction")
