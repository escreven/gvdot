.. code-block:: graphviz

    digraph {
        graph [bgcolor=darkolivegreen3]
        node [shape=plain fontsize=10 fontname="sans-serif"]
        edge [dir=back]
        1 [label=<<table border="1" cellborder="0" cellspacing="0"><tr><td bgcolor="#ddd"><font point-size="8">abstract</font></td><td bgcolor="#fff"><font color="#448"><b>Mapping</b></font></td></tr></table>>]
        2 [label=<<table border="1" cellborder="0" cellspacing="0"><tr><td bgcolor="#ddd"><font point-size="8">abstract</font></td><td bgcolor="#fff"><font color="#448"><b>MutableMapping</b></font></td></tr></table>>]
        3 [label=<<table border="1" cellborder="0" cellspacing="0"><tr><td bgcolor="#ddd"><font point-size="8">concrete</font></td><td bgcolor="#fff"><font color="#448"><b>MappingProxyType</b></font></td></tr></table>>]
        1 -> 2
        1 -> 3
    }
