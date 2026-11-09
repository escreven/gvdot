.. code-block:: python

    from gvdot.markup import Font, Table, TR, TD
    dot = Dot(directed=True).graph(rankdir="LR")

    dot.node(1,shape="plain",label=Font(
        color="blue",face="Courier New").add(
        Table(cellspacing=0, cellborder=1, border=0).add(
            TR(TD("Good"),TD("morning")),
            TR(TD("to you.", colspan=2, port="outro")))))

    dot.node(2,shape="plain",label=Font(
        color="green",face="Courier New").add(
        Table(cellspacing=0, cellborder=1, border=0).add(
            TR(TD("Why", rowspan=2, port="intro"),TD("thank")),
            TR(TD("you.")))))

    dot.edge(Port(1,"outro","s"),Port(2,"intro","w"))
    dot.show()
