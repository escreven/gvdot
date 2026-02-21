.. code-block:: graphviz

    graph {
    
        graph [labelloc=t rankdir=LR bgcolor=antiquewhite]
        node [shape=circle fontsize=10 margin=0]
        edge [fontsize=8 fontcolor=green]
    
        1 [label="First"]
        2 [label="Second"]
        3 [label="Third"]
        distraction [shape=diamond]
    
        1 -- 2 [label="steady"]
        2 -- 3 [label="progress"]
        1 -- distraction
    
        label="Choices"
    }
