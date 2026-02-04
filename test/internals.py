from gvdot import Dot, _NormPort, _Nonce, _Edge


def test_reprs():
    """
    Exercise __repr__ methods of non-public classes.
    """
    normport1 = _NormPort("a")
    normport2 = _NormPort("b")
    assert "_Nonce" in repr(_Nonce())
    assert "_Edge" in repr(_Edge(Dot(),normport1,normport2,None))
    assert "_NormPort" in repr(normport1)


def test_nonce():
    """
    Make sure nonces are equal iff identical.
    """
    nonce1 = _Nonce()
    nonce2 = _Nonce()
    assert nonce1 == nonce1
    assert nonce2 == nonce2
    assert nonce1 != nonce2


