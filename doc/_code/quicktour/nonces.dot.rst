.. code-block:: graphviz

    digraph {
    
        node [shape=plain]
        edge [arrowhead=none]
    
        anchor_1 [label="" width=0.1 height=0.1 style=filled shape=square]
        anchor_2 [label="" width=0.1 height=0.1 style=filled shape=square]
    
        anchor_1 -> A
        A -> anchor_2
        anchor_1 -> B
        B -> anchor_2
        anchor_1 -> C
        C -> anchor_2
    }
