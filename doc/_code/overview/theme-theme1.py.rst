.. code-block:: python

    project_theme = (Dot()
        .node_default(shape="box", margin=0.1, style="filled",
                      fontsize=10, fontname="sans-serif",
                      width=0, height=0)
        .node_role("normal", color="#10a010")
        .node_role("atrisk", color="#ffbf00")
        .node_role("critical", color="#c00000", fontcolor="#e8e8e8"))
