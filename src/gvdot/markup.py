from __future__ import annotations
import re
import html
from abc import ABC, abstractmethod
from typing import Literal, NoReturn, Self, Any
from ._core import Markup

__all__ = (
    'GeneralContent', 'TextContent', 'TextOrTableContent', 'RowContent',
    'CellContent', 'Align', 'TDAlign', 'VAlign', 'ImageScale', 'Text',
    'Entity', 'Span', 'Raw', 'Font', 'Bold', 'Italic', 'Underline', 'Overline',
    'Strike', 'Sub', 'Sup', 'BR', 'Table', 'TR', 'TD', 'HR', 'VR', 'Img',
    'B', 'I', 'U', 'O', 'S',
    'with_entities',
)

#
# All allowed child tags by parent tag plus roots based on the Graphviz HTML
# grammar, augmented with the span pseudo-element.  Actual initialization is
# deferred to the end after the classes are defined.
#

_text_classes:tuple[type,...]

_ALLOWED_CHILDREN:dict[type,set[type]]

_ALLOWED_ROOTS:set[type]

#
# Raise a RuntimeError describing a constraint violation.
#

def _bad(message:str, **kwargs:Managed) -> NoReturn:
    tags = { name: managed._tag.upper()
             for name, managed in kwargs.items() }
    raise RuntimeError(message.format(message,**tags))


class Managed(ABC):
    """
    An ancestor of every Markup subclass defined in ``gvdot.markup``.  Behind
    the scenes, :class:`Managed` organizes the Markup object tree and enforces
    Graphviz HTML grammar constraints.

    :class:`Managed` checks Graphviz HTML grammar constraints as children are
    added to the Markup object tree.  It performs final validation of the root
    when the tree is converted to a string, including when gvdot accepts the
    tree as a label attribute value.
    """
    __slots__ = ("_tag_class", "_parent", "_attributes", "_children",
                 "_is_container", "_have_table", "_have_image")

    _tag          : str
    _tag_class    : type
    _parent       : Managed|None
    _attributes   : dict[str,str]
    _children     : list[Managed]
    _is_container : bool
    _have_table   : bool
    _have_image   : bool

    @abstractmethod
    def _concrete_markup(self) -> Literal[True]: ... # pragma: no cover

    def _managed_init(self, tag_class:type, attributes:dict[str,Any],
                      is_container:bool):
        self._tag_class = tag_class
        self._parent = None
        self._attributes = {
            name.replace('_','-'):
                "true" if value is True else
                "false" if value is False else
                html.escape(str(value))
            for name, value in attributes.items()
            if value is not None
        }
        self._children = []
        self._is_container = is_container
        self._have_table = False
        self._have_image = False

    #
    # _add_content() enforces all content hierarchy rules implied by the
    # grammar except for allowed roots and final HR/VR sibling checks for a
    # root table.
    #

    def _add_content_inner(self, content:tuple[Any,...],
                           ignored:list[Managed]) -> None:

        children         = self._children
        self_class       = self._tag_class
        have_table       = self._have_table
        have_image       = self._have_image
        allowed_children = _ALLOWED_CHILDREN[self_class]

        for child in content:
            #
            # String content is automatically wrapped in a Text object.
            #
            match child:
                case Managed():
                    pass
                case str():
                    child = Text(child)
                case _:
                    raise ValueError("Content type {} not allowed".format(
                        type(child)))
            #
            # Children may only be in one container.
            #
            child_class = child._tag_class
            if child._parent is not None:
                _bad("{child} element is already in a container",child=child)
            #
            # A container cannot be a child of itself.
            #
            if child is self:
                _bad("Attempting to make {self} element child of itself.",
                     self=self)
            #
            # The child must have an allowed tag for the parent.
            #
            if child_class not in allowed_children:
                _bad("{self} element does not permit child {child}",
                     self=self, child=child)
            #
            # If a child is empty, it is ignored.
            #
            if child.vacuous():
                ignored.append(child)
                child._parent = self
                continue
            #
            # HR and VR elements must be between rows and cells.
            #
            if (child_class is HR and
                (not children or children[-1]._tag_class is HR) or
                child_class is Table and child._children[-1]._tag_class is HR
            ):
                _bad("Element HR must be between rows")
            if (child_class is VR and
                (not children or children[-1]._tag_class is VR) or
                child_class is TR and child._children[-1]._tag_class is VR
            ):
                _bad("Element VR must be between cells")
            #
            # If there is an existing TABLE child, no child can be added.
            #
            if have_table:
                _bad("Cannot add element {child} to "
                     "{self} which has a TABLE child", child=child, self=self)
            #
            # If there is an existing IMG child, no child can be added.
            #
            if have_image:
                _bad("Cannot add element {child} to "
                     "{self} which has an IMG child", child=child, self=self)
            #
            # If child is a non-TD container with a TABLE, adding it to
            # anything other than a TD is not allowed.
            #
            if (child._have_table and child_class is not TD
                and self_class is not TD):
                _bad("{self} element containing {child}"
                    " with TABLE not permitted", self=self, child=child)
            #
            # If child is a TABLE or is a non-TD container with a TABLE, then
            # self must have no other children.
            #
            table_ish = (child_class is Table or
                         child._have_table and child_class is not TD)
            if table_ish:
                if children:
                    _bad("TABLE not permitted in {self} with other content",
                         self=self)
                have_table = True
            #
            # If child is an IMG, then the container must have no other
            # children.
            #
            if child_class is Img:
                if children:
                    _bad("IMG not permitted in {self} with other content",
                         self=self)
                have_image = True
            #
            # Move to the next child.
            #
            children.append(child)
            child._parent = self
        #
        # NOTE: There is no need for the outer method to rollback these
        # assignments since no non-catastrophic exception can happen below
        # here.
        #
        self._have_table = have_table
        self._have_image = have_image

    def _add_content(self, content:tuple[Any,...]) -> None:

        assert self._is_container

        if self._parent is not None:
            _bad("Element {self} a child of {gp} is closed",
                 self=self, gp=self._parent)

        #
        # Rollback on exception, making _add_content() atomic.
        #

        ignored  = list[Managed]()
        children = self._children
        mark     = len(children)

        try:
            self._add_content_inner(content, ignored)
        except Exception:
            for i in range(mark,len(children)):
                children[i]._parent = None
            del children[mark:]
            for child in ignored:
                child._parent = None
            raise

    def __repr__(self) -> str:
        attrtext = ",".join(f"{name}={value!r}" for name, value
                            in self._attributes.items())
        bodytext = "".join(map(repr,self._children))
        return (f"{self.__class__.__name__}<" + attrtext +
                (';' if attrtext and bodytext else '') +
                bodytext + '>')

    def _inner_str(self) -> str:
        result = f"<{self._tag}"
        result += "".join(f' {name}="{value}"' for name, value in
                        self._attributes.items())
        if self._is_container:
            result += ">"
            result += "".join(child._inner_str() for child in self._children)
            result += f"</{self._tag}>"
            return result
        else:
            result += "/>"
            return result

    def __eq__(self, other):
        if not isinstance(other,Managed):
            return NotImplemented
        return (self._tag == other._tag and
                self._attributes == other._attributes and
                self._is_container == other._is_container and
                self._children == other._children)

    def __str__(self) -> str:

        self_class = self._tag_class
        if self_class not in _ALLOWED_ROOTS:
            _bad("{self} element cannot be a root",self=self)

        if self.vacuous():
            return ""

        if self_class is Table and self._children[-1]._tag_class is HR:
            _bad("Element HR must be between rows")

        #
        # Note the if condition below will never be true because TR is not an
        # allowed root.  We leave the code here, though, in case these validity
        # checks are ever rearranged.
        #

        if self_class is TR and self._children[-1]._tag_class is VR:
            _bad("Element VR must be between cells")

        return self._inner_str()

    @abstractmethod
    def vacuous(self) -> bool:
        """
        Return True if and only if the managed object is empty and will be
        elided from Graphviz HTML strings.  If non-empty content is added to a
        vacuous :class:`Container`, it ceases being vacuous.
        """


class Container[T:GeneralContent](ABC):
    """
    A base class for Markup subclasses that have content.  In addition to
    method :meth:`~Container.add`, Markup subclasses of :class:`Container` have
    an initializer including the same ``*content:T`` parameter as
    :meth:`~Container.add` for some content type ``T``.

    Each content element in the initializer becomes a child of the initialized
    object.  Each content element subsequently provided as an argument to
    :meth:`~Container.add` is appended to the container's children.  Once a
    container is itself added to a parent, applications can no longer add to
    it.

    Content objects provided to a Container's initializer or
    :meth:`~Container.add` must be either a Managed object or a ``str``.
    Containers convert ``str`` to :class:`Text` objects automatically.

    The initializers of Markup subclasses of :class:`Container` raise the same
    content-related :class:`ValueError` and :class:`RuntimeError` exceptions
    that :meth:`~Container.add` does, and do not separately document these
    exceptions.
    """
    @abstractmethod
    def add(self, *content:T) -> Self:
        """
        Append additional markup content.

        :param content: The markup content.

        :raises ValueError: A content element type is unsupported.

        :raises RuntimeError: Adding a content element would violate a Graphviz
            HTML constraint, or the container has a parent and no further
            content may be added.
        """
        ...


class ContainerElement[T:GeneralContent](Managed,Container[T],ABC):
    """
    A base class for Markup subclasses corresponding to Graphviz HTML elements
    having content.  For example, :class:`Font` and :class:`TD` are
    :class:`ContainerElement` subclasses corresponding to elements ``FONT`` and
    ``TD``.
    """
    @abstractmethod
    def _concrete_markup(self) -> Literal[True]: ...

    def _ce_init(self, tag_class:type, /, content:tuple[T,...],
                 attributes:dict[str,Any]):
        self._managed_init(tag_class,attributes,True)
        self._add_content(content)

    def add(self, *content:T) -> Self:
        self._add_content(content)
        return self

    def vacuous(self) -> bool:
        return len(self._children) == 0


class VoidElement(Managed,ABC):
    """
    A base class for Markup subclasses corresponding to Graphviz HTML elements
    that cannot have content.  For example, :class:`BR` and :class:`Img` are
    :class:`VoidElement` subclasses corresponding to elements ``BR`` and
    ``IMG`` respectively.
    """
    @abstractmethod
    def _concrete_markup(self) -> Literal[True]: ...

    def _ve_init(self, tag_class:type, /, **attributes):
        self._managed_init(tag_class,attributes,False)

    def vacuous(self) -> bool:
        return False


type GeneralContent = Managed | str

type TextContent = (
    str | Text | Entity | BR | Span | Font | Italic | Bold |
    Underline | Overline | Sup | Sub | Strike | Raw)

type TextOrTableContent = (
    str | Text | Entity | BR | Span | Font | Italic | Bold |
    Underline | Overline | Sup | Sub | Strike | Table | Raw)

type RowContent = TR | HR | Raw

type CellContent = TD | VR | Raw


type Align = Literal['left', 'center', 'right']

type TDAlign = Align | Literal['text']

type VAlign = Literal['middle', 'bottom', 'top']

type ImageScale = bool | Literal['width', 'height', 'both']


_NONPRINTING_RE = re.compile(r'[\x00-\x1f]')

class Text(Managed, Markup):
    """
    Plain text in Graphviz HTML. :class:`Text` has no attributes and no markup
    content. :class:`Text` instances correspond to `string` in the Graphviz
    HTML grammar.

    :param text: The plain text string.  :class:`Text` objects escape ``text``,
        so a node label ``Text("<hr/>")`` will be rendered as a less-than sign,
        the letters `h` and `r`, a slash, then a greater-than sign.

    :raise ValueError: The given text is not a ``str``.

    The Graphviz documentation states that `string` is a collection of
    printable characters including spaces, and non-printing characters such as
    tabs or newlines are ignored.  What it actually considers to be
    non-printing are characters with ASCII values less than 32.
    Correspondingly, :class:`Text` strips those same characters from ``text``.

    A :class:`Text` object is empty if and only if ``text`` is empty after
    non-printable characters are removed.

    Applications do not commonly instantiate :class:`Text` because
    :class:`Container` classes create :class:`Text` objects for each content
    Python string.  The Dot object created by

    .. code-block:: python

        dot = Dot()
        dot.node(1,label=Text("First"))   # A directly created Text object
        dot.node(2,label=Bold("Second"))  # Text object created by Bold()
        dot.node(3,label="Third")         # Not a markup label

    has the DOT language representation

    .. code-block:: graphviz

        graph {
            1 [label=<First>]
            2 [label=<<b>Second</b>>]
            3 [label="Third"]
        }
    """
    __slots__ = "_text"

    _text : str

    _tag = "[text]"

    def _concrete_markup(self): return True # pragma: no cover

    def __init__(self,text:str):
        if not isinstance(text,str):
            raise ValueError("Given text is not a str")
        Managed._managed_init(self,Text,{},False)
        self._text = html.escape(_NONPRINTING_RE.sub('',text))

    def __repr__(self) -> str:
        return f"Text<{self._text}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other,Text):
            return NotImplemented
        return self._text == other._text

    def _inner_str(self) -> str:
        return self._text

    def __str__(self) -> str:
        return self._text

    def vacuous(self) -> bool:
        return len(self._text) == 0


_ENTITY_NAME_RE = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#(?:x|X)[0-9A-Fa-f]+)")

def _entity_range_check(entity:int):
    if entity < 0 or entity > 0x10FFFF:
        raise ValueError(f"Numeric entity value {entity} is out of range.")

class Entity(Managed, Markup):
    """
    A Graphviz HTML entity. :class:`Entity` has no attributes and no markup
    content. Like :class:`Text`, :class:`Entity` instances correspond to
    `string` in the Graphviz HTML grammar --- only limited to "&\\ *name*;" or
    "&#\\ *number*;" forms, where *name* is an entity name and *number* is a
    Unicode character number.

    :param entity: An entity name ``str`` or Unicode character number ``int``.
        A name should not include the leading ampersand or trailing semicolon,
        but can describe a numeric entity such as "#x03B2".

    :raises ValueError: The entity name is not lexically legal or the entity
        number is outside the range [0,0x10FFFF].

    Class :class:`Entity` is necessary because :class:`Text` escapes its
    content, meaning embedded HTML entities appear as ordinary text beginning
    with an ampersand.  For example, the Dot object created by

    .. code-block:: python

        dot = Dot(directed=True).graph(rankdir="LR")
        dot.node(1,label=Span("Some ",Entity("Phi")))
        dot.node(2,label=Span("then an ",Entity("Omega")))
        dot.node(3,label=Text("but no &Sigma;"))
        dot.edge(1,2).edge(2,3)
        dot.graph(label=Entity(0x1F600))

    has the DOT language representation

    .. code-block:: graphviz

        digraph {
            rankdir=LR
            1 [label=<Some &Phi;>]
            2 [label=<then an &Omega;>]
            3 [label=<but no &amp;Sigma;>]
            1 -> 2
            2 -> 3
            label=<&#128512;>
        }
    """
    __slots__ = "_text"

    _text : str

    _tag = "[entity]"

    def _concrete_markup(self): return True # pragma: no cover

    def __init__(self,entity:str|int):

        match entity:
            case str() if _ENTITY_NAME_RE.fullmatch(entity):
                if entity[0] == '#':
                    if entity[1] in ('x','X'):
                        _entity_range_check(int(entity[2:],16))
                        entity = '#x' + entity[2:]
                    else:
                        _entity_range_check(int(entity[1:],10))
                entity = f"&{entity};"
            case int():
                entity = int(entity) # Required by bool subtype of int
                _entity_range_check(entity)
                entity = f"&#{entity};"
            case _:
                raise ValueError(f"Invalid entity {entity!r}")
        Managed._managed_init(self,Entity,{},False)
        self._text = entity

    def __repr__(self) -> str:
        return f"Entity<{self._text}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other,Entity):
            return NotImplemented
        return self._text == other._text

    def _inner_str(self) -> str:
        return self._text

    def __str__(self) -> str:
        return self._text

    def vacuous(self) -> bool:
        return False


class Span(Managed,Container[TextContent],Markup):
    """
    A text markup content container.  Similar to real HTML, :class:`Span` is a
    way to group markup.  However, there is no ``SPAN`` element in Graphviz
    HTML, so :class:`Span` is not a :class:`ContainerElement`.

    :param content: The markup content.

    :class:`Span` can be especially useful as a Markup object tree root.

    Example use:

        .. code-block:: python

            dot = Dot()
            dot.graph(label=Span("Hello",BR(),"World!"))
            dot.show_source()

    which displays the following in a notebook:

        .. code-block:: graphviz

            graph {
                label=<Hello<br/>World!>
            }
    """

    _tag = "span"

    def _concrete_markup(self): return True # pragma: no cover

    def __init__(self, *content:TextContent):
        self._managed_init(Span,{},True)
        self._add_content(content)

    def add(self, *content:TextContent) -> Self:
        self._add_content(content)
        return self

    def __repr__(self) -> str:
        return f"Span<{",".join(map(repr,self._children))}>"

    def _inner_str(self) -> str:
        return "".join(child._inner_str() for child in self._children)

    def __str__(self) -> str:
        return self._inner_str()

    def vacuous(self) -> bool:
        return len(self._children) == 0


class Raw(Managed, Markup):
    """
    Graphviz HTML text which is not validated or escaped by ``gvdot.markup`` in
    any way.  :class:`Raw` has no attributes and no markup content.
    :class:`Raw` objects are allowed content for every container Markup
    subclass, and ``gvdot.markup`` assumes the raw HTML is non-empty content
    appropriate for the context in which it appears.

    :param html: Graphviz HTML text.  This text will appear in a Markup object
        tree's string representation as-is.

    :raise ValueError: The given html is not a ``str``.

    .. code-block:: python

        dot = Dot()
        dot.node(1,label=Table(Raw(
            "<tr><td>Raw</td></tr>"
        )))
        dot.node(2,label=Table(
            TR(TD("Cooked"))
        ))
        dot.edge(1,2)

    has the DOT language representation

    .. code-block:: graphviz

        graph {
            1 [label=<<table><tr><td>Raw</td></tr></table>>]
            2 [label=<<table><tr><td>Cooked</td></tr></table>>]
            1 -- 2
        }

    Applications using :class:`Raw` are responsible for escaping and conforming
    to the Graphviz HTML grammar.  The following has several :class:`Raw` use
    mistakes:

    .. code-block:: python

        dot = Dot().graph(label=Span(
            "Outcomes when ",
            Raw("&alpha; < &beta;")
        ))
        dot.node(1,label=Table(
            Raw("<td>Distillation<hr></td>")
        ))
        dot.show()

    The less-than sign in the graph label must be escaped.  Element ``TD`` is
    not an allowed child of ``TABLE``.  ``HR`` is not allowed content of a
    cell.  Because ``HR`` is a void element, it should be written as ``<hr/>``.
    When the code above is run in a notebook, the result is

    .. code-block:: console

        The program dot exited with status 1:

            Error: syntax error in line 1
            ... <table><td> ...
            in label of node 1
    """
    __slots__ = "_text"

    _text : str

    _tag = "[raw]"

    def _concrete_markup(self): return True # pragma: no cover

    def __init__(self,html:str):
        if not isinstance(html,str):
            raise ValueError("Given html is not a str")
        Managed._managed_init(self,Raw,{},False)
        self._text = html

    def __repr__(self) -> str:
        return f"Raw<{self._text}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other,Raw):
            return NotImplemented
        return self._text == other._text

    def _inner_str(self) -> str:
        return self._text

    def __str__(self) -> str:
        return self._text

    def vacuous(self) -> bool:
        return False


class Font(ContainerElement[TextOrTableContent],Markup):
    _tag = "font"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:TextOrTableContent,
                 color:str|None=None,
                 face:str|None=None,
                 point_size:float|None=None):
        self._ce_init(Font, content, {"color": color, "face": face,
                         "point_size": point_size})


class Bold(ContainerElement[TextOrTableContent],Markup):
    _tag = "b"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, *content:TextOrTableContent):
        self._ce_init(Bold, content, {})


class Italic(ContainerElement[TextOrTableContent],Markup):
    _tag = "i"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:TextOrTableContent):
        self._ce_init(Italic, content, {})


class Underline(ContainerElement[TextOrTableContent],Markup):
    _tag = "u"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:TextOrTableContent):
        self._ce_init(Underline, content, {})


class Overline(ContainerElement[TextOrTableContent],Markup):
    _tag = "o"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:TextOrTableContent):
        self._ce_init(Overline, content, {})


class Strike(ContainerElement[TextContent],Markup):
    _tag = "s"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:TextContent):
        self._ce_init(Strike, content, {})


class Sub(ContainerElement[TextContent],Markup):
    _tag = "sub"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:TextContent):
        self._ce_init(Sub, content, {})


class Sup(ContainerElement[TextContent],Markup):
    _tag = "sup"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:TextContent):
        self._ce_init(Sup, content, {})


class BR(VoidElement,Markup):
    _tag = "br"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, *,
                 align:Align|None=None):
        self._ve_init(BR, align=align)


class Table(ContainerElement[RowContent],Markup):
    _tag = "table"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:RowContent,
                 align:Align|None=None,
                 bgcolor:str|None=None,
                 border:int|None=None,
                 cellborder:int|None=None,
                 cellpadding:int|None=None,
                 cellspacing:int|None=None,
                 color:str|None=None,
                 columns:Literal['*']|None=None,
                 fixedsize:bool|None=None,
                 gradientangle:int|None=None,
                 height:int|None=None,
                 href:str|None=None,
                 id:str|None=None,
                 port:str|None=None,
                 rows:Literal['*']|None=None,
                 sides:str|None=None,
                 style:str|None=None,
                 target:str|None=None,
                 title:str|None=None,
                 tooltip:str|None=None,
                 valign:VAlign|None=None,
                 width:int|None=None):
        self._ce_init(Table, content, {
            "align": align, "bgcolor": bgcolor, "border": border,
            "cellborder": cellborder, "cellpadding": cellpadding,
            "cellspacing": cellspacing, "color": color, "columns": columns,
            "fixedsize": fixedsize, "gradientangle": gradientangle,
            "height": height, "href": href, "id": id, "port": port,
            "rows": rows, "sides": sides, "style": style, "target": target,
            "title": title, "tooltip": tooltip, "valign": valign,
            "width": width})


class TR(ContainerElement[CellContent],Markup):
    _tag = "tr"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:CellContent):
        self._ce_init(TR, content, {})


class TD(ContainerElement[GeneralContent],Markup):
    _tag = "td"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, /, *content:GeneralContent,
                 align:TDAlign|None=None,
                 balign:Align|None=None,
                 bgcolor:str|None=None,
                 border:int|None=None,
                 cellpadding:int|None=None,
                 cellspacing:int|None=None,
                 color:str|None=None,
                 colspan:int|None=None,
                 fixedsize:bool|None=None,
                 gradientangle:int|None=None,
                 height:int|None=None,
                 href:str|None=None,
                 id:str|None=None,
                 port:str|None=None,
                 rowspan:int|None=None,
                 sides:str|None=None,
                 style:str|None=None,
                 target:str|None=None,
                 title:str|None=None,
                 tooltip:str|None=None,
                 valign:VAlign|None=None,
                 width:int|None=None):
        self._ce_init(TD, content, {
            "align": align, "balign": balign, "bgcolor": bgcolor,
            "border": border, "cellpadding": cellpadding,
            "cellspacing": cellspacing, "color": color, "colspan": colspan,
            "fixedsize": fixedsize, "gradientangle": gradientangle,
            "height": height, "href": href, "id": id, "port": port,
            "rowspan": rowspan, "sides": sides, "style": style,
            "target": target, "title": title, "tooltip": tooltip,
            "valign": valign, "width": width})

    def vacuous(self) -> bool:
        return False


class HR(VoidElement,Markup):
    _tag = "hr"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self):
        self._ve_init(HR)


class VR(VoidElement,Markup):
    _tag = "vr"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self):
        self._ve_init(VR)


class Img(VoidElement,Markup):
    _tag = "img"
    def _concrete_markup(self): return True # pragma: no cover
    def __init__(self, *,
                 scale:ImageScale|None=None,
                 src:str|None=None):
        self._ve_init(Img, scale=scale, src=src)

#
# Aliases
#

B = Bold
I = Italic
U = Underline
O = Overline
S = Strike

#
# These need to be after the classes are defined.
#

_text_classes = (Text, Entity, Span, BR, Font, Italic, Bold,
                 Underline, Overline, Sub, Sup, Strike)

_ALLOWED_CHILDREN = {
    Span     : set((*_text_classes,Raw,)),
    Font     : set((*_text_classes,Table,Raw,)),
    Italic   : set((*_text_classes,Table,Raw,)),
    Bold     : set((*_text_classes,Table,Raw,)),
    Underline: set((*_text_classes,Table,Raw,)),
    Overline : set((*_text_classes,Table,Raw,)),
    Sub      : set((*_text_classes,Raw,)),
    Sup      : set((*_text_classes,Raw,)),
    Strike   : set((*_text_classes,Raw,)),
    Table    : set((TR,HR,Raw)),
    TR       : set((TD,VR,Raw)),
    TD       : set((*_text_classes,Table,Img,Raw))
}

_ALLOWED_ROOTS = set((*_text_classes, Table, Raw))


_ENTITY_RE = re.compile(f"&({_ENTITY_NAME_RE.pattern});")

def with_entities(text:str) -> Text | Span:
    """
    Return a Markup subclass instance for text that may contain HTML entities.

    :param text: A string that is plain text except that it may contain HTML
        entities.

    :return: A Markup subclass instance for ``text`` that includes rather than
        escapes the HTML entities of ``text``, but does escape all other text.

    :raise ValueError: The given text is not a ``str`` or a contained HTML
        numeric entity value is out of range.

    Explicitly or implicitly created :class:`Text` objects fully escape the
    underlying text, meaning ``Text("&alpha; < &beta;")`` and ``Bold("&alpha; <
    &beta;")`` appear with ampersands and semicolons and not Greek letters.
    ``with_entities("&alpha; < &beta;")`` looks like "α < β".
    """
    if not isinstance(text,str):
        raise ValueError("Given text is not a str")

    content:list[TextContent] = []

    start = 0
    for match in _ENTITY_RE.finditer(text):
        if match.start() > start:
            content.append(text[start:match.start()])
        content.append(Entity(match.group(1)))
        start = match.end()

    if not content:
        return Text(text)

    if start < len(text):
        content.append(text[start:])

    return Span(*content)
