.. code-block:: python

    dot = Dot(directed=True).graph(rankdir="LR")
    dot.node_default(shape="box")
    dot.node(1,label=Text("&alpha; < &beta;"))
    dot.node(2,label=with_entities("&alpha; < &beta;"))
    dot.edge(1,2)
