.. code-block:: graphviz

    digraph {
    
        node [style=filled width=0 height=0 fontsize=10 fontname=monospace]
    
        rankdir=LR
    
        "model.h" [shape=box fillcolor=orange]
        "main.cpp" [shape=box fillcolor=cyan2]
        server [shape=hexagon fillcolor=green margin=0.02]
    
        "model.h" -> "main.cpp" [color=orange penwidth=2]
        "interactor.h" -> "main.cpp" [color=orange penwidth=2]
        "main.cpp" -> server [color=green penwidth=2]
        "interactor.cpp" -> server [color=green penwidth=2]
    
        subgraph {
            cluster=true
            bgcolor=gray80
            penwidth=0
            "interactor.h" [shape=box fillcolor=orange]
            "interactor.cpp" [shape=box fillcolor=cyan2]
            "interactor.h" -> "interactor.cpp" [color=orange penwidth=2]
        }
    }
