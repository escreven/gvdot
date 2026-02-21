.. code-block:: graphviz

    digraph {
    
        graph [penwidth=1.25]
        node [penwidth=1.25 shape=box width=0 height=0 style=filled]
        edge [penwidth=1.25 arrowsize=0.75]
    
        rankdir=LR
    
        Fred [margin=0.05 fillcolor=khaki]
        Wilma [margin=0.05 fillcolor=khaki]
        Betty [margin=0.05 fillcolor=khaki]
        Barney [margin=0.05 fillcolor=khaki]
        nil [label="NIL" fontname="sans-serif" fontsize=8 margin=0.02]
    
        Fred -> Wilma [color="#333"]
        Wilma -> Betty [color="#333"]
        Betty -> Barney [color="#333"]
        Barney -> nil [style=dashed]
    }
