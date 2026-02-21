.. code-block:: python

    theme = Dot()
    theme.node_default(shape="plain")
    theme.edge_default(arrowhead="none")
    theme.node_role("anchor", label="", width=.10, height=.10,
                    style="filled", shape="square")
    
    dot = Dot(directed=True).use_theme(theme)
    source = Nonce("anchor")
    sink = Nonce("anchor")
    dot.node(source, role="anchor")
    dot.node(sink, role="anchor")
    dot.edge(source,"A").edge("A",sink)
    dot.edge(source,"B").edge("B",sink)
    dot.edge(source,"C").edge("C",sink)
