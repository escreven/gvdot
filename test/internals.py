from typing import Any
from gvdot import Dot, _NormPort, _Edge


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
    the entry, otherwise it should duplicate the instance and add an entry.
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
