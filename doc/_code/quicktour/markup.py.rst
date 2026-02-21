.. code-block:: python

    dot = Dot()
    dot.graph(rankdir="LR", label=Markup(
        '<b>Graphviz HTML Strings</b><br/>'
        '<font point-size="10">'
        'are supported</font>'))
    dot.node(1,label=Markup("x<sub>1</sub>"))
    dot.node(2,label=Markup("x<sub>2</sub>"))
    dot.edge(1,2)
