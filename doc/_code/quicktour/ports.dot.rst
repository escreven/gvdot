.. code-block:: graphviz

    digraph {
    
        node [shape=record]
    
        rankdir=LR
    
        node1 [label="First|<link>next"]
        node2 [label="Second|<link>next"]
        node3 [label="Third|<link>next"]
    
        subgraph {
            node1:link:s -> node2:w
            node2:link -> node3:s
            node3:link -> node1:ne
        }
    }
