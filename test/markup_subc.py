import re
import typing
from collections.abc import Callable
from dataclasses import dataclass
from re import Pattern
from typing import Any, cast
from pathlib import Path

from gvdot import Dot, Markup, ProcessException
from gvdot.markup import *
from gvdot.markup import Managed
from utility import expect_ex


type ContainerMarkup = (
    Span | Font | Bold | Italic | Underline | Overline |
    Strike | Sub | Sup | Table | TR | TD
)

_container_classes = set(typing.get_args(ContainerMarkup.__value__))
_root_classes      = _container_classes | { Text, Entity, Raw, BR }



#
# _ESCAPE_EXPECT is fragile because it depends on the single quote
# escaping choice -- "&apos;" and "&#39;" are also valid.
#

_ESCAPE_CORPUS = "<>&'\"<>&'\""
_ESCAPE_EXPECT = "&lt;&gt;&amp;&#x27;&quot;&lt;&gt;&amp;&#x27;&quot;"


#
# The test_allowed_structure() renders a Dot object including an Img which will
# refer to _DOT_PNG, if __file__ is available for this module.
#

if '__file__' in globals():
    _DOT_PNG = str(Path(__file__).parent / "dot.png")
else:
    _DOT_PNG = None


#
# One example value for every Graphviz HTML attribute.
#

_attr_exemplars = {
    'align': 'left',
    'balign': 'right',
    'bgcolor': 'yellow:orange',
    'border': 1,
    'cellborder': 1,
    'cellpadding': 4,
    'cellspacing': 2,
    'color': 'red',
    'colspan': 1,
    'columns': '*',
    'face': 'Helvetica',
    'fixedsize': False,
    'gradientangle': 45,
    'height': 20,
    'href': 'https://graphviz.org/',
    'id': 'example',
    'point_size': 12.5,
    'port': 'p',
    'rows': '*',
    'rowspan': 1,
    'scale': False,
    'sides': 'LTRB',
    'src': 'dot.png',
    'style': 'radial',
    'target': '_blank',
    'title': 'Example',
    'tooltip': 'Example',
    'valign': 'top',
    'width': 20,
}

#
# Some elements can't be at the top level of a label.  _Wrapper provides an
# embedding transformation for those elements.  The nil wrapper applies no
# transformation.
#

@dataclass(frozen=True)
class _Wrapper[T:Managed]:
    wrap_fn   : Callable[[T],Managed]
    unwrap_re : Pattern

    def wrap(self, tree:T) -> Managed:
        return self.wrap_fn(tree)

    def unwrap(self, html:str) -> str:
        assert (match := self.unwrap_re.fullmatch(html))
        return match[1]

_nil_wrapper = _Wrapper[Managed](
    wrap_fn   = lambda e: e,
    unwrap_re = re.compile(r"(.*)"),
)

_row_wrapper = _Wrapper[RowContent](
    wrap_fn=lambda e: Table(e),
    unwrap_re=re.compile(r"<table>(.*)</table>"),
)

_cell_wrapper = _Wrapper[CellContent](
    wrap_fn=lambda e: Table(TR(e)),
    unwrap_re=re.compile(r"<table><tr>(.*)</tr></table>"),
)

_img_wrapper = _Wrapper[Img](
    wrap_fn=lambda e: Table(TR(TD(e))),
    unwrap_re=re.compile(r"<table><tr><td>(.*)</td></tr></table>"),
)

#
# Slugs are exemplar contents for each content type.  The nil slug is no
# content.
#

@dataclass(frozen=True)
class _Slug[T:GeneralContent]:
    children_fn : Callable[[],tuple[T,...]]
    html        : str
    is_nil      : bool = False

_nil_slug = _Slug(lambda:(),"",is_nil=True)

_text_slug = _Slug(
    lambda: (Text("X"),Bold("Y"),),
    "X<b>Y</b>")

_table_slug = _Slug(
    lambda: (Table(TR(TD("Z"))),),
    "<table><tr><td>Z</td></tr></table>")

_row_slug = _Slug(
    lambda: (TR(TD("U")),TR(TD("V"))),
    "<tr><td>U</td></tr><tr><td>V</td></tr>")

_cell_slug = _Slug(
    lambda: (TD("U"),TD("V")),
    "<td>U</td><td>V</td>")

_img_slug = _Slug(
    lambda: (Img(src="dot.png"),),
    '<img src="dot.png"/>')

_empty_text_slug = _Slug(
    lambda: ("",Text(""),Span()),
    "")

_empty_text_table_slug = _Slug(
    lambda: ("",Text(""),Span(),Table(),),
    "")

_empty_row_slug = _Slug(
    lambda: (TR(),TR()),
    "")


#
# _Element fields:
#
#    tag       - Element tag (including span but not [text])
#    class_    - Corresponding Markup subclass
#    slugs     - Non-nil, non-empty exemplars for container elements
#    emptyslug - Non-nil, empty exemplar for container elements
#    wrapper   - Non-nil wrapper for elements not allowed at root
#    attrnames - All permitted attributes
#    anyparent - Some legal container of the element
#    solo      - Must be the only content item of a parent
#

@dataclass(frozen=True)
class _Element:
    tag        : str
    class_     : type[Managed]
    slugs      : tuple[_Slug,...] = (_nil_slug,)
    emptyslug  : _Slug = _nil_slug
    wrapper    : _Wrapper = _nil_wrapper
    attrnames  : tuple[str,...] = ()
    anyparent  : type[ContainerMarkup] = Span
    solo       : bool = False

    #
    # Special elements cannot be constructed and added to a tree as others are.
    # This includes Text, Entity, and Raw because their initializers require
    # one fixed string, and HR and VR because they must be placed between rows
    # and cells.
    #

    def is_special(self) -> bool:
        return self.class_ in (Text, Entity, Raw, HR, VR)

_elements:dict[type[Managed],_Element] = {

    Text: _Element(
        '[text]', Text,
    ),

    Entity: _Element(
        '[entity]', Entity,
    ),

    Raw: _Element(
        '[raw]', Raw,
    ),

    Span: _Element(
        'span', Span,
        slugs=(_text_slug,),
        emptyslug=_empty_text_slug,
    ),

    Font: _Element(
        'font', Font,
        slugs=(_text_slug, _table_slug),
        emptyslug=_empty_text_table_slug,
        attrnames=('color', 'face', 'point_size'),
    ),

    Bold: _Element(
        'b', Bold,
        slugs=(_text_slug, _table_slug),
        emptyslug=_empty_text_table_slug,
    ),

    Italic: _Element(
        'i', Italic,
        slugs=(_text_slug, _table_slug),
        emptyslug=_empty_text_table_slug,
    ),

    Underline: _Element(
        'u', Underline,
        slugs=(_text_slug, _table_slug),
        emptyslug=_empty_text_table_slug,
    ),

    Overline: _Element(
        'o', Overline,
        slugs=(_text_slug, _table_slug),
        emptyslug=_empty_text_table_slug,
    ),

    Strike: _Element(
        's', Strike,
        slugs=(_text_slug,),
        emptyslug=_empty_text_slug,
    ),

    Sub: _Element(
        'sub', Sub,
        slugs=(_text_slug,),
        emptyslug=_empty_text_slug,
    ),

    Sup: _Element(
        'sup', Sup,
        slugs=(_text_slug,),
        emptyslug=_empty_text_slug,
    ),

    BR: _Element(
        'br', BR,
        attrnames=('align',),
    ),

    Table: _Element(
        'table', Table,
        slugs=(_row_slug,),
        emptyslug=_empty_row_slug,
        attrnames=(
            'align', 'bgcolor', 'border', 'cellborder', 'cellpadding',
            'cellspacing', 'color', 'columns', 'fixedsize',
            'gradientangle', 'height', 'href', 'id', 'port', 'rows',
            'sides', 'style', 'target', 'title', 'tooltip', 'valign',
            'width',
        ),
        anyparent=TD,
        solo=True,
    ),

    # No empty slug because cells are not elided.
    TR: _Element(
        'tr', TR,
        slugs=(_cell_slug,),
        wrapper=_row_wrapper,
        anyparent=Table,
    ),

    TD: _Element(
        'td', TD,
        slugs=(_text_slug, _table_slug, _img_slug),
        emptyslug=_empty_text_table_slug,
        wrapper=_cell_wrapper,
        attrnames=(
            'align', 'balign', 'bgcolor', 'border', 'cellpadding',
            'cellspacing', 'color', 'colspan', 'fixedsize',
            'gradientangle', 'height', 'href', 'id', 'port',
            'rowspan', 'sides', 'style', 'target', 'title', 'tooltip',
            'valign', 'width',
        ),
        anyparent=TR
    ),

    HR: _Element(
        'hr', HR,
        wrapper=_row_wrapper,
        anyparent=Table,
    ),

    VR: _Element(
        'vr', VR,
        wrapper = _cell_wrapper,
        anyparent=TR,
    ),

    Img: _Element(
        'img', Img,
        wrapper=_img_wrapper,
        attrnames=('scale', 'src'),
        anyparent=TD,
        solo=True,
    ),
}

#
# For adding HR and VR to content.
#

def _hr_bundle() -> tuple[TR,HR,TR]:
    return ( TR(TD("X")), HR(), TR(TD("X")) )

def _vr_bundle() -> tuple[TD,VR,TD]:
    return ( TD("X"), VR(), TD("X") )

#
# Check at least a fragment of text from a RuntimeError.  There are many
# validation rules, and it's easy to construct a test that raises an expected
# RuntimeError for the wrong reason.
#

def _require_err_fn(fragment:str) -> Callable[...,None]:
    def require_err(fn:Callable, moreinfo:Callable|None=None):
        message = str(expect_ex(RuntimeError,fn,moreinfo))
        assert fragment in message, (
            f"Expected RuntimeError message '{message}' "
            f"to contain '{fragment}'")
    return require_err


###########################################################################
#                                 GENERATION
###########################################################################

#
# Raise an AssertionError if the specified actual html does not equal what
# should be generated for the given element, attributes, and content slug.
#

def _expect_html(element:_Element, attrs:dict[str,Any],
                 slug:_Slug, actual_html:str) -> None:

    expect_attrs = "".join(
        f' {name.replace("_","-")}="{
            "true" if value is True else
            "false" if value is False else
            value}"'
        for name, value in attrs.items())

    if slug.is_nil:
        expect_html = f"<{element.tag}{expect_attrs}/>"
    elif element.tag == 'span':
        expect_html = slug.html
    else:
        expect_html  = f"<{element.tag}{expect_attrs}>"
        expect_html += slug.html
        expect_html += f"</{element.tag}>"

    assert actual_html == expect_html,(
        f"Expected {expect_html}, found {actual_html}"
    )


def test_to_html():
    """
    Markup subclasses should have the correct HTML representation.
    """
    #
    # Test special elements.
    #

    assert str(Text("")) == ""
    assert str(Text("X")) == "X"
    assert str(Text("XYZ")) == "XYZ"
    assert str(Text(_ESCAPE_CORPUS)) == _ESCAPE_EXPECT

    assert str(Entity("amp"))    == "&amp;"
    assert str(Entity("#x03B2")) == "&#x03B2;"
    assert str(Entity("#X03B2")) == "&#x03B2;"
    assert str(Entity(0x03B2))   == "&#946;"
    assert str(Entity(False))    == "&#0;"
    assert str(Entity(True))     == "&#1;"

    assert str(Raw("")) == ""
    assert str(Raw("anything <&'\"> at all")) == "anything <&'\"> at all"

    assert (str(Table(*_hr_bundle())) ==
            "<table><tr><td>X</td></tr><hr/><tr><td>X</td></tr></table>")

    assert (str(Table(TR(*_vr_bundle()))) ==
            "<table><tr><td>X</td><vr/><td>X</td></tr></table>")

    def trees(element:_Element, attrs:dict[str,Any], slug:_Slug):
        class_ = element.class_
        yield class_(*slug.children_fn(),**attrs)
        if class_ in _container_classes:
            yield class_(**attrs).add(*slug.children_fn()) #type:ignore
        empty = element.emptyslug
        yield class_(*empty.children_fn(),
                     *slug.children_fn(),
                     *empty.children_fn(),
                     **attrs)
        if class_ in _container_classes:
            yield class_(
                *empty.children_fn(),
                *slug.children_fn(),
                *empty.children_fn(),
                **attrs).add(*empty.children_fn())           #type:ignore
            yield class_(*empty.children_fn(),**attrs).add(  #type:ignore
                *empty.children_fn(),
                *slug.children_fn(),
                *empty.children_fn())


    def per_element_attrs(element:_Element, attrs:dict[str,Any]):
        class_ = element.class_
        wrapper = element.wrapper
        for slug in element.slugs:
            for tree in trees(element,attrs,slug):
                tree = wrapper.wrap(tree)
                html = wrapper.unwrap(str(tree))
                _expect_html(element,attrs,slug,html)

    #
    # Test string conversion with no attributes.
    #

    for element in _elements.values():
        if element.is_special(): continue
        per_element_attrs(element,{})

    #
    # Test string conversion with one attribute (if element has at
    # least one attribute.)
    #

    for element in _elements.values():
        if element.is_special(): continue
        attrnames = element.attrnames
        if not attrnames: continue
        attrs = { attrnames[0]: _attr_exemplars[attrnames[0]] }
        per_element_attrs(element,attrs)

    #
    # Test string conversion with all attributes (if element has at
    # least two attributes.)
    #

    for element in _elements.values():
        if element.is_special(): continue
        attrnames = element.attrnames
        if len(attrnames) < 2: continue
        attrs = { name: _attr_exemplars[name] for name in attrnames }
        per_element_attrs(element,attrs)


def test_implicit_text():
    """
    Text content can be given as Python strings, and those strings should be
    properly escaped if necessary.
    """
    _str_slug = _Slug(
        lambda: ("Plain",_ESCAPE_CORPUS,"Text"),
        f"Plain{_ESCAPE_EXPECT}Text")

    for class_ in _container_classes - {Table,TR}:
        element = _elements[class_]
        wrapper = element.wrapper
        tree = wrapper.wrap(class_(*_str_slug.children_fn())) #type: ignore
        html = wrapper.unwrap(str(tree))
        _expect_html(element,{},_str_slug,html)


def test_escaped_attributes():
    """
    Element attributes should be properly escaped.
    """
    for element in _elements.values():
        attrnames = [ name for name in element.attrnames
                      if type(_attr_exemplars[name]) is str ]
        if not attrnames: continue
        corpus_attrs = { name:_ESCAPE_CORPUS for name in attrnames }
        expect_attrs = { name:_ESCAPE_EXPECT for name in attrnames }
        wrapper = element.wrapper
        class_ = element.class_
        slug = element.slugs[0]
        tree = wrapper.wrap(class_(*slug.children_fn(),
                                   **corpus_attrs)) # type:ignore
        html = wrapper.unwrap(str(tree))
        _expect_html(element,expect_attrs,slug,html)


def test_none_attributes():
    """
    Specifying an attribute as None is the same as not specifying it.
    """

    for element in _elements.values():

        attrs = { name: None for name in element.attrnames }
        if not attrs: continue

        wrapper = element.wrapper
        class_  = element.class_
        slug    = element.slugs[0]

        tree1 = wrapper.wrap(class_(*slug.children_fn()))
        tree2 = wrapper.wrap(class_(*slug.children_fn(),**attrs))

        assert str(tree1) == str(tree2)

    #
    # Test string conversion with all attributes (if element has at
    # least two attributes.)
    #

    for element in _elements.values():
        if element.is_special(): continue
        class_ = element.class_
        attrnames = element.attrnames
        if len(attrnames) < 2: continue
        attrs = { name: _attr_exemplars[name] for name in attrnames }
        wrapper = element.wrapper
        for slug in element.slugs:
            tree = wrapper.wrap(class_(*slug.children_fn(),**attrs))
            html = wrapper.unwrap(str(tree))
            _expect_html(element,attrs,slug,html)


def test_nonprintable_strip():
    """
    Non-printable ASCII characters should be stripped from text.
    """
    for code in range(0,32):
        s = bytes([code]).decode()
        assert str(Text(s  )) == ""
        assert str(Text(s*2)) == ""
        assert str(Span(s  )) == ""
        assert str(Span(s*2)) == ""
        assert str(Text(s   + "A" + s   + "B" + s  )) == "AB"
        assert str(Text(s*2 + "A" + s*2 + "B" + s*2)) == "AB"
        assert str(Span(s   + "A" + s   + "B" + s  )) == "AB"
        assert str(Span(s*2 + "A" + s*2 + "B" + s*2)) == "AB"


def test_empty():
    """
    Void elements, entities, and raw HTML are never empty.  Text is empty iff
    the text content consists of only non-printable characters.  Containers
    except for TD are elided if their content is empty.
    """
    #
    # There is no way to directly test that HR and VR are truly non-empty since
    # they are not allowed unless preceded by non-empty content.  They show up
    # correctly when used or not -- test_to_html() takes care of that.
    #

    def td_str(tree:Managed):
        match = re.fullmatch(r"<table><tr><td>(.*)</td></tr></table>",
                             str(Table(TR(TD(tree)))))
        assert match
        return match[1]

    def require_empty(tree:Managed):
        assert tree.vacuous()
        assert not td_str(tree), repr(tree)
        if tree.__class__ in _root_classes:
            assert not str(tree)

    def require_nonempty(tree:Managed):
        assert not tree.vacuous()
        assert td_str(tree), repr(tree)
        if tree.__class__ in _root_classes:
            assert str(tree)

    require_nonempty(BR())
    require_nonempty(Img())

    assert not HR().vacuous()
    assert not VR().vacuous()

    require_empty(Text(""))
    require_empty(Text("\t\r\n"))

    for class_ in _container_classes - {Table, TR, TD}:

        require_empty(class_())
        require_empty(class_(""))
        require_empty(class_(Text("")))
        require_empty(class_(class_()))

        require_nonempty(class_().add("X"))
        require_nonempty(class_("").add("X"))
        require_nonempty(class_(Text("")).add("X"))
        require_nonempty(class_(class_()).add("X"))

        require_nonempty(class_("X").add())
        require_nonempty(class_("X").add(""))
        require_nonempty(class_("X").add(Text("")))
        require_nonempty(class_("X").add(class_()))

    require_empty(Table())
    require_empty(Table(TR()))
    require_nonempty(Table(TR(TD())))

    #
    # Raw requires a different approach.
    #

    assert not Raw("").vacuous()
    assert str(Bold(Raw("")))   == "<b></b>"
    assert str(Bold(Raw("\t"))) == "<b>\t</b>"
    assert str(Bold(Raw("\r"))) == "<b>\r</b>"
    assert str(Bold(Raw("\n"))) == "<b>\n</b>"


def test_empty_td():
    """
    TD, alone among containers, is allowed to be empty and not elided.
    """
    assert str(Table(TR(TD()))) == '<table><tr><td></td></tr></table>'
    assert not TD().vacuous()

    def table():
        return Table(
            TR(TD("One"),TD()),
            TR(TD(),TD("Two")),
        )

    dot = Dot()
    dot.graph(label=table())
    dot.node(1,label=table())
    dot.edge(1,2,label=table())
    dot.to_svg()


##############################################################################
#                             GRAMMAR COMPLIANCE
##############################################################################

#
# A TreeSpec describes a Markup object tree that includes the path
#
#       {wrap-->|}level1-->{level2-->|}{level3-->}-->slug
#
# where the level alternatives are determined by whether or not that field is
# None.  The slug is included iff the trailing element is a container.  The
# wrapping is included iff field wrap is True.
#
# If siblings is True or 2, any level2 elements will have level1's slug[0] as a
# sibling, and similarly for siblings and level3.
#
# The build_by argument determines how a subtree and its sibling content (if
# any) is added to a parent.  Only values 1 and 2 are sensible without
# siblings; 1 through 6 otherwise.
#
# As a special case, because HR and VR must occur between rows and columns, if
# level<n>, n > 1, is an HR or VR, it is given surrounding TR or TD siblings.
#

type _Builder = Callable[...,Managed]  # Includes the Markup subclasses

def _builder_TAG(builder:_Builder):
    class_ = builder if isinstance(builder,type) else builder().__class__
    return _elements[class_].tag.upper()

def _builder_element(builder:_Builder) -> _Element:
    class_ = builder if isinstance(builder,type) else builder().__class__
    return _elements[class_]

@dataclass(frozen=True)
class _TreeSpec:
    level1    : _Builder
    level2    : _Builder | None = None
    level3    : _Builder | None = None
    siblings  : bool|int = True
    wrap      : bool = False

    def __str__(self) -> str:
        s = ""
        siblings2 = self.siblings == True or self.siblings == 2
        siblings3 = self.siblings == True or self.siblings == 3
        more2 = "+" if siblings2 else ""
        more3 = "+" if siblings3 else ""
        if self.wrap: s += "..."
        if self.level1: s += f"/{_builder_TAG(self.level1)}"
        if self.level2: s += f"/{_builder_TAG(self.level2)}{more2}"
        if self.level3: s += f"/{_builder_TAG(self.level3)}{more3}"
        return s

    def make(self, build_by:int) -> Managed:

        def push(builder:_Builder, tree:Managed|None, siblings:bool):
            if not isinstance(builder,type):
                return builder()
            attrs = { 'src': _DOT_PNG } if builder is Img else {}
            element = _elements[builder]
            if tree is None:
                content = element.slugs[0].children_fn()
                return element.class_(*content,**attrs)
            elif type(tree) is HR:
                content = _hr_bundle()
            elif type(tree) is VR:
                content = _vr_bundle()
            else:
                content = (tree,)
            rest = () if not siblings else element.slugs[0].children_fn()
            cons = cast(Callable,builder) # Make pylance happy about .add()
            match build_by:
                case 1: return cons(*content,*rest,**attrs)
                case 2: return cons(**attrs).add(*content,*rest)
                case 3: return cons(*content,**attrs).add(*rest)
                case 4: return cons(*rest,*content,**attrs)
                case 5: return cons(**attrs).add(*rest,*content)
                case 6: return cons(*rest,**attrs).add(*content)
                case _:
                    raise AssertionError(f"Bad build_by {build_by}")

        level1 = self.level1
        level2 = self.level2
        level3 = self.level3

        assert level1 is not None
        assert level2 is not None or level3 is None

        siblings2 = self.siblings == True or self.siblings == 2
        siblings3 = self.siblings == True or self.siblings == 3

        tree = None
        if level3: tree = push(level3,tree,False)
        if level2: tree = push(level2,tree,siblings3)
        if level1: tree = push(level1,tree,siblings2)
        assert tree
        if self.wrap: tree = _elements[tree.__class__].wrapper.wrap(tree)
        return tree

#
# Require a TreeSpec make() to succeed or fail.  _require_fail() doesn't use
# expect_ex() so we can provide more descriptive assertion failure messages.
#

def _make_describe(spec:_TreeSpec, build_by):
    return f"{spec}[{build_by}]"

def _require_good(spec:_TreeSpec):
    for build_by in range(1, 7 if spec.siblings else 3):
        try:
            str(spec.make(build_by))
        except Exception as ex:
            raise AssertionError(
                f"{str(ex)} for {_make_describe(spec,build_by)}")

def _require_fail(spec:_TreeSpec, fragment:str):
    for build_by in range(1, 7 if spec.siblings else 3):
        try:
            str(spec.make(build_by))
            raise AssertionError(
                f"Unexpected success for {_make_describe(spec,build_by)}")
        except RuntimeError as ex:
            assert re.search(fragment,str(ex))

#
# A _TreeRange iterates over specs defined by a cross product of level
# dimensions.  Dimensions should never be empty but level2 and level3 can
# contain None.
#

@dataclass(frozen=True, kw_only=True)
class _TreeRange:
    level1_dim : tuple[_Builder,...]
    level2_dim : tuple[_Builder|None,...] = (None,)
    level3_dim : tuple[_Builder|None,...] = (None,)
    siblings   : bool|int = True
    wrap       : bool = False

    def __post_init__(self):
        assert self.level1_dim
        assert self.level2_dim
        assert self.level3_dim

    def __iter__(self):
        return (_TreeSpec(level1,level2,level3,self.siblings,self.wrap)
                for level3 in self.level3_dim
                for level2 in self.level2_dim
                for level1 in self.level1_dim)


#
# These trees must be allowed.
#

def test_allowed_structure():
    """
    All tree structures implied by Graphviz HTML grammar productions are valid.
    """
    must_allow_trees = [
        #
        # The *text* part of the label production,
        #
        _TreeRange(
            level1_dim=(Span,Font,Bold,Italic,
                        Underline,Overline,Strike,Sub,Sup),
            level2_dim=(Span,Font,Bold,Italic,
                        Underline,Overline,Strike,Sub,Sup,
                        lambda:Text("X"),lambda:Entity("alpha"),BR),
        ),
        _TreeRange(
            level1_dim=(lambda:Text("X"),lambda:Entity("alpha"),BR),
        ),
        #
        # The *fonttable* part of the label production.  Observe that TD has the
        # widest content range in the grammar.
        #
        _TreeRange(
            level1_dim=(Table,),
        ),
        _TreeRange(
            level1_dim=(Font,Bold,Italic,Underline,Overline,),
            level2_dim=(Table,),
            siblings=False,
        ),
        _TreeRange(
            level1_dim=(Table,),
            level2_dim=(TR,HR),
        ),
        _TreeRange(
            level1_dim=(TR,),
            level2_dim=(TD,VR,),
            wrap=True,
        ),
        _TreeRange(
            level1_dim=(TD,),
            level2_dim=(Table,Img,),
            siblings=False,
            wrap=True,
        ),
        _TreeRange(
            level1_dim=(TD,),
            level2_dim=(Font,Bold,Italic,Underline,Overline,),
            level3_dim=(Table,),
            siblings=False,
            wrap=True,
        ),
        _TreeRange(
            level1_dim=(TD,),
            level2_dim=(Span,Font,Bold,Italic,
                        Underline,Overline,Strike,Sub,Sup,
                        lambda:Text("X"),lambda:Entity("alpha"),BR,),
            siblings=True,
            wrap=True,
        ),
        #
        # All containers allow Raw()
        #
        _TreeRange(
            level1_dim=(Span,Font,Bold,Italic,
                        Underline,Overline,Strike,Sub,Sup),
            level2_dim=(lambda:Raw("&rho;"),)
        ),
        _TreeRange(
            level1_dim=(Table,),
            level2_dim=(lambda:Raw("<tr><td>RawRow</td></tr>"),),
        ),
        _TreeRange(
            level1_dim=(TR,),
            level2_dim=(lambda:Raw("<td>RawCell</td>"),),
            wrap=True,
        ),
        _TreeRange(
            level1_dim=(TD,),
            level2_dim=(lambda:Raw("&rho;"),),
            wrap=True,
        ),
    ]

    #
    # Check all combinations allowed by the rules.
    #

    for tree_range in must_allow_trees:
        for spec in tree_range:
            _require_good(spec)

    #
    # Make sure the allowed structures are accepted by Graphviz.  This verifies
    # the test more than gvdot.markup.
    #

    if _DOT_PNG is None:
        raise RuntimeError("Cannot complete test -- no __file__ defined")

    unique = dict[str,Managed]()
    for tree_range in must_allow_trees:
        for spec in tree_range:
            for build_by in range(1, 7 if spec.siblings else 3):
                tree = spec.make(build_by)
                unique[str(tree)] = tree

    dot = Dot().node_default(shape="plain")
    for i, tree in enumerate(unique.values()):
        assert isinstance(tree,Markup)
        dot.node(i,label=tree)
    dot.to_svg(program="neato")


def test_rules_between():
    """
    Horizontal and vertical rules must be between rows and cells.
    """
    tr = lambda: TR(TD("X"))
    td = lambda: TD("X")

    require_between_err = _require_err_fn("between")
    require_between_err(lambda:str(Table(HR(),tr())))
    require_between_err(lambda:str(Table(tr(),HR())))
    require_between_err(lambda:str(Table(TR(VR(),td()))))
    require_between_err(lambda:str(Table(TR(td(),VR()))))


def test_disallowed_roots():
    """
    Some elements cannot be root elements.
    """
    disallowed_roots = _TreeRange(
        level1_dim=(TR,TD,HR,VR,Img,)
    )
    for spec in disallowed_roots:
        _require_fail(spec, "root")


def test_disallowed_parents():
    """
    Elements are limited to certain parents.
    """
    disallowed_parents = [
        _TreeRange(
            level1_dim=(Table,TR),
            level2_dim=(Span,Font,Bold,Italic,
                        Underline,Overline,Strike,Sub,Sup,
                        lambda:Text("X"),lambda:Entity("alpha"),BR),
            siblings=False,
            wrap=True,
        ),
        _TreeRange(
            level1_dim=(Span,Strike,Sub,Sup,Table,TR,),
            level2_dim=(Table,),
            siblings=False,
            wrap=True,
        ),
        _TreeRange(
            level1_dim=tuple(_container_classes - {Table}),
            level2_dim=(HR,TR,),
            siblings=False,
            wrap=True,
        ),
        _TreeRange(
            level1_dim=tuple(_container_classes - {TR}),
            level2_dim=(VR,TD),
            siblings=False,
            wrap=True,
        ),
        _TreeRange(
            level1_dim=tuple(_container_classes - {TD}),
            level2_dim=(Img,),
            siblings=False,
            wrap=True,
        ),
    ]
    for tree_range in disallowed_parents:
        for spec in tree_range:
            _require_fail(spec, "does not permit child")


def test_font_table():
    """
    If a TABLE is contained by a font-ish element, the font-ish element must be
    the root or contained by a TD.
    """
    disallowed_font_table = _TreeRange(
        level1_dim=(Span,Font,Bold,Italic,
                    Underline,Overline,Strike,Sub,Sup),
        level2_dim=(Font,Bold,Italic,Underline,Overline,),
        level3_dim=(Table,),
        siblings=False,
    )
    for spec in disallowed_font_table:
        _require_fail(spec, "TABLE")


def test_sole_child():
    """
    TABLEs, TABLEs wrapped in certain font-ish elements, and IMGs must be the
    sole child of an otherwise legal container.
    """
    disallowed_siblings = [
        _TreeRange(
            level1_dim=(Font,Bold,Italic,Underline,Overline,),
            level2_dim=(Table,),
            siblings=True,
            wrap=True,
        ),
        _TreeRange(
            level1_dim=(TD,),
            level2_dim=(Font,Bold,Italic,Underline,Overline,),
            level3_dim=(Table,),
            siblings=2,
            wrap=True,
        ),
        _TreeRange(
            level1_dim=(TD,),
            level2_dim=(Img,),
            siblings=True,
            wrap=True,
        ),
    ]
    for tree_range in disallowed_siblings:
        for spec in tree_range:
            _require_fail(spec, "TABLE|IMG")


##############################################################################
#                             MISCELLANEOUS
##############################################################################


def test_equality():
    """
    Markup subclasses can be compared for equality.
    """
    assert Text("hello") == Text("hello")
    assert Text("hello") != Text("world")
    assert Text("hello") != "hello"
    assert Entity("alpha") == Entity("alpha")
    assert Entity("alpha") != Entity("beta")
    assert Entity("alpha") != Text("alpha")
    assert Entity(65) == Entity(65)
    assert Entity(65) != Entity(64)
    assert BR() == BR()
    assert BR() != HR()
    assert BR(align="left") == BR(align="left")
    assert BR(align="left") != BR(align="right")
    assert BR(align="left") != BR()
    assert Bold("hello") == Bold("hello")
    assert Bold("hello") == Bold(Text("hello"))
    assert Bold("hello") != Italic("hello")
    assert Bold("hello") != Bold("world")
    assert Span("a", "b") != Span("b", "a")
    assert Span("a", "b") != Span("a")
    assert Table(TR(TD("hello"))) == Table(TR(TD("hello")))
    assert Table(TR(TD("hello"))) != Table(TR(TD("world")))
    assert BR() != None
    assert BR() != "<br/>"
    assert Raw("fredo") == Raw("fredo")
    assert Raw("fredo") != Raw("alfredo")
    assert Raw("fredo") != Text("fredo")


def test_repr():
    """
    Markup subclasses have reasonable reprs.
    """
    assert repr(Text("")) == "Text<>"
    assert repr(Text("hello")) == "Text<hello>"
    assert repr(Text("<&>")) == "Text<&lt;&amp;&gt;>"
    assert repr(Entity("epsilon")) == "Entity<&epsilon;>"
    assert repr(Entity(64)) == "Entity<&#64;>"
    assert repr(BR()) == "BR<>"
    assert repr(HR()) == "HR<>"
    assert repr(BR(align="left")) == "BR<align='left'>"
    assert repr(Span()) == "Span<>"
    assert repr(Span("a", "b")) == "Span<Text<a>,Text<b>>"
    assert repr(Bold("hello")) == "Bold<Text<hello>>"
    assert repr(Bold(Text("hello"))) == "Bold<Text<hello>>"
    assert repr(Bold("a", "b")) == "Bold<Text<a>Text<b>>"
    assert repr(Font("hello", color="red")) == (
        "Font<color='red';Text<hello>>")
    assert repr(Table(TR(TD("hello")))) == (
        "Table<TR<TD<Text<hello>>>>")
    assert repr(Raw("<&>")) == "Raw<<&>>"


def test_aliases():
    """
    The single letter aliases should be properly defined.
    """
    from gvdot.markup import B, I, U, O, S
    assert B is Bold
    assert I is Italic
    assert U is Underline
    assert O is Overline
    assert S is Strike


def test_add_twice():
    """
    A Markup object can only be added once.
    """
    require_contained_err = _require_err_fn("in a container")

    def add_twice(child_fn:Callable[[],Managed]):

        child = child_fn()
        parent_class = _elements[type(child)].anyparent
        require_contained_err(lambda:parent_class(child,child)) #type:ignore

        container = parent_class()
        child = child_fn()
        container.add(child) #type:ignore
        require_contained_err(lambda:container.add(child)) #type:ignore

    add_twice(lambda: Span("X"))
    add_twice(lambda: Font("X"))
    add_twice(lambda: Bold("X"))
    add_twice(lambda: Italic("X"))
    add_twice(lambda: Underline("X"))
    add_twice(lambda: Overline("X"))
    add_twice(lambda: Strike("X"))
    add_twice(lambda: Sub("X"))
    add_twice(lambda: Sup("X"))
    add_twice(lambda: Text("X"))
    add_twice(lambda: Entity("rarr"))
    add_twice(lambda: BR())
    add_twice(lambda: Table(TR(TD("X"))))
    add_twice(lambda: TR(TD("X")))
    add_twice(lambda: TD("X"))
    add_twice(lambda: Img(src="image.png"))
    add_twice(lambda: Raw("&rho;"))

    hr = HR()
    table = Table()
    table.add(TR(TD("x")))
    table.add(hr)
    table.add(TR(TD("x")))
    require_contained_err(lambda: table.add(hr))

    tr = TR()
    vr = VR()
    tr.add(TD("x"))
    tr.add(vr)
    tr.add(TD("x"))
    require_contained_err(lambda: tr.add(vr))


def test_add_bad_content():
    """
    Only strings and Markup subclasses can be added.  Text() and Raw()
    arguments must be strings.
    """
    expect_ex(ValueError, lambda: Span(1.23))                    #type:ignore
    expect_ex(ValueError, lambda: Span().add(b'not a str'))      #type:ignore
    expect_ex(ValueError, lambda: Table(Markup(
        '<tr><td>ok</td></tr>'))) #type:ignore
    expect_ex(ValueError, lambda: Text(1.23))           #type:ignore
    expect_ex(ValueError, lambda: Text(Text("not ok"))) #type:ignore
    expect_ex(ValueError, lambda: Raw(1.23))            #type:ignore
    expect_ex(ValueError, lambda: Raw(Text("not ok")))  #type:ignore


def test_no_self_loops():
    """
    A Markup object cannot be its own content.
    """
    s = Span("recursive")
    assert "child of itself" in str(
        expect_ex(RuntimeError, lambda: s.add(s)))


def test_closed_container():
    """
    Once a container becomes a child of a parent, its closed to additional
    content.
    """
    require_closed_err = _require_err_fn("closed")

    for class_ in _container_classes:

        element      = _elements[class_]
        parent_class = element.anyparent
        content_fn   = element.slugs[0].children_fn

        child = class_(*content_fn())
        _ = parent_class(child)
        require_closed_err(lambda: child.add(*content_fn()))

        child = class_()
        child.add(*content_fn())
        _ = parent_class(child)
        require_closed_err(lambda: child.add(*content_fn()))


def test_atomicity():
    """
    Adding content to a parent element is atomic with respect to validation
    failures.
    """
    text   = Text("Ok")
    br     = BR()
    italic = Italic("Joe")
    empty  = Span()

    def reset():
        nonlocal text, br, italic, empty
        text   = Text("Ok")
        br     = BR()
        italic = Italic("Joe")
        empty  = Span()

    def bad_penny(extype:type[Exception], item:Callable):

        expect_ex(extype, lambda: Span(empty,text,br,item(),italic))
        assert str(Span(empty,text,br,italic)) == "Ok<br/><i>Joe</i>"
        reset()

        span = Span(empty,text,br,italic)
        expect_ex(extype, lambda: span.add(item()))
        assert str(span) == "Ok<br/><i>Joe</i>"
        reset()

        span = Span(text,br)
        expect_ex(extype, lambda: span.add(empty,italic,item()))
        assert str(span) == "Ok<br/>"
        assert str(Span(empty,italic)) == "<i>Joe</i>"
        reset()

        span = Span(empty,text,br)
        expect_ex(extype, lambda: span.add(italic,item()))
        assert str(span) == "Ok<br/>"
        expect_ex(RuntimeError, lambda: Span(empty))
        expect_ex(RuntimeError, lambda: Span(text))
        expect_ex(RuntimeError, lambda: Span(br))
        reset()

        span = Span()
        expect_ex(extype, lambda: span.add(item()))
        assert str(span) == ""
        reset()


    bad_penny(RuntimeError,lambda: HR())
    bad_penny(ValueError,lambda: 1.23)


def test_bad_entity():
    """
    Lexically invalid and out of range entities raise ValueError.
    """
    expect_ex(ValueError, lambda:Entity("&epsilon;"))
    expect_ex(ValueError, lambda:Entity("&#0040;"))
    expect_ex(ValueError, lambda:Entity("ep silon"))
    expect_ex(ValueError, lambda:Entity("epsilon!"))
    expect_ex(ValueError, lambda:Entity(-1))
    expect_ex(ValueError, lambda:Entity(0x110000))
    expect_ex(ValueError, lambda:Entity("#x110000"))
    expect_ex(ValueError, lambda:Entity(64.0))  #type:ignore


def test_bad_raw():
    """
    Incorrect raw HTML should cause Graphviz programs to exit with non-zero
    status.
    """

    def require_bad(dot):
        expect_ex(ProcessException,lambda: dot.to_svg(),
                  lambda: str(dot))

    #
    # Try bad HTML for all label attribute values.
    #

    def not_legal():
        return Bold(Raw("x < y"))

    require_bad(Dot().graph(label=not_legal()))
    require_bad(Dot().node(1,label=not_legal()))
    require_bad(Dot().node(1,xlabel=not_legal()))
    require_bad(Dot().edge(1,2,label=not_legal()))
    require_bad(Dot().edge(1,2,xlabel=not_legal()))
    require_bad(Dot().edge(1,2,headlabel=not_legal()))
    require_bad(Dot().edge(1,2,taillabel=not_legal()))

    #
    # Try other forms of illegal HTML.
    #

    require_bad(Dot().graph(label=Italic(Raw(
        "<font point-size=10>Small"))))

    require_bad(Dot().graph(label=Table(TR(
        TD("First"),Raw("<td>Second<vr/></td>")))))

    require_bad(Dot().graph(label=Table(TR(
        Raw(""),VR(),TD("Second")))))

    require_bad(Dot().graph(label=Span(
        "The ",Raw('<img src="dot.png">')," language")))


def test_abc_intantiate():
    """
    Instantiating the base classes directly should fail.
    """
    from gvdot.markup import Managed, Container, ContainerElement, VoidElement
    expect_ex(TypeError, lambda: Managed())           # type:ignore
    expect_ex(TypeError, lambda: Container())         # type:ignore
    expect_ex(TypeError, lambda: ContainerElement())  # type:ignore
    expect_ex(TypeError, lambda: VoidElement())      # type:ignore


def test_subclassing():
    """
    Applications should be able to subclass Markup subclasses.
    """
    class AppText(Text): pass
    class AppEntity(Entity): pass
    class AppSpan(Span): pass
    class AppRaw(Raw): pass
    class AppFont(Font): pass
    class AppBold(Bold): pass
    class AppItalic(Italic): pass
    class AppUnderline(Underline): pass
    class AppOverline(Overline): pass
    class AppStrike(Strike): pass
    class AppSub(Sub): pass
    class AppSup(Sup): pass
    class AppBR(BR): pass
    class AppTable(Table): pass
    class AppTR(TR): pass
    class AppTD(TD): pass
    class AppHR(HR): pass
    class AppVR(VR): pass
    class AppImg(Img): pass

    tree = AppTable(
        AppTR(
            AppTD(AppSpan(
                AppText("A < B"), AppEntity("amp"),
                AppRaw("&nbsp;"),
                AppFont(AppBold("bold"), face="Helvetica"),
                AppItalic("italic"), AppUnderline("underline"),
                AppOverline("overline"), AppStrike("strike"),
                AppSub("sub"), AppSup("sup"), AppBR(),
            )),
            AppVR(),
            AppTD(AppImg(src="dot.png")),
        ),
        AppHR(),
        AppTR(AppTD("end")),
    )
    assert str(tree) == (
        '<table><tr><td>A &lt; B&amp;&nbsp;'
        '<font face="Helvetica"><b>bold</b></font>'
        '<i>italic</i><u>underline</u><o>overline</o>'
        '<s>strike</s><sub>sub</sub><sup>sup</sup><br/>'
        '</td><vr/><td><img src="dot.png"/></td></tr>'
        '<hr/><tr><td>end</td></tr></table>'
    )

    expect_ex(RuntimeError, lambda: AppSpan(AppTD()))  # type:ignore

    expect_ex(RuntimeError, lambda: AppTable(AppHR()))

    expect_ex(RuntimeError, lambda: AppTable(
         AppTR(AppTD()), AppHR(), AppHR()))

    expect_ex(RuntimeError, lambda: AppBold(
        AppTable(AppTR(AppTD()), AppHR())))  #type:ignore

    expect_ex(RuntimeError, lambda: AppTR(AppVR()))

    expect_ex(RuntimeError, lambda: AppTR(
        AppTD(), AppVR(), AppVR()))

    expect_ex(RuntimeError, lambda: AppTable(
        AppTR(AppTD(), AppVR())))

    expect_ex(RuntimeError, lambda: AppSpan(
        AppTable(AppTR(AppTD())), AppText("x"))) #type:ignore

    expect_ex(RuntimeError, lambda: AppTD(AppImg(), AppText("x")))

    expect_ex(RuntimeError, lambda: AppSpan(
        AppBold(AppTable(AppTR(AppTD())))))

    expect_ex(RuntimeError, lambda: AppSpan(
        AppText("x"), AppTable(AppTR(AppTD())))) #type:ignore

    expect_ex(RuntimeError, lambda: AppTD(
        AppText("x"), AppBold(AppTable(AppTR(AppTD())))))

    expect_ex(RuntimeError, lambda: AppTD(AppText("x"), AppImg()))

    expect_ex(RuntimeError, lambda: str(AppTR(AppTD())))

    expect_ex(RuntimeError, lambda: str(
        AppTable(AppTR(AppTD()), AppHR())))


def test_with_entities():
    """
    Function with_entities() should preserve HTML entities while escaping
    surrounding plain text.  The text given to with_entities() must be a str.
    """
    for text, expected in (
        ("", ""),
        (_ESCAPE_CORPUS, _ESCAPE_EXPECT),
        ("&alpha &; &#;", "&amp;alpha &amp;; &amp;#;"),
        ("&alpha;", "&alpha;"),
        ("&alpha;&beta;", "&alpha;&beta;"),
        ("&#945;&#x3B2;", "&#945;&#x3B2;"),
        ("&alpha; < &beta;", "&alpha; &lt; &beta;"),
        ("< &amp; >", "&lt; &amp; &gt;"),
        ("&amp;lt;", "&amp;lt;"),
    ):
        assert str(with_entities(text)) == expected

    assert str(Bold(with_entities("&alpha; < &beta;"))) == (
        "<b>&alpha; &lt; &beta;</b>"
    )

    expect_ex(ValueError, lambda: with_entities(1.23))            #type:ignore
    expect_ex(ValueError, lambda: with_entities(Entity("alpha"))) #type:ignore
