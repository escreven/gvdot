.. code-block:: python

    dot = Dot()
    dot.graph(rankdir="LR", label=Markup(
        '<b>Graphviz HTML Strings</b><br/>are supported'))
    dot.node(1,label=Markup('x<sub><font point-size="10">1</font></sub>'))
    dot.node(2,label=Markup('x<sub><font point-size="10">2</font></sub>'))
    dot.edge(1,2)
