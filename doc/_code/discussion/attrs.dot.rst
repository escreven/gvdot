.. code-block:: graphviz

    digraph {
    
        graph [bgcolor=antiquewhite]
        node [shape=circle]
        edge [style=dashed]
    
        rankdir=LR
    
        a [label="A"]
        b [label="B" fontcolor=green]
    
        a -> b
        b -> c [color=red]
    
        subgraph cluster_1 {
            graph [fontsize=12 fontname="sans-serif"]
            node [shape=box]
            edge [arrowhead=diamond]
            labelloc=t
            bgcolor=bisque4
            c [label="C" style=filled fillcolor=khaki]
            c -> last
            label="Clustered"
        }
    
        label="Many ways to set attributes"
    }
