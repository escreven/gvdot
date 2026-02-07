.. code-block:: python

    example = NFA("01", {
        "s0": [["q0", "r0"], [], []],
        "q0": [[], ["q1"], ["q0"]],
        "q1": [[], ["q1"], ["q2"]],
        "q2": [[], ["q3"], ["q0"]],
        "q3": [[], ["q1"], ["q4"]],
        "q4": [[], ["q4"], ["q4"]],
        "r0": [[], ["r0"], ["r1"]],
        "r1": [[], ["r0"], ["r2"]],
        "r2": [[], ["r3"], ["r1"]],
        "r3": [[], ["r3"], ["r3"]],
    }, ["q4","r0","r1","r2"], "s0")
    
    with open("example.svg","w") as f:
    print(nfa_diagram(example,"Example NFA").to_svg(), file=f)
    
