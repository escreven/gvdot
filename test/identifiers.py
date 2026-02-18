import re
from gvdot import Block, Dot, Markup, Nonce, Port
from utility import expect_str, expect_ex


def test_id_forms():
    """
    IDs can have simple, quoted, and markup forms.  IDs can be strings, ints,
    floats, bools, or Markup objects.  Strings that are not simple numerics or
    programming language identifier-like tokens must be quoted.
    """
    dot = Dot()
    dot.node("simple")
    dot.node("this is quoted")
    dot.node("so-is-this")
    dot.node(Markup("this is markup"))
    dot.node(42)
    dot.node(1.23)
    dot.node(True)
    dot.node(False)
    expect_str(dot,
    """
    graph {
        simple
        "this is quoted"
        "so-is-this"
        <this is markup>
        42
        1.23
        true
        false
    }
    """)

    expect_ex(ValueError,lambda: Dot().node(b'a')) #type:ignore
    expect_ex(ValueError,lambda: Dot().node(None)) #type:ignore


def test_id_use():
    """
    IDs can be used for graph and subgraph identifiers, node identifiers, edge
    endpoints (including ports), discriminants, and attribute values.
    """
    dot = Dot(multigraph=True,id=Markup("graph"))
    dot.node(Markup("node"))
    dot.edge(Markup("a"),Markup("b"))
    dot.edge(Port(Markup("c"),Markup("u")),Port(Markup("d"),Markup("v")))
    dot.edge("e","f",Markup("g"))
    dot.subgraph(id=Markup("i"))
    dot.graph(label=Markup("h"))
    expect_str(dot,
    """
    graph <graph> {
        <node>
        <a> -- <b>
        <c>:<u> -- <d>:<v>
        e -- f
        subgraph <i> {
        }
        label=<h>
    }
    """)


def test_id_str_escape():
    """
    Backslashes, double-quote characters and end-of-line sequences must be
    escaped in non-Markup IDs.
    """
    dot = Dot()
    dot.node("\\ab")
    dot.node("a\\b")
    dot.node("ab\\")
    dot.node("\\a\\b\\")
    dot.node("\nab")
    dot.node("a\nb")
    dot.node("ab\n")
    dot.node("\na\nb\n")
    dot.node("\r\nac")
    dot.node("a\r\nc")
    dot.node("ac\r\n")
    dot.node("\r\na\r\nc\r\n")
    dot.node('"ad')
    dot.node('a"d')
    dot.node('ad"')
    dot.node('"a"d"')
    dot.node('\\')
    dot.node('\n')
    dot.node('\r\n',label="gotit")
    dot.node('"')
    expect_str(dot,
    r"""
    graph {
        "\\ab"
        "a\\b"
        "ab\\"
        "\\a\\b\\"
        "\nab"
        "a\nb"
        "ab\n"
        "\na\nb\n"
        "\nac"
        "a\nc"
        "ac\n"
        "\na\nc\n"
        "\"ad"
        "a\"d"
        "ad\""
        "\"a\"d\""
        "\\"
        "\n" [label="gotit"]
        "\""
    }
    """)


def test_prefer_quotes():
    """
    Attribute values that are general text are always quoted, even if the ID
    value is simple.
    """
    dot = Dot()
    dot.graph(comment="ImaGraph")
    dot.node("a",label="Label")
    dot.node("b",xlabel="XLabel")
    dot.edge("a","b",headlabel="HeadLabel")
    dot.edge("c","d",taillabel="TailLabel")
    expect_str(dot,
    """
    graph {
        comment="ImaGraph"
        a [label="Label"]
        b [xlabel="XLabel"]
        a -- b [headlabel="HeadLabel"]
        c -- d [taillabel="TailLabel"]
    }
    """)


def test_ports():
    """
    Edge endpoints can be specified with ports.  The name and compass point
    fields of ports are both optional.  Port specifications can be amended.
    """
    dot = Dot()
    dot.edge(Port("a"),"z")
    dot.edge(Port("b","next"),"z")
    dot.edge(Port("c","next","n"),"z")
    dot.edge(Port("d",cp="s"),"z")
    dot.edge(Port("e","next","e"),Port("y","prev","w"))
    dot.edge(Port("f","n"),"z")
    expect_str(dot,
    """
    graph {
        a -- z
        b:next -- z
        c:next:n -- z
        d:s -- z
        e:next:e -- y:prev:w
        f:"n" -- z
    }
    """)

    dot.edge("b",Port("z",cp="s"))
    dot.edge(Port("c"),"z")
    dot.edge(Port("e","prev","w"),Port("y","next","e"))
    expect_str(dot,
    """
    graph {
        a -- z
        b:next -- z:s
        c -- z
        d:s -- z
        e:prev:w -- y:next:e
        f:"n" -- z
    }
    """)



def test_compass_points():
    """
    There are 10 compass points, the typical n, ne, e, se, s, sw, w, nw plus
    "c" for center and "_" meaning none.
    """
    dot = Dot(multigraph=True)
    dot.edge("a",Port("b",cp="n"))
    dot.edge("a",Port("b",cp="ne"))
    dot.edge("a",Port("b",cp="e"))
    dot.edge("a",Port("b",cp="se"))
    dot.edge("a",Port("b",cp="s"))
    dot.edge("a",Port("b",cp="sw"))
    dot.edge("a",Port("b",cp="w"))
    dot.edge("a",Port("b",cp="nw"))
    dot.edge("a",Port("b",cp="c"))
    dot.edge("a",Port("b",cp="_"))
    expect_str(dot,
    """
    graph {
        a -- b:n
        a -- b:ne
        a -- b:e
        a -- b:se
        a -- b:s
        a -- b:sw
        a -- b:w
        a -- b:nw
        a -- b:c
        a -- b
    }
    """)

    expect_ex(ValueError, lambda:Dot().edge("a",Port("b",cp="x")))


def test_nonce():
    """
    IDs can be Nonces.  Nonces must resolve to unique DOT identifiers each
    generation run, avoiding collisions with non-Nonce IDs, including attribute
    values.  Nonces must be effective as keys or part of keys for nodes, edges,
    and subgraphs.  Nonces can be used as graph IDs.
    """
    nonce1 = Nonce()
    nonce2 = Nonce()
    discriminant = Nonce("disc")

    dot = Dot(multigraph=True)
    dot.node(nonce1)
    dot.node(nonce2)
    dot.edge(nonce1,nonce2)
    dot.node("_nonce_1")
    dot.graph(label="_nonce_2")
    dot.edge("a","b",discriminant,a=1)
    dot.edge("a","b",discriminant,b=2)
    expect_str(dot,
    """
    graph {
        _nonce_3
        _nonce_4
        _nonce_1
        _nonce_3 -- _nonce_4
        a -- b [a=1 b=2]
        label="_nonce_2"
    }
    """)

    dot.node("disc_1")
    dot.node(discriminant)
    expect_str(dot,
    """
    graph {
        _nonce_3
        _nonce_4
        _nonce_1
        disc_1
        disc_2
        _nonce_3 -- _nonce_4
        a -- b [a=1 b=2]
        label="_nonce_2"
    }
    """)

    dot = Dot(id=nonce1)
    sub = dot.subgraph(nonce1)
    sub.subgraph(nonce1)
    sub.subgraph(nonce2)
    expect_str(dot,
    """
    graph _nonce_1 {
        subgraph _nonce_1 {
            subgraph _nonce_1 {
            }
            subgraph _nonce_2 {
            }
        }
    }
    """)


def test_nonce_names():
    """
    Nonce resolved IDs have the form <prefix>_<n>.  Nonce prefixes can be
    specified as part of the Nonce constructor.  Nonce prefixes are general
    strings, not limited to identifier-like sequences.  Nonce prefixes must be
    strings.
    """
    dot = Dot()
    dot.node(Nonce())
    dot.node(Nonce("test"))
    dot.node(Nonce("with space"))
    dot.node(Nonce('and "quotes"'))
    dot.subgraph(Nonce("cluster"))
    expect_str(dot,
    """
    graph {
        _nonce_1
        test_1
        "with space_1"
        "and \\"quotes\\"_1"
        subgraph cluster_1 {
        }
    }
    """)

    expect_ex(ValueError, lambda: Nonce(42))  #type:ignore


def test_nonce_properties():
    """
    Nonces are equal iff identical.  Nonces are hashable.
    """
    nonce1 = Nonce()
    nonce2 = Nonce()

    assert nonce1 == nonce1
    assert nonce2 == nonce2
    assert nonce1 != nonce2

    d:dict[Nonce,int] = dict()
    d[nonce1] = 10
    d[nonce1] = 11
    d[nonce2] = 20
    d[nonce2] = 21
    assert d[nonce1] == 11
    assert d[nonce2] == 21


def test_nonce_dynamics():
    """
    Nonce resolution is dynamic.  Adding a conflicting ID to a Dot object after
    first resolution should result in a new non-conflicting resolution in the
    next resolution.
    """
    nonce = Nonce()

    dot = Dot()
    dot.node(nonce)
    expect_str(dot,"""
    graph {
        _nonce_1
    }
    """)

    dot.node(nonce, label="_nonce_1")
    expect_str(dot,"""
    graph {
        _nonce_2 [label="_nonce_1"]
    }
    """)


def test_nonce_avoidance():
    """
    Regular IDs provided anywhere in a Dot object should be avoided when
    resolving nonces, including themes.
    """
    def must_avoid(what:str, block:Block):
        text = str(block.dot().node(Nonce()))
        if not re.search(r"^\s*_nonce_2\s*",text,re.MULTILINE):
            raise AssertionError(f"Did not avoid {what}")

    X = "_nonce_1"

    must_avoid("graph id",         Dot(id=X))
    must_avoid("graph_role",       Dot().graph_role("test",a=X))
    must_avoid("graph_default",    Dot().graph_default(a=X))
    must_avoid("graph attribute",  Dot().graph(a=X))
    must_avoid("node_role",        Dot().node_role("test",a=X))
    must_avoid("node_default",     Dot().node_default(a=X))
    must_avoid("node id",          Dot().node(X))
    must_avoid("node attribute",   Dot().node("x", a=X))
    must_avoid("edge_role",        Dot().edge_role("test",a=X))
    must_avoid("edge_default",     Dot().edge_default(a=X))
    must_avoid("edge node 1",      Dot().edge(X,"b"))
    must_avoid("edge port 1 id",   Dot().edge(Port(X),"b"))
    must_avoid("edge port 1 name", Dot().edge(Port("a",X),"b"))
    must_avoid("edge node 2",      Dot().edge("a",X))
    must_avoid("edge port 2 id",   Dot().edge("a",Port(X)))
    must_avoid("edge port 2 name", Dot().edge("a",Port("b",X)))
    must_avoid("edge attribute",   Dot().edge("a","b",a=X))

    def sub(id=None):
        return Dot().subgraph(id)

    must_avoid("sub graph id",         sub(id=X))
    must_avoid("sub graph_default",    sub().graph_default(a=X))
    must_avoid("sub graph attribute",  sub().graph(a=X))
    must_avoid("sub node_default",     sub().node_default(a=X))
    must_avoid("sub node id",          sub().node(X))
    must_avoid("sub node attribute",   sub().node("x", a=X))
    must_avoid("sub edge_default",     sub().edge_default(a=X))
    must_avoid("sub edge node 1",      sub().edge(X,"b"))
    must_avoid("sub edge port 1 id",   sub().edge(Port(X),"b"))
    must_avoid("sub edge port 1 name", sub().edge(Port("a",X),"b"))
    must_avoid("sub edge node 2",      sub().edge("a",X))
    must_avoid("sub edge port 2 id",   sub().edge("a",Port(X)))
    must_avoid("sub edge port 2 name", sub().edge("a",Port("b",X)))
    must_avoid("sub edge attribute",   sub().edge("a","b",a=X))

    def use(theme:Dot):
        return Dot().use_theme(theme)

    must_avoid("graph_role",       use(Dot().graph_role("test",a=X)))
    must_avoid("graph_default",    use(Dot().graph_default(a=X)))
    must_avoid("graph attribute",  use(Dot().graph(a=X)))
    must_avoid("node_role",        use(Dot().node_role("test",a=X)))
    must_avoid("node_default",     use(Dot().node_default(a=X)))
    must_avoid("edge_role",        use(Dot().edge_role("test",a=X)))
    must_avoid("edge_default",     use(Dot().edge_default(a=X)))


def test_nonce_replacement():
    """
    Nonces must be resolved and replaced everywhere in a Dot object, including
    its theme.
    """
    def must_replace(what:str, block:Block):
        block.graph(role="test")
        block.node("a",role="test")
        block.edge("a","b",role="test")
        text = str(block.dot())
        if not re.search(r"\b_nonce_1\b",text):
            raise AssertionError(f"Did not replace {what}")

    X = Nonce()

    def dot(id=None):
        return Dot(id=id).all_role("test")

    must_replace("graph id",         dot(id=X))
    must_replace("graph_role",       dot().graph_role("test",a=X))
    must_replace("graph_default",    dot().graph_default(a=X))
    must_replace("graph attribute",  dot().graph(a=X))
    must_replace("node_role",        dot().node_role("test",a=X))
    must_replace("node_default",     dot().node_default(a=X))
    must_replace("node id",          dot().node(X))
    must_replace("node attribute",   dot().node("x", a=X))
    must_replace("edge_role",        dot().edge_role("test",a=X))
    must_replace("edge_default",     dot().edge_default(a=X))
    must_replace("edge node 1",      dot().edge(X,"b"))
    must_replace("edge port 1 id",   dot().edge(Port(X),"b"))
    must_replace("edge port 1 name", dot().edge(Port("a",X),"b"))
    must_replace("edge node 2",      dot().edge("a",X))
    must_replace("edge port 2 id",   dot().edge("a",Port(X)))
    must_replace("edge port 2 name", dot().edge("a",Port("b",X)))
    must_replace("edge attribute",   dot().edge("a","b",a=X))

    def sub(id=None):
        return Dot().all_role("test").subgraph(id)

    must_replace("graph id",         sub(id=X))
    must_replace("graph_default",    sub().graph_default(a=X))
    must_replace("graph attribute",  sub().graph(a=X))
    must_replace("node_default",     sub().node_default(a=X))
    must_replace("node id",          sub().node(X))
    must_replace("node attribute",   sub().node("x", a=X))
    must_replace("edge_default",     sub().edge_default(a=X))
    must_replace("edge node 1",      sub().edge(X,"b"))
    must_replace("edge port 1 id",   sub().edge(Port(X),"b"))
    must_replace("edge port 1 name", sub().edge(Port("a",X),"b"))
    must_replace("edge node 2",      sub().edge("a",X))
    must_replace("edge port 2 id",   sub().edge("a",Port(X)))
    must_replace("edge port 2 name", sub().edge("a",Port("b",X)))
    must_replace("edge attribute",   sub().edge("a","b",a=X))

    def use(theme:Dot):
        return Dot().use_theme(theme).all_role("test")

    must_replace("graph_role",       use(Dot().graph_role("test",a=X)))
    must_replace("graph_default",    use(Dot().graph_default(a=X)))
    must_replace("graph attribute",  use(Dot().graph(a=X)))
    must_replace("node_role",        use(Dot().node_role("test",a=X)))
    must_replace("node_default",     use(Dot().node_default(a=X)))
    must_replace("edge_role",        use(Dot().edge_role("test",a=X)))
    must_replace("edge_default",     use(Dot().edge_default(a=X)))
