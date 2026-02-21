.. code-block:: python

    list_theme = Dot()
    list_theme.all_default(penwidth=1.25)
    list_theme.node_default(shape="box", width=0, height=0, style="filled")
    list_theme.edge_default(arrowsize=0.75)
    list_theme.node_role("element", margin=0.05, fillcolor="khaki")
    list_theme.node_role("nil", label="NIL", fontname="sans-serif", fontsize=8,
                         style="filled", margin=0.02, width=0)
    list_theme.edge_role("link", color="#333")
    list_theme.edge_role("nil", style="dashed")
    list_theme.graph(rankdir="LR")
    
    dot = Dot(directed=True)
    dot.use_theme(list_theme)
    dot.node("Fred", role="element")
    dot.node("Wilma", role="element")
    dot.node("Betty", role="element")
    dot.node("Barney", role="element")
    dot.edge("Fred", "Wilma", role="link")
    dot.edge("Wilma", "Betty", role="link")
    dot.edge("Betty", "Barney", role="link")
    dot.edge("Barney", "nil", role="nil")
    dot.node("nil", role="nil")
