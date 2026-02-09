from __future__ import annotations
from copy import deepcopy
from gvdot import Dot, Port
from utility import expect_str, expect_ex


def test_graph_header():
    """
    Each graph header element must appear, and appear in the correct order.
    """
    dot = Dot()
    expect_str(dot,"""
    graph {
    }""")

    dot = Dot(directed=True)
    expect_str(dot,"""
    digraph {
    }""")

    dot = Dot(strict=True)
    expect_str(dot,"""
    strict graph {
    }""")

    dot = Dot(multigraph=True)
    expect_str(dot,"""
    graph {
    }""")

    dot = Dot(id="MyGraph")
    expect_str(dot,"""
    graph MyGraph {
    }""")

    dot = Dot(directed=True, strict=True, id="MyGraph")
    expect_str(dot,"""
    strict digraph MyGraph {
    }""")


def test_strict_multigraph_disallowed():
    """
    Options strict and multigraph are mutually exclusive.
    """
    expect_ex(ValueError,lambda: Dot(strict=True,multigraph=True))


def test_comment():
    """
    Single and multiline comments must appear.  Trailing newlines must be
    irrelevant.
    """
    dot = Dot(comment="One")
    expect_str(dot,"""
    // One
    graph {
    }""")

    dot = Dot(comment="One\n")
    expect_str(dot,"""
    // One
    graph {
    }""")

    dot = Dot(comment="One\nTwo")
    expect_str(dot,"""
    // One
    // Two
    graph {
    }""")

    dot = Dot(comment="One\nTwo\n")
    expect_str(dot,"""
    // One
    // Two
    graph {
    }""")


def test_is_multigraph():
    """
    is_multigraph() must be true iff multigraph is specified to constructor.
    """
    dot = Dot()
    expect_str(dot,"""
    graph {
    }""")

    assert not dot.is_multigraph()

    dot = Dot(multigraph=True)
    expect_str(dot,"""
    graph {
    }""")

    assert dot.is_multigraph()


def test_statement_order():
    """
    All statements must appear in the order defined in the documentation.
    """
    dot = Dot()
    dot.graph(label="Label")
    subdot = dot.subgraph(id="Subgraph1")
    subdot.graph(label="SubLabel1")
    subdot.edge("c","d")
    subdot.node("c")
    subdot.graph(rankdir="LTR")
    subdot.edge_default(color="red")
    subdot.node_default(shape="circle")
    subdot.graph_default(dpi=300)
    subdot.subgraph(id="Subgraph1Sub")
    dot.subgraph("Subgraph2")
    dot.edge("a","b")
    dot.node("a")
    dot.graph(labelloc="t")
    dot.edge_default(color="lime")
    dot.node_default(shape="square")
    dot.graph_default(dpi=72)

    expect_str(dot,
    """
    graph {
        graph [dpi=72]
        node [shape=square]
        edge [color=lime]
        labelloc = t
        a
        a -- b
        subgraph Subgraph1 {
            graph [dpi=300]
            node [shape=circle]
            edge [color=red]
            rankdir = LTR
            c
            c -- d
            subgraph Subgraph1Sub {
            }
            label = "SubLabel1"
        }
        subgraph Subgraph2 {
        }
        label = "Label"
    }
    """)


def test_attr_basics():
    """
    Default and entity attributes can be defined and amended.
    """
    dot = Dot()
    dot.graph_default(d_graph_a=1)
    dot.node_default (d_node_a=1)
    dot.edge_default (d_edge_a=1)
    dot.graph        (graph_a=1)
    dot.node         ("a",node_a=1)
    dot.edge         ("a","b",edge_a=1)
    expect_str(dot,
    """
    graph {
        graph  [ d_graph_a=1 ]
        node   [ d_node_a=1 ]
        edge   [ d_edge_a=1 ]
        graph_a=1
        a      [ node_a=1 ]
        a -- b [ edge_a=1 ]
    }
    """)

    dot.graph_default(d_graph_a=2, d_graph_b=1)
    dot.node_default (d_node_a=2, d_node_b=1)
    dot.edge_default (d_edge_a=2, d_edge_b=1)
    dot.graph        (graph_a=2, graph_b=1)
    dot.node         ("a",node_a=2, node_b=1)
    dot.edge         ("a","b",edge_a=2, edge_b=1)
    expect_str(dot,
    """
    graph {
        graph  [ d_graph_a=2 d_graph_b=1 ]
        node   [ d_node_a=2 d_node_b=1 ]
        edge   [ d_edge_a=2 d_edge_b=1 ]
        graph_a=2
        graph_b=1
        a      [ node_a=2 node_b=1 ]
        a -- b [ edge_a=2 edge_b=1 ]
    }
    """)

    dot.graph_default(d_graph_a=None, d_graph_b=2)
    dot.node_default (d_node_a=None, d_node_b=2)
    dot.edge_default (d_edge_a=None, d_edge_b=2)
    dot.graph        (graph_a=None, graph_b=2)
    dot.node         ("a",node_a=None, node_b=2)
    dot.edge         ("a","b",edge_a=None, edge_b=2)
    expect_str(dot,
    """
    graph {
        graph  [ d_graph_b=2 ]
        node   [ d_node_b=2 ]
        edge   [ d_edge_b=2 ]
        graph_b=2
        a      [ node_b=2 ]
        a -- b [ edge_b=2 ]
    }
    """)


def test_attr_escape():
    """
    A single trailing underscore character is trimmed from attribute keyword
    names if present.
    """
    dot = Dot()
    dot.node("a",class_="required",shape_="superfluous")
    dot.node("b",class__="only one")
    expect_str(dot,
    """
    graph {
        a [ class=required shape=superfluous ]
        b [ class_="only one" ]
    }
    """)


def test_all_default():
    """
    Graph, node, and edge defaults can be defined and amended all at once.
    """
    dot = Dot()
    dot.all_default(a1=1)
    dot.graph_default(b1=1, a2=2)
    dot.node_default(b1=1, a3=3)
    dot.edge_default(b1=1, a4=4)
    dot.all_default(b1=2)
    expect_str(dot,
    """
    graph {
        graph [ a1=1 a2=2 b1=2 ]
        node  [ a1=1 a3=3 b1=2 ]
        edge  [ a1=1 a4=4 b1=2 ]
    }
    """)


def test_def_vs_update():
    """
    Nodes, edges, and subgraphs can be specifically defined and updated.  The
    general API forms do both.  The defined status of nodes and edges can be
    tested.
    """
    dot = Dot()
    assert not dot.node_is_defined("a")
    assert not dot.edge_is_defined("a","b")
    expect_ex(RuntimeError,lambda: dot.node_update("a",shape="circle"))
    expect_ex(RuntimeError,lambda: dot.edge_update("a","b",color="red"))
    dot.node_define("a",shape="circle")
    dot.edge_define("a","b",color="red")
    assert dot.node_is_defined("a")
    assert dot.edge_is_defined("a","b")
    expect_ex(RuntimeError,lambda: dot.node_define("a",shape="circle"))
    expect_ex(RuntimeError,lambda: dot.edge_define("a","b",color="red"))
    dot.node_update("a",style="filled")
    dot.edge_update("a","b",style="dashed")

    expect_str(dot,
    """
    graph {
        a [ shape=circle style=filled ]
        a -- b [ color=red style=dashed ]
    }
    """)

    dot = Dot()
    assert not dot.node_is_defined("a")
    assert not dot.edge_is_defined("a","b")
    dot.node("a",shape="circle")
    dot.edge("a","b",color="red")
    assert dot.node_is_defined("a")
    assert dot.edge_is_defined("a","b")
    dot.node("a",style="filled")
    dot.edge("a","b",style="dashed")

    expect_str(dot,
    """
    graph {
        a [ shape=circle style=filled ]
        a -- b [ color=red style=dashed ]
    }
    """)

    dot = Dot(multigraph=True)
    assert not dot.edge_is_defined("a","b")
    expect_ex(RuntimeError,lambda: dot.edge_update("a","b",color="red"))
    dot.edge_define("a","b")
    expect_ex(RuntimeError,lambda: dot.edge_update("a","b",color="red"))
    dot.edge_define("a","b","x")
    assert dot.edge_is_defined("a","b","x")
    expect_ex(RuntimeError,lambda: dot.edge_define("a","b","x"))
    dot.edge_update("a","b","x",color="red")

    expect_str(dot,
    """
    graph {
        a -- b
        a -- b [color=red]
    }
    """)

    dot = Dot()
    assert not dot.subgraph_is_defined("sub1")
    expect_ex(RuntimeError, lambda: dot.subgraph_update("sub1"))
    sub1 = dot.subgraph_define("sub1")
    expect_ex(RuntimeError, lambda: dot.subgraph_define("sub1"))
    sub1.node("a")
    assert dot.subgraph_update("sub1") is sub1
    assert dot.subgraph("sub1") is sub1
    sub2 = dot.subgraph("sub2")
    sub2.node("a")
    assert sub2 is not sub1
    sub3 = dot.subgraph()
    sub3.node("a")
    assert sub3 not in (sub1, sub2)
    sub4 = dot.subgraph()
    sub4.node("a")
    assert sub4 not in (sub1, sub2, sub3)
    expect_str(dot,
    """
    graph {
        subgraph sub1 {
            a
        }
        subgraph sub2 {
        }
        subgraph {
        }
        subgraph {
        }
    }
    """)



def test_edge_identity():
    """
    Only the node id part of port specifications matters for edge identity.
    With respect to identify, non-directed graph endpoints are unordered,
    however order is preserved and can be amended because it can matter to
    graphviz.  For multigraphs, discriminants are required for complete edge
    identity.  Multigraph edges without discriminants are always distinct.
    """
    dot = Dot()
    dot.edge("a","b",a1=1)
    dot.edge(Port("a","next",cp="n"),"b",a2=2)
    dot.edge(Port("a","next",cp="n"),Port("b","prev","s"),a3=3)
    dot.edge(Port("b"),Port("a"),a4=4)
    assert dot.edge_is_defined("a","b")
    assert dot.edge_is_defined("b","a")
    expect_str(dot,
    """
    graph {
        b -- a [a1=1 a2=2 a3=3 a4=4]
    }
    """)
    dot = Dot(directed=True)
    dot.edge("a","b",a1=1)
    dot.edge(Port("a","next",cp="n"),"b",a2=2)
    dot.edge(Port("a","next",cp="n"),Port("b","prev","s"),a3=3)
    assert dot.edge_is_defined("a","b")
    assert not dot.edge_is_defined("b","a")
    dot.edge(Port("b"),Port("a"),a4=4)
    assert dot.edge_is_defined("b","a")
    expect_str(dot,
    """
    digraph {
        a:next:n -> b:prev:s [a1=1 a2=2 a3=3]
        b -> a [a4=4]
    }
    """)
    dot = Dot(multigraph=True)
    dot.edge("a","b",a1=1)
    dot.edge("a","b",a2=2)
    dot.edge("a","b","x",a3=3)
    dot.edge("a","b","y",a4=4)
    dot.edge("a","b","x",a5=5)
    dot.edge("a","b","y",a6=6)
    assert not dot.edge_is_defined("a","b")
    assert not dot.edge_is_defined("b","a")
    assert dot.edge_is_defined("a","b","x")
    assert dot.edge_is_defined("a","b","y")
    assert dot.edge_is_defined("b","a","x")
    assert dot.edge_is_defined("b","a","y")
    assert not dot.edge_is_defined("a","b","z")
    expect_str(dot,
    """
    graph {
        a -- b [a1=1]
        a -- b [a2=2]
        a -- b [a3=3 a5=5]
        a -- b [a4=4 a6=6]
    }
    """)
    dot = Dot(directed=True, multigraph=True)
    dot.edge("a","b",a1=1)
    dot.edge("a","b",a2=2)
    dot.edge("a","b","x",a3=3)
    dot.edge("a","b","y",a4=4)
    dot.edge("a","b","x",a5=5)
    assert not dot.edge_is_defined("a","b")
    assert not dot.edge_is_defined("b","a")
    assert dot.edge_is_defined("a","b","x")
    assert dot.edge_is_defined("a","b","y")
    assert not dot.edge_is_defined("b","a","x")
    assert not dot.edge_is_defined("b","a","y")
    assert not dot.edge_is_defined("a","b","z")
    dot.edge("b","a","y",a6=6)
    assert dot.edge_is_defined("b","a","y")
    expect_str(dot,
    """
    digraph {
        a -> b [a1=1]
        a -> b [a2=2]
        a -> b [a3=3 a5=5]
        a -> b [a4=4]
        b -> a [a6=6]
    }
    """)


def test_endpoint_swapping():
    """
    When amending an edge, endpoints of an edge can be swapped.
    """
    dot = Dot()
    dot.edge("a","b")
    dot.edge("c","d")
    dot.edge("e","f")
    dot.edge("g","h")

    dot.edge("b", "a")
    dot.edge(Port("d"), "c")
    dot.edge("f", Port("e"))
    dot.edge(Port("h"), Port("g"))

    expect_str(dot,
    """
    graph {
        b -- a
        d -- c
        f -- e
        h -- g
    }
    """)



def test_disc_for_mg_only():
    """
    Discriminants may not be specified for non-multigraphs.
    """
    expect_ex(ValueError,lambda: Dot().edge("a","b","x"))


def test_subgraph_identity():
    """
    Subgraph identity is scoped to parents.
    """
    dot = Dot()
    sub1 = dot.subgraph(id="sub1")
    sub1_sub2 = sub1.subgraph(id="sub2")
    assert dot.subgraph(id="sub1") is sub1
    assert sub1.subgraph(id="sub2") is sub1_sub2
    assert dot.subgraph(id="sub2") is not sub1_sub2


def test_subgraph_scoping():
    """
    Nodes and edges are scoped to the root dot object, but appear in the graph
    or subgraph in which they are first defined.  Roles are also scoped to the
    root dot object, but may be defined or amended in the root or any subgraph.
    Default attributes are specific to the graph or subgraph.
    """
    def add_defaults(dot:Dot, value:str):
        dot.graph_default(a1=value)
        dot.node_default(a2=value)
        dot.edge_default(a3=value)

    dot = Dot(id="Root")
    subdot = dot.subgraph("Sub")
    subsubdot = subdot.subgraph("SubSub")

    add_defaults(dot,"root")
    add_defaults(subdot,"sub")
    add_defaults(subsubdot,"subsub")

    dot.node("a")
    subdot.node("b")
    subsubdot.node("c")

    dot.edge("a","b")
    subdot.edge("b","c")
    subsubdot.edge("c","a")

    def assign(dot:Dot, name:str, value):
        kv={name:value}
        dot.node("a",**kv)
        dot.node("b",**kv)
        dot.node("c",**kv)
        dot.edge("a","b",**kv)
        dot.edge("b","c",**kv)
        dot.edge("c","a",**kv)
        dot.graph_role("test",**kv)
        dot.node_role("test",**kv)
        dot.edge_role("test",**kv)

    assign(dot,"by_root",1)
    assign(subdot,"by_sub",2)
    assign(subsubdot,"by_subsub",3)

    dot.node("x",role="test")
    subdot.node("y",role="test")
    subsubdot.node("z",role="test")

    dot.edge("x","x",role="test")
    subdot.edge("y","y",role="test")
    subsubdot.edge("z","z",role="test")

    expect_str(dot,
    """
    graph Root {
        graph [a1=root]
        node  [a2=root]
        edge  [a3=root]
        a      [by_root=1 by_sub=2 by_subsub=3]
        x      [by_root=1 by_sub=2 by_subsub=3]
        a -- b [by_root=1 by_sub=2 by_subsub=3]
        x -- x [by_root=1 by_sub=2 by_subsub=3]
        subgraph Sub {
            graph [a1=sub]
            node  [a2=sub]
            edge  [a3=sub]
            b      [by_root=1 by_sub=2 by_subsub=3]
            y      [by_root=1 by_sub=2 by_subsub=3]
            b -- c [by_root=1 by_sub=2 by_subsub=3]
            y -- y [by_root=1 by_sub=2 by_subsub=3]
            subgraph SubSub {
                graph [a1=subsub]
                node  [a2=subsub]
                edge  [a3=subsub]
                c      [by_root=1 by_sub=2 by_subsub=3]
                z      [by_root=1 by_sub=2 by_subsub=3]
                c -- a [by_root=1 by_sub=2 by_subsub=3]
                z -- z [by_root=1 by_sub=2 by_subsub=3]
            }
        }
    }
    """)


def test_copy():
    """
    Copies should be faithful, and should allow the graph and comment to be
    changed.  A copy should have the identical theme as the original.
    """
    dot = Dot(id="Original", comment="V1")
    dot.graph_default(dpi=72)
    dot.node_default(shape="square")
    dot.edge_default(color="lime")
    dot.graph(labelloc="t", label="Label")
    dot.node("a")
    dot.edge("a","b")
    dot.graph_role("gr",a1=1)
    dot.node_role("nr",a2=2)
    dot.edge_role("er",a3=3)
    subdot = dot.subgraph(id="Subgraph1")
    subdot.graph_default(dpi=300)
    subdot.node_default(shape="circle")
    subdot.edge_default(color="red")
    subdot.graph(label="SubLabel1")
    subdot.graph(rankdir="LTR", role="gr")
    subdot.node("c", role="nr")
    subdot.edge("c","d", role="er")

    DOT= """
    // {comment}
    graph {id} {{
        graph [dpi=72]
        node [shape=square]
        edge [color=lime]
        labelloc = t
        a
        a -- b
        subgraph Subgraph1 {{
            graph [dpi=300]
            node [shape=circle]
            edge [color=red]
            rankdir = LTR
            a1=1
            c [a2=2]
            c -- d [a3=3]
            label = "SubLabel1"
        }}
        label = "Label"
    }}
    """

    expect_str(dot.copy(),DOT.format(id="Original",comment="V1"))

    expect_str(dot.copy(id="Copy"),DOT.format(id="Copy",comment="V1"))

    expect_str(dot.copy(comment="V2"),DOT.format(id="Original",comment="V2"))

    expect_str(dot.copy(id="Copy",comment="V2"),
               DOT.format(id="Copy",comment="V2"))

    dot = Dot(strict=True, directed=True).copy()
    expect_str(dot,
    """
    strict digraph {
    }
    """)

    dot = Dot()
    assert not dot.is_multigraph()
    assert not dot.copy().is_multigraph()

    dot = Dot(multigraph=True).edge("a","b")
    assert dot.is_multigraph()
    assert dot.copy().is_multigraph()

    theme = Dot()
    dot = Dot()
    dot.use_theme(theme)
    other = dot.copy()
    theme.node_default(x=1)
    expect_str(dot,"""
    graph {
        node [x=1]
    }
    """)
    assert str(dot) == str(other)


def test_parent():
    """
    Method parent() should return the dot object's parent, if any.
    """
    dot = Dot()
    subdot = dot.subgraph()
    assert dot.parent() is None
    assert subdot.parent() is dot


def test_chaining():
    """
    Most Dot methods should return self.
    """
    dot = Dot()
    assert dot is dot.graph_default()
    assert dot is dot.graph_role("test")
    assert dot is dot.graph()
    assert dot is dot.node_default()
    assert dot is dot.node_role("test")
    assert dot is dot.node("a")
    assert dot is dot.node_define("b")
    assert dot is dot.node_update("a")
    assert dot is dot.edge_default()
    assert dot is dot.edge_role("test")
    assert dot is dot.edge("a","b")
    assert dot is dot.edge_define("a","c")
    assert dot is dot.edge_update("a","c")
    assert dot is dot.use_theme(Dot())
    assert dot is dot.all_default()
    assert dot is dot.all_role("test")


def test_deepcopy():
    """
    Deep copy of a container referencing dot objects should maintain reference
    aliases.
    """
    dot = Dot(id="Canary")
    subject = [ dot, dot ]
    other = deepcopy(subject)
    assert other[0] is other[1]
    assert other[0] is not subject[0]
