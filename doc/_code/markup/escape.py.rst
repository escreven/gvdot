.. code-block:: python

    dot = Dot(directed=True).graph(rankdir="LR")
    dot.node_default(shape="circle",style="filled",color="sienna3")
    dot.edge("A","B",label=Font(point_size=10).add(
        "Not <b>bold</b>",BR(),
        "Not <i>italic</i>",BR(),
        'But "quoted"'
    ))
