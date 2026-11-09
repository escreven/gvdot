from gvdot import Dot, Markup
from utility import expect_str, expect_ex


#
# We test the base gvdot.Markup class HTML behavior here.
#
# expect_str() cannot parse markup containing right angle brackets.  Tests
# with HTML tags compare the DOT text directly.
#


def test_labels():
    """
    Markup labels on graphs, subgraphs, nodes, and edges are enclosed in
    angle brackets rather than quotes, even when they contain no HTML tags.
    """
    dot = Dot()
    dot.graph(label=Markup("Graph"))
    dot.node("a",label=Markup("Node"))
    dot.edge("a","b",label=Markup("Edge"),
             headlabel=Markup("Head"),taillabel=Markup("Tail"))
    dot.subgraph("cluster_c").graph(label=Markup("Cluster"))
    expect_str(dot,"""
    graph {
        a [label=<Node>]
        a -- b [label=<Edge> headlabel=<Head> taillabel=<Tail>]
        subgraph cluster_c {
            label=<Cluster>
        }
        label=<Graph>
    }
    """)


def test_html():
    """
    HTML tags, quoted attributes, entities, backslashes, and newlines are
    preserved in markup.  Ordinary strings containing tags remain quoted.
    """
    dot = Dot()
    dot.node("a",label=Markup('<font color="red">A &amp; B</font>'))
    dot.node("b",label=Markup('<b>first</b>\n<i>second\\N</i>'))
    dot.node("c",label="<b>plain</b>")
    assert str(dot) == (
        'graph {\n'
        '    a [label=<<font color="red">A &amp; B</font>>]\n'
        '    b [label=<<b>first</b>\n<i>second\\N</i>>]\n'
        '    c [label="<b>plain</b>"]\n'
        '}\n'
    )


def test_subclass():
    """
    A Markup subclass can generate HTML without initializing markup.
    Its string representation is used wherever a label is assigned.
    """
    class X(Markup):
        def __init__(self, i:int):
            self.i = i

        def __str__(self) -> str:
            return f'x<sub><font point-size="10">{self.i}</font></sub>'

    dot = Dot()
    dot.graph(label=X(0))
    dot.node("a",label=X(1))
    dot.edge("a","b",label=X(2))
    dot.subgraph("cluster_c").graph(label=X(3))
    assert str(dot) == (
        'graph {\n'
        '    a [label=<x<sub><font point-size="10">1</font></sub>>]\n'
        '    a -- b [label=<x<sub><font point-size="10">2</font></sub>>]\n'
        '    subgraph cluster_c {\n'
        '        label=<x<sub><font point-size="10">3</font></sub>>\n'
        '    }\n'
        '    label=<x<sub><font point-size="10">0</font></sub>>\n'
        '}\n'
    )


def test_override():
    """
    An overridden __str__ takes precedence over the markup field, and can
    use the base class string representation to build its result.
    """
    class Bold(Markup):
        def __str__(self) -> str:
            return f'<b>{super().__str__()}</b>'

    dot = Dot()
    dot.node("a",label=Bold("Hello"))
    assert str(dot) == (
        'graph {\n'
        '    a [label=<<b>Hello</b>>]\n'
        '}\n'
    )


def test_defaults():
    """
    Markup and generated markup can be used in default attributes.
    """
    class Bold(Markup):
        def __str__(self) -> str:
            return f'<b>{self.markup}</b>'

    for label in [ Markup("<b>Default</b>"), Bold("Default") ]:
        dot = Dot()
        dot.graph_default(label=label)
        dot.node_default(label=label)
        dot.edge_default(label=label)
        dot.edge("a","b")
        assert str(dot) == (
            'graph {\n'
            '    graph [label=<<b>Default</b>>]\n'
            '    node [label=<<b>Default</b>>]\n'
            '    edge [label=<<b>Default</b>>]\n'
            '    a -- b\n'
            '}\n'
        )


def test_roles():
    """
    Markup and generated markup are preserved in labels inherited from
    theme roles.
    """
    class Bold(Markup):
        def __str__(self) -> str:
            return f'<b>{self.markup}</b>'

    for label in [ Markup("<b>Role</b>"), Bold("Role") ]:
        theme = Dot()
        theme.graph_role("test",label=label)
        theme.node_role ("test",label=label)
        theme.edge_role ("test",label=label)
        dot = Dot().use_theme(theme)
        dot.graph(role="test")
        dot.node("a",role="test")
        dot.edge("a","b",role="test")
        assert str(dot) == (
            'graph {\n'
            '    a [label=<<b>Role</b>>]\n'
            '    a -- b [label=<<b>Role</b>>]\n'
            '    label=<<b>Role</b>>\n'
            '}\n'
        )


def test_non_str_initializer():
    """
    The `markup` initializer argument must be a string.
    """
    expect_ex(ValueError, lambda: Markup(None))      # type:ignore
    expect_ex(ValueError, lambda: Markup(b'bytes'))  # type:ignore
    expect_ex(ValueError, lambda: Markup(42))        # type:ignore


def test_eq():
    """
    Markup instances can be compared for equality.  A base Markup instance is
    only equal to other base instances with the same markup text.
    """
    class MyMarkup(Markup):
        def __init__(self, markup):
            super().__init__(markup)

    assert Markup("a") == Markup("a")
    assert Markup("a") != Markup("b")
    assert Markup("a") != MyMarkup("a")
    assert MyMarkup("a") != Markup("a")
    assert MyMarkup("a").markup == Markup("a").markup


def test_markup_property():
    """
    The Markup base has a read-only property 'markup' that has a value only for
    the base class or any subclass that calls Markup's initializer (or allows
    it to run).  If a subclass does not call that initializer, accessing the
    property raises an AttributeError.

    If a Markup subclass does not call Markup.__init__(), str() on the object
    raises an AttributeError unless the subclass overrides __str__ (and does
    not call super().__str__()).
    """

    class InitMarkup(Markup):
        def __init__(self):
            super().__init__("Init")

    class NoInitStrMarkup(Markup):
        def __init__(self):
            pass
        def __str__(self):
            return "NoInitStr"

    class NoInitNoStrMarkup(Markup):
        def __init__(self):
            pass

    base        = Markup("Base")
    init        = InitMarkup()
    noinitstr   = NoInitStrMarkup()
    noinitnostr = NoInitNoStrMarkup()

    assert base.markup == "Base"
    assert init.markup == "Init"

    expect_ex(AttributeError, lambda: noinitstr.markup)
    expect_ex(AttributeError, lambda: noinitnostr.markup)

    assert str(base) == "Base"
    assert str(init) == "Init"
    assert str(noinitstr) == "NoInitStr"

    expect_ex(AttributeError, lambda: str(noinitnostr))


def test_repr():
    """
    Markup has a conventional repr.  It does not produce reprs for subclasses.
    """
    assert repr(Markup("X")) == "Markup(markup='X')"

    class InitMarkup(Markup):
        def __init__(self):
            super().__init__("Cookie")

    assert "Cookie" not in repr(InitMarkup())
