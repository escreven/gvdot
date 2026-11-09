from typing import Any
from gvdot import Dot, _NormPort, _Edge, _Digraph
from gvdot.markup import _ALLOWED_ROOTS, TR, TD, VR
from utility import expect_ex


def test_reprs():
    """
    Exercise __repr__ methods of non-public classes.
    """
    normport1 = _NormPort("a")
    normport2 = _NormPort("b")
    assert "_Edge" in repr(_Edge(False,normport1,normport2,None))
    assert "_NormPort" in repr(normport1)


def test_dot_deepcopy():
    """
    Dot __deepcopy__ must check for entry in memo.  If present, it must return
    the entry. Otherwise, it should duplicate the instance and add an entry.
    """
    memo:dict[int,Any] = {}
    dot1 = Dot()
    dot2 = dot1.__deepcopy__(memo)
    assert dot2 is not dot1
    assert id(dot1) in memo
    assert memo[id(dot1)] is dot2
    dot3 = dot1.__deepcopy__(memo)
    assert dot3 is dot2
    assert id(dot1) in memo
    assert memo[id(dot1)] is dot2


def test_digraph_self_loop():
    """
    The _Digraph.add_arc() method used by impose_order() should raise an
    exception if given a self-loop.  Because impose_order() filters out
    self-loops while constructing the graph, we must test that here.
    """
    digraph = _Digraph()
    expect_ex(AssertionError,lambda: digraph.add_arc("a","a"))


def test_role_compaction():
    """
    Duplicated roles should not be accumulated.  Because of the attribute
    assignment precedence rules, it isn't possible to test this by examining
    generated DOT language.
    """
    #
    # NOTE: The implementation tracks roles in highest to lowest precedence
    # order.
    #
    a = "a"; b = "b"; c = "c"
    dot = Dot()
    dot.node_role("a",a=1)
    dot.node_role("b",b=1)
    dot.node_role("c",c=1)
    dot.node("x",role=(a,b,c,c,b,a,a,b,c))
    x = dot.nodemap["x"]
    assert x.roles == [ "c", "b", "a"]
    for _ in range(10):
        dot.node("x",role=(...,...,"c","b","a",...,...))
    assert x.roles == [ "c", "b", "a"]


def test_bad_vr_at_root():
    """
    The Graphviz HTML grammar requires VR elements to be between table cells.
    There is a supporting validation in Managed.__str__().  However it's not
    possible to reach that code because TR is the only allowed parent of VR,
    and TR is not an allowed root.  We prefer to keep the VR check in __str__()
    in case __str__() is ever rearranged -- so we temporarily allow TR roots to
    test that validation code.
    """
    try:
        assert TR not in _ALLOWED_ROOTS
        _ALLOWED_ROOTS.add(TR)
        expect_ex(RuntimeError, lambda: str(TR(TD("x"),VR())))
    finally:
        _ALLOWED_ROOTS.remove(TR)
