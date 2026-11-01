.. code-block:: python

    dot = Dot(directed=True).graph(ranksep=0.4)
    dot.node_default(fontsize=12, fontname="Helvetica", margin=0.05, height=0.4)
    dot.edge_default(dir="back")
    dot.node_role("class",shape="box",style="filled")
    dot.node_role("protocol",shape="box",style="filled,dashed")
    dot.node_role("public",fontcolor="#eee",fillcolor="#161")
    dot.node_role("private",fontcolor="#111",fillcolor="#9c9")
    dot.edge("_Entity","_Node").edge("_Entity","_Edge")
    dot.edge("_Entity","Block").edge("Block","Dot")
    dot.node("_Entity",role=("private","protocol")) # <-- Assign roles
    dot.node("_Node",role=("private","class"))      # <-- Assign roles
    dot.node("_Edge",role=("private","class"))      # <-- Assign roles
    dot.node("Block",role=("public","class"))       # <-- Assign roles
    dot.node("Dot",role=("public","class"))         # <-- Assign roles
    dot.show()
