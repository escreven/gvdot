.. code-block:: python

    compact_project_theme = (Dot()
        .use_theme(project_theme)
        .graph(rankdir="LR", ranksep=0.25)
        .node_default(margin=0.05)
        .edge_default(arrowsize=0.75))
