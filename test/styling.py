from gvdot import Dot
from utility import expect_ex, expect_str


def test_roles():
    """
    Graphs, nodes, and edges can have roles from which attribute value
    assignments are inherited.  Explicitly assigned values should have
    precedence.  Roles are amendable.
    """
    dot = Dot()
    dot.graph_role("primary",explicit="hidden",implicit="graph_implicit_1")
    dot.node_role ("primary",explicit="hidden",implicit="node_implicit_1")
    dot.edge_role ("primary",explicit="hidden",implicit="edge_implicit_1")
    dot.graph_role("secondary",other="graph_other")
    dot.node_role ("secondary",other="node_other")
    dot.edge_role ("secondary",other="edge_other")
    dot.graph(explicit="graph_explicit")
    dot.node("a",explicit="node_explicit")
    dot.edge("a","b",explicit="edge_explicit")
    expect_str(dot,
    """
    graph {
        explicit=graph_explicit
        a [ explicit=node_explicit ]
        a -- b [ explicit=edge_explicit ]
    }
    """)

    dot.graph(role="primary")
    dot.node("a",role="primary")
    dot.edge("a","b",role="primary")
    expect_str(dot,
    """
    graph {
        explicit=graph_explicit
        implicit=graph_implicit_1
        a      [ explicit=node_explicit implicit=node_implicit_1]
        a -- b [ explicit=edge_explicit implicit=edge_implicit_1]
    }
    """)

    dot.graph_role("primary",implicit="graph_implicit_2")
    dot.node_role ("primary",implicit="node_implicit_2")
    dot.edge_role ("primary",implicit="edge_implicit_2")
    expect_str(dot,
    """
    graph {
        explicit=graph_explicit
        implicit=graph_implicit_2
        a      [ explicit=node_explicit implicit=node_implicit_2]
        a -- b [ explicit=edge_explicit implicit=edge_implicit_2]
    }
    """)

    dot.graph(role="secondary")
    dot.node("a",role="secondary")
    dot.edge("a","b",role="secondary")
    expect_str(dot,
    """
    graph {
        explicit=graph_explicit
        other=graph_other
        a      [ explicit=node_explicit other=node_other]
        a -- b [ explicit=edge_explicit other=edge_other]
    }
    """)


def test_all_role():
    """
    Graph, node, and edge roles can be defined and amended all at once.
    """
    dot = Dot()
    dot.all_role("test",a1=1)
    dot.graph_role("test",b1=1, a2=2)
    dot.node_role("test",b1=1, a3=3)
    dot.edge_role("test",b1=1, a4=4)
    dot.all_role("test",b1=2)
    dot.graph(role="test")
    dot.node("a",role="test")
    dot.edge("a","b",role="test")
    expect_str(dot,
    """
    graph {
        a1=1
        b1=2
        a2=2
        a [ a1=1 a3=3 b1=2 ]
        a -- b [ a1=1 a4=4 b1=2 ]
    }
    """)


def test_roles_limited():
    """
    Roles may not be assignd to default attributes or other roles.
    """
    dot = Dot()
    expect_ex(ValueError, lambda: dot.graph_default(role="test"))
    expect_ex(ValueError, lambda: dot.node_default(role="test"))
    expect_ex(ValueError, lambda: dot.edge_default(role="test"))
    expect_ex(ValueError, lambda: dot.graph_role("recurse",role="test"))
    expect_ex(ValueError, lambda: dot.node_role("recurse",role="test"))
    expect_ex(ValueError, lambda: dot.edge_role("recurse",role="test"))


def test_unusual_role_names():
    """
    Role names are strings, but they are not limited to being identifier-like.
    They can contain spaces, double-quotes, and anything else and ID str can
    contain.
    """
    dot = Dot()
    dot.node_role("the node", color="blue")
    dot.edge_role('the "edge"', style="dashed")
    dot.graph_role(" <the graph> ", rankdir="LR")
    dot.node("a", role="the node")
    dot.edge("a", "b", role='the "edge"')
    dot.graph(role=" <the graph> ")

    expect_str(dot,"""
    graph {
        rankdir=LR
        a [color=blue]
        a -- b [style=dashed]
    }
    """)

def test_roles_must_be_defined():
    """
    Assigned roles must eventually be defined, but not need to be defined
    before the DOT language representation is created.
    """

    dot1 = Dot().graph(role="test")
    dot2 = Dot().node("a",role="test")
    dot3 = Dot().edge("a","b",role="test")

    expect_ex(RuntimeError,lambda: str(dot1))
    expect_ex(RuntimeError,lambda: str(dot2))
    expect_ex(RuntimeError,lambda: str(dot3))

    dot1.graph_role("test")
    dot2.node_role("test")
    dot3.edge_role("test")

    str(dot1)
    str(dot2)
    str(dot3)


def test_theme_precedence():
    """
    Using the theme of another dot object should apply its default attributes,
    graph attributes, and roles, but not its nodes, edges, and subgraphs.
    Assigned attribute values of the target dot object should prevail over
    theme values.
    """
    def add_attrs(dot:Dot, name:str, source:str):
        def kv(n:int):
            return { name: f"{source}_{n}" }
        dot.graph_default(**kv(1))
        dot.node_default(**kv(2))
        dot.edge_default(**kv(3))
        dot.graph(**kv(4))
        dot.node("a",**kv(5))
        dot.edge("a","b",**kv(6))
        dot.node_role("test",**kv(8))
        dot.edge_role("test",**kv(9))

    dot = Dot()
    add_attrs(dot, "a", "target")
    dot.graph(role="test")
    dot.node("x",role="test")
    dot.edge("x","y",role="test")
    dot.subgraph(id="TargetSub")

    theme = Dot(directed=True, strict=True, id="Theme", comment="Theme")
    add_attrs(theme, "a", "theme")
    add_attrs(theme, "b", "theme")
    theme.graph_role("test",c="theme")
    theme.node("x",should_not_have=True)
    theme.node("y")
    theme.edge("x","y",should_not_have=True)
    theme.subgraph(id="ThemeSub")

    dot.use_theme(theme)

    expect_str(dot,
    """
    graph {
        graph  [ a=target_1 b=theme_1 ]
        node   [ a=target_2 b=theme_2 ]
        edge   [ a=target_3 b=theme_3 ]
        a=target_4
        b=theme_4
        c=theme
        a      [ a=target_5 ]
        x      [ a=target_8 b=theme_8 ]
        a -- b [ a=target_6 ]
        x -- y [ a=target_9 b=theme_9 ]
        subgraph TargetSub {
        }
    }
    """)


def test_theme_dynamics():
    """
    Using themes shouldn't modify the base object.  Switching themes should
    cause the DOT language representation to shift to the new theme.
    Modifications to a theme should be immediately reflected in all dot objects
    inheriting from the theme.
    """
    theme1 = Dot().node_default(a=1,b=1,c=1)
    theme2 = Dot().node_default(b=2,c=2)
    theme3 = Dot().node_default(c=3)

    dot = Dot()

    dot.use_theme(theme1)
    expect_str(dot,"""
    graph {
        node [ a=1 b=1 c=1 ]
    }
    """)

    dot.use_theme(theme2)
    expect_str(dot,"""
    graph {
        node [ b=2 c=2 ]
    }
    """)

    dot = dot.use_theme(theme3)
    expect_str(dot,"""
    graph {
        node [ c=3 ]
    }
    """)

    theme2.use_theme(theme1)
    theme3.use_theme(theme2)

    expect_str(dot,"""
    graph {
        node [ a=1 b=2 c=3 ]
    }
    """)

    dot.use_theme(theme2)
    expect_str(dot,"""
    graph {
        node [ a=1 b=2 c=2 ]
    }
    """)

    theme1.node_default(a=100, d=100)
    expect_str(dot,"""
    graph {
        node [ a=100 b=2 c=2 d=100 ]
    }
    """)

    dot.use_theme(None)
    expect_str(dot,"""
    graph {
    }
    """)


def test_theme_errors():
    """
    Attempting to form a theme cycle should raise an exception.  Themes and the
    dot objects that use them must be root objects.
    """
    theme1 = Dot().node_role("test",a=1,b=1,c=1)
    theme2 = Dot().node_role("test",b=2,c=2)
    theme3 = Dot().node_role("test",c=3)

    expect_ex(ValueError, lambda: theme1.use_theme(theme1))

    theme2.use_theme(theme1)
    expect_ex(ValueError, lambda: theme1.use_theme(theme2))

    theme3.use_theme(theme2)
    expect_ex(ValueError, lambda: theme1.use_theme(theme3))

    dot1 = Dot()
    dot2 = Dot()
    sub2 = dot2.subgraph()

    expect_ex(RuntimeError, lambda: dot1.use_theme(sub2))  #type:ignore


def test_subgraphs_see_theme_roles():
    """
    Inherited roles should be assignable to entities defined through subgraph
    dot objects.
    """
    theme = Dot().all_role("test",x=1)
    dot = Dot().use_theme(theme)
    subblock = dot.subgraph()
    subblock.graph(role="test")
    subblock.node("a",role="test")
    subblock.edge("a","b",role="test")
    expect_str(dot,"""
    graph {
        subgraph {
            x=1
            a [x=1]
            a -- b [x=1]
        }
    }
    """)
