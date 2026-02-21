.. code-block:: graphviz

    digraph {
        rankdir=LR
        labelloc=t
        old [color=green label=<d<sub>k</sub>>]
        new [color=red label=<d<sub>k+1</sub>>]
        old -> new [label="apply"]
        new:s -> old:s [label="undo"]
        label="Rolling Back"
    }
