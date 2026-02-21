.. code-block:: graphviz

    digraph {
    
        rankdir=LR
    
        a [label="Node A" shape=box]
        b [label="Node B" penwidth=1.75]
    
        a -> b [style=dashed color=blue]
        b -> c [label=" B/C " labelfloat=true]
    
        subgraph cluster_1 {
            style=rounded
            color=orange
            c [style=filled color=orange]
            c -> d
        }
    
        label="Basic Construction"
    }
