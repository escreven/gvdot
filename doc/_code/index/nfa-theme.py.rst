.. code-block:: python

    nfa_theme = (Dot()
       .all_default(fontsize=12)
       .node_default(shape="circle", style="filled", fillcolor="khaki")
       .node_role("init", label="", shape="none", width=0, height=0)
       .node_role("final", shape="doublecircle", penwidth=1.25)
       .graph(rankdir="LR", labelloc="t", fontsize=16))
