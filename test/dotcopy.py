from copy import deepcopy
from gvdot import Dot
from utility import expect_str, expect_ex


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
    subblock = dot.subgraph(id="Subgraph1")
    subblock.graph_default(dpi=300)
    subblock.node_default(shape="circle")
    subblock.edge_default(color="red")
    subblock.graph(label="SubLabel1")
    subblock.graph(rankdir="LTR", role="gr")
    subblock.node("c", role="nr")
    subblock.edge("c","d", role="er")

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
