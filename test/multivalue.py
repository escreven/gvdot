from typing import Any

from gvdot import Dot, Block
from utility import expect_edge, expect_ex, expect_graph, expect_node, expect_str, parse


#
# An initial Dot object for tests including non-role attributes.
#

def _general(dot:Dot) -> Dot:

    dot.graph_role(f"role1",gra=1,grb=1)
    dot.node_role (f"role1",nra=1,nrb=1)
    dot.edge_role (f"role1",era=1,erb=1)

    dot.graph_default(gda=1,gdb=1)
    dot.node_default (nda=1,ndb=1)
    dot.edge_default (eda=1,edb=1)
    dot.graph        (ga=1,gb=1,role="role1")

    dot.node("node1",na=1,nb=1,role="role1")
    dot.edge("node1","node1",ea=1,eb=1,role="role1")

    return dot

#
# Role definitions for detecting order
#

def _ordered_roles(dot:Dot) -> Dot:
    dot.all_role("a", a=1, a_vs_b="a", a_vs_c="a")
    dot.all_role("b", b=1, a_vs_b="b", b_vs_c="b")
    dot.all_role("c", c=1, a_vs_c="c", b_vs_c="c")
    return dot

def _order_sig(role1:str, role2:str, role3:str) -> dict[str,str]:
    t = (role1,role2,role3)
    def superior(u,v):
        return v if t.index(v) > t.index(u) else u
    d = dict[str,Any](a="1",b="1",c="1")
    d['a_vs_b'] = superior('a','b')
    d['a_vs_c'] = superior('a','c')
    d['b_vs_c'] = superior('b','c')
    return d


def test_empty():
    """
    An empty tuple attribute value is equivalent to None.
    """
    #
    # Delete non-role attributes.
    #

    dot = _general(Dot())
    dot.graph_role("role1",gra=())
    dot.node_role ("role1",nra=())
    dot.edge_role ("role1",era=())
    dot.graph_default(gda=())
    dot.node_default(nda=())
    dot.edge_default(eda=())
    dot.graph(ga=())
    dot.node("node1",na=())
    dot.edge("node1","node1",ea=())

    expect_str(dot,"""
    graph {
        graph [gdb=1]
        node [ndb=1]
        edge [edb=1]
        gb=1
        grb=1
        node1 [nb=1 nrb=1]
        node1 -- node1 [eb=1 erb=1]
    }
    """)

    #
    # Delete roles.
    #

    dot = _general(Dot())
    dot.graph(role=())
    dot.node("node1",role=())
    dot.edge("node1","node1",role=())

    expect_str(dot,"""
    graph {
        graph [gda=1 gdb=1]
        node [nda=1 ndb=1]
        edge [eda=1 edb=1]
        ga=1
        gb=1
        node1 [na=1 nb=1]
        node1 -- node1 [ea=1 eb=1]
    }
    """)


def test_id_singleton():
    """
    A non-Ellipsis singleton is the same as an ID.
    """
    #
    # Assign non-role attribute values.
    #

    dot = _general(Dot())
    dot.graph_role("role1",gra=(2,))
    dot.node_role ("role1",nra=(2,))
    dot.edge_role ("role1",era=(2,))
    dot.graph_default(gda=(2,))
    dot.node_default(nda=(2,))
    dot.edge_default(eda=(2,))
    dot.graph(ga=(2,))
    dot.node("node1",na=(2,))
    dot.edge("node1","node1",ea=(2,))

    expect_str(dot,"""
    graph {
        graph [gda=2 gdb=1]
        node [nda=2 ndb=1]
        edge [eda=2 edb=1]
        ga=2
        gb=1
        gra=2
        grb=1
        node1 [na=2 nb=1 nra=2 nrb=1]
        node1 -- node1 [ea=2 eb=1 era=2 erb=1]
    }
    """)

    #
    # Assign roles.
    #

    dot = _general(Dot())
    dot.graph_role("role2",grc=1)
    dot.node_role ("role2",nrc=1)
    dot.edge_role ("role2",erc=1)
    dot.graph(role=("role2",))
    dot.node("node1",role=("role2",))
    dot.edge("node1","node1",role=("role2",))

    expect_str(dot,"""
    graph {
        graph [gda=1 gdb=1]
        node [nda=1 ndb=1]
        edge [eda=1 edb=1]
        ga=1
        gb=1
        grc=1
        node1 [na=1 nb=1 nrc=1]
        node1 -- node1 [ea=1 eb=1 erc=1]
    }
    """)


def test_ellipsis_singleton():
    """
    An Ellipsis singleton does not change the attribute value, or provide a
    value if none exists.
    """
    #
    # No change to existing attributes.
    #

    dot = _general(Dot())
    dot.graph_role("role1",gra=(...,))
    dot.node_role ("role1",nra=(...,))
    dot.edge_role ("role1",era=(...,))
    dot.graph_default(gda=(...,))
    dot.node_default(nda=(...,))
    dot.edge_default(eda=(...,))
    dot.graph(ga=(...,),role=(...,))
    dot.node("node1",na=(...,),role=(...,))
    dot.edge("node1","node1",ea=(...,),role=(...,))

    expect_str(dot,"""
    graph {
        graph [gda=1 gdb=1]
        node [nda=1 ndb=1]
        edge [eda=1 edb=1]
        ga=1
        gb=1
        gra=1
        grb=1
        node1 [na=1 nb=1 nra=1 nrb=1]
        node1 -- node1 [ea=1 eb=1 era=1 erb=1]
    }
    """)

    #
    # No definition of non-existent attributes.
    #

    dot = Dot()  # <-- not populated
    dot.graph_role("role1",gra=(...,))
    dot.node_role ("role1",nra=(...,))
    dot.edge_role ("role1",era=(...,))
    dot.graph_default(gda=(...,))
    dot.node_default(nda=(...,))
    dot.edge_default(eda=(...,))
    dot.graph(ga=(...,),role=(...,))
    dot.node("node1",na=(...,),role=(...,))
    dot.edge("node1","node1",ea=(...,),role=(...,))

    expect_str(dot,"""
    graph {
        node1
        node1 -- node1
    }
    """)


def test_effective_singletons():
    """
    Duplicate filtering means surprising forms are effectively singletons.
    """
    #
    # Define non-role attribute values.
    #

    for value in [ (...,2), (2,...), (...,2,...), (2,2) ]:
        dot = _general(Dot())
        dot.graph_role("role1",grc=value)
        dot.node_role ("role1",nrc=value)
        dot.edge_role ("role1",erc=value)
        dot.graph_default(gdc=value)
        dot.node_default(ndc=value)
        dot.edge_default(edc=value)
        dot.graph(gc=value)
        dot.node("node1",nc=value)
        dot.edge("node1","node1",ec=value)
        expect_str(dot,"""
        graph {
            graph [gda=1 gdb=1 gdc=2]
            node [nda=1 ndb=1 ndc=2]
            edge [eda=1 edb=1 edc=2]
            ga=1
            gb=1
            gc=2
            gra=1
            grb=1
            grc=2
            node1 [na=1 nb=1 nc=2 nra=1 nrb=1 nrc=2]
            node1 -- node1 [ea=1 eb=1 ec=2 era=1 erb=1 erc=2]
        }
        """)

    #
    # Amend non-role attribute values.
    #

    for value in [ (...,1), (1,...), (...,1,...), (1,1) ]:
        dot = _general(Dot())
        dot.graph_role("role1",gra=value)
        dot.node_role ("role1",nra=value)
        dot.edge_role ("role1",era=value)
        dot.graph_default(gda=value)
        dot.node_default(nda=value)
        dot.edge_default(eda=value)
        dot.graph(ga=value)
        dot.node("node1",na=value)
        dot.edge("node1","node1",ea=value)
        expect_str(dot,"""
        graph {
            graph [gda=1 gdb=1]
            node [nda=1 ndb=1]
            edge [eda=1 edb=1]
            ga=1
            gb=1
            gra=1
            grb=1
            node1 [na=1 nb=1 nra=1 nrb=1]
            node1 -- node1 [ea=1 eb=1 era=1 erb=1]
        }
        """)

    #
    # Role assignments.
    #

    for value in [ (...,"role1"), ("role1",...),
                   (...,"role1",...), ("role1","role1") ]:
        dot = Dot()
        dot.graph_role("role1",gra=1)
        dot.node_role ("role1",nra=1)
        dot.edge_role ("role1",era=1)
        dot.graph(role=value)
        dot.node("node1",role=value)
        dot.edge("node1","node1",role=value)
        expect_str(dot,"""
        graph {
            gra=1
            node1 [nra=1]
            node1 -- node1 [era=1]
        }
        """)


def test_non_role_multivalue():
    """
    Assigning multiple values to non-role attributes raises ValueError.
    """
    dot = Dot()

    expect_ex(ValueError, lambda: dot.graph_role("test",x=("a","b")))
    expect_ex(ValueError, lambda: dot.node_role("test",x=("a","b")))
    expect_ex(ValueError, lambda: dot.edge_role("test",x=("a","b")))
    expect_ex(ValueError, lambda: dot.graph_default(x=("a","b")))
    expect_ex(ValueError, lambda: dot.node_default(x=("a","b")))
    expect_ex(ValueError, lambda: dot.edge_default(x=("a","b")))
    expect_ex(ValueError, lambda: dot.graph(x=("a","b")))
    expect_ex(ValueError, lambda: dot.node("node1",x=("a","b")))
    expect_ex(ValueError, lambda: dot.edge("u","v",x=("a","b")))

    expect_ex(ValueError, lambda: dot.graph_role("test",role_=("a","b")))
    expect_ex(ValueError, lambda: dot.node_role("test",role_=("a","b")))
    expect_ex(ValueError, lambda: dot.edge_role("test",role_=("a","b")))
    expect_ex(ValueError, lambda: dot.graph_default(role_=("a","b")))
    expect_ex(ValueError, lambda: dot.node_default(role_=("a","b")))
    expect_ex(ValueError, lambda: dot.edge_default(role_=("a","b")))
    expect_ex(ValueError, lambda: dot.graph(role_=("a","b")))
    expect_ex(ValueError, lambda: dot.node("node1",role_=("a","b")))
    expect_ex(ValueError, lambda: dot.edge("u","v",role_=("a","b")))

    dot.graph_role("test",x="a")
    dot.node_role("test",x="a")
    dot.edge_role("test",x="a")
    dot.graph_default(x="a")
    dot.node_default(x="a")
    dot.edge_default(x="a")
    dot.graph(x="a")
    dot.node("node1",x="a")
    dot.edge("u","v",x="a")

    expect_ex(ValueError, lambda: dot.graph_role("test",x=(...,"b")))
    expect_ex(ValueError, lambda: dot.node_role("test",x=(...,"b")))
    expect_ex(ValueError, lambda: dot.edge_role("test",x=(...,"b")))
    expect_ex(ValueError, lambda: dot.graph_default(x=(...,"b")))
    expect_ex(ValueError, lambda: dot.node_default(x=(...,"b")))
    expect_ex(ValueError, lambda: dot.edge_default(x=(...,"b")))
    expect_ex(ValueError, lambda: dot.graph(x=(...,"b")))
    expect_ex(ValueError, lambda: dot.node("node1",x=(...,"b")))
    expect_ex(ValueError, lambda: dot.edge("u","v",x=(...,"b")))


def test_role_multivalue():
    """
    Multiple roles can be assigned to graphs, nodes, and edges.  Role order as
    assigned is lowest to highest precedence.  Duplication is no problem -- the
    last appearance is the one that matters.
    """
    a = "a"; b = "b"; c = "c"

    #
    # Initial definition order.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b,c))
    dot.node("node1",        role=(a,b,c))
    dot.edge("node1","node2",role=(a,b,c))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(a,b,c))
    expect_node(lines,"node1",        _order_sig(a,b,c))
    expect_edge(lines,"node1","node2",_order_sig(a,b,c))

    #
    # Amended order.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b,c))
    dot.node("node1",        role=(a,b,c))
    dot.edge("node1","node2",role=(a,b,c))

    dot.graph(               role=(c,a,b))
    dot.node("node1",        role=(c,a,b))
    dot.edge("node1","node2",role=(c,a,b))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(c,a,b))
    expect_node(lines,"node1",        _order_sig(c,a,b))
    expect_edge(lines,"node1","node2",_order_sig(c,a,b))

    #
    # Duplication.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b,c,c,b,a))
    dot.node("node1",        role=(a,b,c,c,b,a))
    dot.edge("node1","node2",role=(a,b,c,c,b,a))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(c,b,a))
    expect_node(lines,"node1",        _order_sig(c,b,a))
    expect_edge(lines,"node1","node2",_order_sig(c,b,a))

    #
    # Check the full DOT text.
    #

    expect_str(dot,"""
    graph {
        a=1
        a_vs_b=a
        a_vs_c=a
        b=1
        b_vs_c=b
        c=1
        node1 [c=1 a_vs_c=a b_vs_c=b b=1 a_vs_b=a a=1]
        node1 -- node2 [c=1 a_vs_c=a b_vs_c=b b=1 a_vs_b=a a=1]
    }
    """)


def test_bad_tuple():
    """
    The elements of a tuple must be IDs or Ellipsis objects.  Only tuples can
    be used for multiple values; lists cannot.
    """
    dot = Dot()
    expect_ex(ValueError, lambda: dot.graph(role=( b'bytes' ,))) # type:ignore
    expect_ex(ValueError, lambda: dot.graph(role=( ()       ,))) # type:ignore
    expect_ex(ValueError, lambda: dot.graph(role=( []       ,))) # type:ignore
    expect_ex(ValueError, lambda: dot.graph(role=( None     ,))) # type:ignore
    expect_ex(ValueError, lambda: dot.graph(role=[ "a"      ,])) # type:ignore


def test_role_ellipses():
    """
    Ellipsis can represent existing multiple assigned roles, allowing roles to
    be appended, prepended, and shifted to the end.  Ellipsis can appear more
    than once and repetition does not cause duplication issues.
    """
    a = "a"; b = "b"; c = "c"

    #
    # Noop.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b,c))
    dot.node("node1",        role=(a,b,c))
    dot.edge("node1","node2",role=(a,b,c))

    dot.graph(               role=(...,))
    dot.node("node1",        role=(...,))
    dot.edge("node1","node2",role=(...,))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(a,b,c))
    expect_node(lines,"node1",        _order_sig(a,b,c))
    expect_edge(lines,"node1","node2",_order_sig(a,b,c))

    #
    # Appending a role.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b))
    dot.node("node1",        role=(a,b))
    dot.edge("node1","node2",role=(a,b))

    dot.graph(               role=(...,c))
    dot.node("node1",        role=(...,c))
    dot.edge("node1","node2",role=(...,c))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(a,b,c))
    expect_node(lines,"node1",        _order_sig(a,b,c))
    expect_edge(lines,"node1","node2",_order_sig(a,b,c))

    #
    # Prepending a role.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(b,c))
    dot.node("node1",        role=(b,c))
    dot.edge("node1","node2",role=(b,c))

    dot.graph(               role=(a,...))
    dot.node("node1",        role=(a,...))
    dot.edge("node1","node2",role=(a,...))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(a,b,c))
    expect_node(lines,"node1",        _order_sig(a,b,c))
    expect_edge(lines,"node1","node2",_order_sig(a,b,c))

    #
    # Shifting a role to the end.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b,c))
    dot.node("node1",        role=(a,b,c))
    dot.edge("node1","node2",role=(a,b,c))

    dot.graph(               role=(...,b))
    dot.node("node1",        role=(...,b))
    dot.edge("node1","node2",role=(...,b))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(a,c,b))
    expect_node(lines,"node1",        _order_sig(a,c,b))
    expect_edge(lines,"node1","node2",_order_sig(a,c,b))

    #
    # Shifting a role to the beginning isn't possible....
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b,c))
    dot.node("node1",        role=(a,b,c))
    dot.edge("node1","node2",role=(a,b,c))

    dot.graph(               role=(b,...))
    dot.node("node1",        role=(b,...))
    dot.edge("node1","node2",role=(b,...))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(a,b,c))
    expect_node(lines,"node1",        _order_sig(a,b,c))
    expect_edge(lines,"node1","node2",_order_sig(a,b,c))

    #
    # ...unless we shift all other roles to the end.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b,c))
    dot.node("node1",        role=(a,b,c))
    dot.edge("node1","node2",role=(a,b,c))

    dot.graph(               role=(...,a,c))
    dot.node("node1",        role=(...,a,c))
    dot.edge("node1","node2",role=(...,a,c))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(b,a,c))
    expect_node(lines,"node1",        _order_sig(b,a,c))
    expect_edge(lines,"node1","node2",_order_sig(b,a,c))

    #
    # Massive duplication doesn't matter.
    #

    dot = _ordered_roles(Dot())
    dot.graph(               role=(a,b,c))
    dot.node("node1",        role=(a,b,c))
    dot.edge("node1","node2",role=(a,b,c))

    for _ in range(10):
        dot.graph(               role=(...,...,c,b,a))
        dot.node("node1",        role=(c,b,a,...,...))
        dot.edge("node1","node2",role=(...,c,b,a,...))

    lines = parse(str(dot))
    expect_graph(lines,               _order_sig(c,b,a))
    expect_node(lines,"node1",        _order_sig(a,b,c))
    expect_edge(lines,"node1","node2",_order_sig(a,b,c))


def test_theme_graph_mv_role():
    """
    A theme multivalued graph role assignment is inherited by Dot objects.
    """
    theme1 = Dot().graph_role("test1",x=1).graph_role("test2",y=1)
    theme2 = Dot().use_theme(theme1)
    dot = Dot().use_theme(theme2)
    theme1.graph(role=("test1","test2"))
    expect_str(dot,"""
    graph {
        y=1
        x=1
    }
    """)

    theme1 = Dot().graph_role("test1",x=1).graph_role("test2",y=1)
    theme2 = Dot().use_theme(theme1)
    dot = Dot().use_theme(theme2)
    theme2.graph(role=("test1","test2"))
    expect_str(dot,"""
    graph {
        y=1
        x=1
    }
    """)

    theme1 = Dot().graph_role("test1",x=1).graph_role("test2",y=1)
    theme2 = Dot().use_theme(theme1)
    dot = Dot().use_theme(theme2)
    dot.graph(role=("test1","test2"))
    expect_str(dot,"""
    graph {
        y=1
        x=1
    }
    """)

    theme1 = Dot().graph_role("test1",x=1).graph_role("test2",y=1)
    theme2 = Dot().use_theme(theme1)
    dot = Dot().use_theme(theme2)
    theme1.graph(role=("test1","test2"))
    dot.graph(x=2)
    expect_str(dot,"""
    graph {
        x=2
        y=1
    }
    """)


def test_nil():
    """
    This isn't a gvdot test -- it's a helper verification.
    """
    dot = _general(Dot())

    expect_str(dot,"""
    graph {
        graph [gda=1 gdb=1]
        node [nda=1 ndb=1]
        edge [eda=1 edb=1]
        ga=1
        gb=1
        gra=1
        grb=1
        node1 [na=1 nb=1 nra=1 nrb=1]
        node1 -- node1 [ea=1 eb=1 era=1 erb=1]
    }
    """)
