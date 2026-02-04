from gvdot import Dot, Markup, Port
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

