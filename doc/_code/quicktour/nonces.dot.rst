.. code-block:: graphviz

    digraph {
    
        node [shape=plain]
        edge [arrowhead=none]
    
        _nonce_1 [label="" width=0.1 height=0.1 style=filled shape=square]
        _nonce_2 [label="" width=0.1 height=0.1 style=filled shape=square]
    
        _nonce_1 -> A
        A -> _nonce_2
        _nonce_1 -> B
        B -> _nonce_2
        _nonce_1 -> C
        C -> _nonce_2
    }
