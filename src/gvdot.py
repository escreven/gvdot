"""
Generate and render Graphviz diagrams with clear, maintainable code by separating presentation from structure.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from html import escape as html_escape
from os import PathLike
from pathlib import Path, PurePath
import subprocess
from subprocess import CalledProcessError, TimeoutExpired
from typing import Any, Hashable, Self
import re

__version__ = "1.2.0"

__all__ = (
    "Markup", "Nonce", "Port", "Dot", "InvocationException",
    "ProcessException", "TimeoutException", "ShowException",
)

#
# Optional notebook support.
#

try:
    from IPython.display import display, Markdown, SVG, Image, Code
except ImportError:
    display  = None
    Markdown = None
    SVG      = None
    Image    = None
    Code     = None

def _missing_ipython():
    raise RuntimeError(
        "IPython is required to show Dot objects. "
        "Install with: pip install gvdot[ipython]")


@dataclass(slots=True)
class Markup:
    """
    A Graphviz DOT language markup string.

    Graphviz supports what it calls HTML strings such as ``<x<sub>1</sub>>``.
    Because in DOT language ``"<x<sub>1</sub>>"`` (note the quotes) is an
    ordinary non-HTML ID, gvdot uses :class:`Markup` to delineate HTML strings.

    :param markup: The DOT language markup text excluding the opening and
        closing angle brackets.
    """
    markup : str


#
# In addition to being a publicly available for creating unique IDs, nonces are
# used as edge discriminants in the multi-graph case when none is provided by
# the application.
#

class Nonce(Hashable):
    """
    A placeholder that :class:`Dot` resolves to a unique ID in DOT language
    representations.

    When generating the DOT language representation of a Dot object,
    :class:`Dot` resolves every Nonce that is part of the object or its theme
    chain to a DOT language ID, choosing IDs not used
    anywhere else in the object or theme chain.  :class:`Dot` resolves two
    Nonce objects ``u`` and ``v`` to the same ID if and only if ``u is v``.

    :param prefix: :class:`Dot` will resolve the Nonce to an ID of the form
        *prefix_n* where *prefix* is the given value and *n* is a small
        positive integer.


    Applications use Nonce objects to create identifiers that do not conflict
    with each other or with identifiers derived from input values.  For
    example, an application might complete an illustration of a linked list
    with

    .. code-block:: python

        nil = Nonce()
        dot.node(nil, role="nil")
        dot.edge(last_value, nil)

    The DOT language representation would then include a node statement for
    ``nil`` like

    .. code-block:: graphviz

            _nonce_1 [label="NIL" fontname="sans-serif" fontsize=8 style=filled
                shape=box width=0 height=0 margin=0.02]

    and, if ``last_value`` is ``"Fred"``, an edge statement like

    .. code-block:: graphviz

            Fred -> _nonce_1

    :class:`Dot` dynamically resolves Nonce objects each time it generates a
    DOT language representation.  Changing a Dot object may change the ID to
    which a Nonce object resolves.

    Nonce objects are :class:`Hashable` and objects ``u`` and ``v`` compare
    equal if and only if ``u`` is ``v``.
    """
    __slots__ = "prefix"

    def __init__(self, prefix:str="_nonce"):
        if not isinstance(prefix, str):
            raise ValueError(f"Nonce prefix {repr(prefix)} is not a string")
        self.prefix = prefix

    def __hash__(self):
        return hash(id(self))

    def __eq__(self, other):
        return other is self

    def __deepcopy__(self, memo):
        return self


type ID = str|int|float|bool|Markup|Nonce
"""
    Values corresponding to the DOT language non-terminal *ID* used for both
    entity identifiers and attribute values.  Consistent with the grammar,

    - using an int ``x`` as an :type:`ID` is equivalent to using ``str(x)``
    - using a float ``x`` as an :type:`ID` is equivalent to using ``str(x)``
    - using ``Markup(x)`` as an :type:`ID` is different than
      using ``x``

    For convenience, given that Graphviz uses ``true`` and ``false`` for
    boolean values,

    - using ``True`` as an :type:`ID` is equivalent to using ``"true"``
    - using ``False`` as an :type:`ID` is equivalent to using ``"false"``

    Nonce objects are placeholders for generated IDs.  See :class:`Nonce`.
"""

type _NormID = str | Nonce

def _id_key(normid:_NormID) -> tuple[int,str|int]:
    if isinstance(normid, str):
        return 0, normid
    else:
        return 1, id(normid)

def _id_debug(normid:_NormID) -> str:
    return normid if isinstance(normid, str) else repr(normid)

#
# Make sure the purported ID is in fact an ID and return its normalized
# representation (a string or Nonce).  We do extra work to avoid quoting when
# we can, in the hope this aids readability of the DOT language generated.
#

_SIMPLE_ID_RE = re.compile(
    r"[a-zA-Z_][a-zA-Z0-9_]*|" +
    r"-?([.][0-9]+|[0-9]+([.][0-9]*)?)")

_RESERVED_IDS = {
    "strict", "graph", "digraph", "node", "edge", "subgraph"
}

_NEEDESCAPE_RE = re.compile(r'["\n\r\\]')

def _normalize(id:Any, what:str) -> _NormID:
    match id:
        case Nonce():
            return id
        case bool():
            return "true" if id else "false"
        case Markup():
            return '<' + id.markup + '>'
        case str() | int() | float():
            s = str(id)
            if _SIMPLE_ID_RE.fullmatch(s) and s not in _RESERVED_IDS:
                return s
            else:
                if _NEEDESCAPE_RE.search(s):
                    s = s.replace('\\','\\\\')
                    s = s.replace('"','\\"')
                    s = s.replace('\r\n','\\n')
                    s = s.replace('\n','\\n')
                return '"' + s + '"'
        case _:
            raise ValueError(f"{what} {repr(id)} is not an ID")

#
# Return the quoted form of a normalized identifier, unless it is markup.
# Because the identifier is normalized, there is no need to escape it when
# quoting.
#

def _prefer_quoted(id:str):
    if id and id[0] != '"' and id[0] != '<':
        return '"' + id + '"'
    else:
        return id


@dataclass(slots=True)
class Port:
    """
    An edge endpoint.  Graphviz allows endpoints to be specified as a node
    identifier, an optional port name, and an optional compass point.  Properly
    speaking, in the DOT language grammar a port is the name and compass point
    components only, but for simplicity this class incorporates all three.

    :param node: The node identifier.

    :param name: The optional port name.

    :param cp: The optional compass point, which must be one of "n", "ne" "e",
        "se", "s", "sw", "w", "nw", "c", or "\\_".  Compass point "\\_" appears
        in the DOT grammar and is equivalent to None; it's included for
        completeness.
    """
    node : ID
    name : ID  | None = None
    cp   : str | None = None

#
# The allowed compass points.
#

_COMPASS_PT = { "n", "ne", "e", "se", "s", "sw", "w", "nw", "c" }

#
# Normalized, validated, and application mutation safe version of a Port.
# Property implicit=True means the application provided only an ID, not a Port
# object.
#

class _NormPort:
    __slots__ = "node", "name", "cp", "implicit"

    def __init__(self, point:ID|Port):

        if isinstance(point,Port):
            self.node = _normalize(point.node,"Endpoint node identifier")
            self.name = (_normalize(name,"Endpoint port field")
                         if (name := point.name) is not None else None)
            if (cp := point.cp) is not None:
                if cp == '_':
                    cp = None
                elif cp not in _COMPASS_PT:
                    raise ValueError(f"Invalid compass point: {repr(cp)}")
            self.cp = cp
            self.implicit = False
        else:
            self.node = _normalize(point, "Endpoint node identifier")
            self.name = None
            self.cp = None
            self.implicit = True

    def __repr__(self):
        return "_NormPort<{},{},{},{}>".format(
            repr(self.node), repr(self.name),
            repr(self.cp), repr(self.implicit))

    def dot(self, resolver:_NonceResolver):
        result = resolver.resolve(self.node)
        if (name := self.name) is not None:
            name = resolver.resolve(name)
            if name in _COMPASS_PT: name = _prefer_quoted(name)
            result += ":" + name
        if (cp := self.cp) is not None:
            result += ":" + cp
        return result

    def __deepcopy__(self, memo):
        return self

#
# Graphs, nodes, and edges all have attributes.  While from the grammar an
# attribute can be any ID, all attributes supported by Graphviz have names that
# are lexically identifiers in Python, and through this API are specified via
# keyword parameter names.
#

type _Attrs = dict[str,_NormID]

type _Roles = dict[_NormID,_Attrs]

#
# Update target entity attributes based on a "**attrs" parameter in the public
# API.  Observe that "foo=None" deletes attribute foo if it exists.
#

def _set_attrs(target:_Attrs, attrargs:dict[str,Any], permit_role=False):
    for name, value in attrargs.items():
        if name[-1] == '_':
            name = name[:-1]
        if not permit_role and name == 'role':
            raise ValueError(f"Attribute 'role' is reserved")
        if value is None:
            target.pop(name,None)
        else:
            target[name] = _normalize(value,f"Attribute {name} value")

#
# Return the flattened attributes of the possibly role-bearing object.
#

def _integrate_role(attrs:_Attrs, roles:_Roles, what:str, identity:Any):
    if (role_name := attrs.get('role')) is not None:
        if (role_attrs := roles.get(role_name)) is not None:
            attrs = attrs.copy()
            for name, value in role_attrs.items():
                if name not in attrs:
                    attrs[name] = value
            del attrs['role']
        else:
            if identity is not None:
                what += " " + str(identity)
            raise RuntimeError(
                f"Role {role_name} used by {what} not defined")
    return attrs

#
# Merge target and source role dictionaries with source having precedence.
#

def _update_roles(target:_Roles, source:_Roles) -> None:
    for role, source_attrs in source.items():
        if (target_attrs := target.get(role)) is not None:
            target_attrs.update(source_attrs)
        else:
            target[role] = source_attrs.copy()

#
# We prefer quoted strings for attribute values that are general text.
#

_TEXT_ATTRS = { "label", "headlabel", "taillabel", "xlabel", "comment" }

#
# We normalize discriminants to _NormIDs if they are given, otherwise (when
# given as None) they are normalized to _Nonces for multigraphs and None for
# non-multigraphs.
#

type _NormDisc = _NormID | None

#
# Identify nodes, edges, and subgraphs internally.  Node keys and subgraph keys
# are normalized IDs.  Edge keys are normalized (node1,node2,discriminant)
# triples.  For non-directed graphs, node1 <= node2.
#

type _NodeKey = _NormID

type _EdgeKey = tuple[_NodeKey,_NodeKey,_NormDisc]

type _SubgraphKey = _NormID

#
# Edges have port specifications and attributes, and can be directed.
#

class _Edge:
    __slots__ = "normport1", "normport2", "normdisc", "directed", "attrs"

    def __init__(self, directed:bool, normport1:_NormPort,
                 normport2:_NormPort, normdisc:_NormDisc):
        self.normport1 = normport1
        self.normport2 = normport2
        self.normdisc = normdisc
        self.directed = directed
        self.attrs:_Attrs = dict()

    def update_ports(self, otherport1:_NormPort, otherport2:_NormPort):

        normport1 = self.normport1
        normport2 = self.normport2

        if otherport1.node != normport1.node:
            normport1, normport2 = normport2, normport1
            assert not self.directed

        assert otherport1.node == normport1.node
        assert otherport2.node == normport2.node

        if not otherport1.implicit: normport1 = otherport1
        if not otherport2.implicit: normport2 = otherport2

        self.normport1 = normport1
        self.normport2 = normport2

    def __repr__(self):
        return "_Edge<{},{},{},{}>".format(
            repr(self.normport1), repr(self.normport2),
            repr(self.normdisc), repr(self.directed))

    #
    # DOT language representation.
    #

    def dot(self, resolver:_NonceResolver):
        return (self.normport1.dot(resolver) +
                (" -> " if self.directed else " -- ") +
                self.normport2.dot(resolver))

    #
    # Used in exception messages.
    #

    def name(self):
        s = str(self)
        if self.normdisc is not None:
            s += " / " + _id_debug(self.normdisc)
        return s

#
# A _Mien is the result of merging the heritable attributes of themes and a
# Dot object.
#

class _Mien:
    __slots__ = ("d_grapha", "d_nodea", "d_edgea", "grapha",
                 "noderoles", "edgeroles", "graphroles")

    d_grapha   : _Attrs
    d_nodea    : _Attrs
    d_edgea    : _Attrs
    grapha     : _Attrs
    graphroles : _Roles
    noderoles  : _Roles
    edgeroles  : _Roles

    def __init__(self, dot:Dot):

        if (theme := dot.theme) is None:
            self.d_grapha = dot.d_grapha
            self.d_nodea = dot.d_nodea
            self.d_edgea = dot.d_edgea
            self.grapha = dot.grapha
            self.graphroles = dot.graphroles
            self.noderoles = dot.noderoles
            self.edgeroles = dot.edgeroles
            return

        stack = [ dot ]
        while theme is not None:
            stack.append(theme)
            theme = theme.theme

        d_grapha   = dict()
        d_nodea    = dict()
        d_edgea    = dict()
        grapha     = dict()
        graphroles = defaultdict(dict)
        noderoles  = defaultdict(dict)
        edgeroles  = defaultdict(dict)

        for theme in reversed(stack):
            d_grapha.update(theme.d_grapha)
            d_nodea.update(theme.d_nodea)
            d_edgea.update(theme.d_edgea)
            grapha.update(theme.grapha)
            _update_roles(graphroles,theme.graphroles)
            _update_roles(noderoles,theme.noderoles)
            _update_roles(edgeroles,theme.edgeroles)

        self.d_grapha   = d_grapha
        self.d_nodea    = d_nodea
        self.d_edgea    = d_edgea
        self.grapha     = grapha
        self.graphroles = graphroles
        self.noderoles  = noderoles
        self.edgeroles  = edgeroles


#
# Return a list of all _NormIDs values in a Dot object and its _Mien, including
# None.  (Including None simplifies the collection code, and they're filtered
# out for free when used.)
#

def _collect_ids(dot:Dot, mien:_Mien) -> list[_NormID|None]:

    result:list[_NormID|None] = [ dot.graphid ]

    result.extend(mien.d_grapha.values())
    result.extend(mien.d_nodea.values())
    result.extend(mien.d_edgea.values())
    result.extend(mien.grapha.values())
    for attrs in mien.graphroles.values(): result.extend(attrs.values())
    for attrs in mien.noderoles.values(): result.extend(attrs.values())
    for attrs in mien.edgeroles.values(): result.extend(attrs.values())

    for node, attrs in dot.nodemap.items():
        result.append(node)
        result.extend(attrs.values())

    for edge in dot.edgemap.values():
        result.append(edge.normport1.node)
        result.append(edge.normport1.name)
        result.append(edge.normport2.node)
        result.append(edge.normport2.name)
        result.extend(edge.attrs.values())

    def add_block(block:Block):
        result.append(block.graphid)
        result.extend(block.d_grapha.values())
        result.extend(block.d_nodea.values())
        result.extend(block.d_edgea.values())
        result.extend(block.grapha.values())
        for subgraph in block.subgraphs:
            add_block(subgraph)

    for subgraph in dot.subgraphs:
        add_block(subgraph)

    return result


class _NonceResolver:
    __slots__ = "avoid", "nonce_id", "prefix_seqno"

    avoid        : set[str]
    nonce_id     : dict[Nonce,str]
    prefix_seqno : dict[str,int]

    def __init__(self, dot:Dot, mien:_Mien):
        self.avoid = { normid for normid in _collect_ids(dot,mien)
                       if isinstance(normid,str) }
        self.nonce_id     = dict()
        self.prefix_seqno = dict()

    def resolve(self, normid:_NormID) -> str:

        if isinstance(normid, str):
            return normid

        if (resolved := self.nonce_id.get(normid)) is not None:
            return resolved

        prefix = normid.prefix
        seqno = self.prefix_seqno.get(prefix, 0)
        while True:
            seqno += 1
            candidate = _normalize(f"{prefix}_{seqno}", "Generated ID")
            assert isinstance(candidate, str)
            if candidate not in self.avoid:
                self.avoid.add(candidate)
                self.nonce_id[normid] = candidate
                self.prefix_seqno[prefix] = seqno
                return candidate


class Block:
    """
    A scope for graph and default attribute assignments and a container for
    node, edge, and subgraph definitions.

    :class:`Block` is the base class of :class:`Dot`.

    There is a one-to-one correspondence between Block objects and the graph
    and subgraph statements of a Dot object's DOT language representation.  The
    Dot object itself corresponds to the top-level ``graph`` or ``digraph``
    form.  The remaining Block objects are those returned by methods
    :meth:`~Block.subgraph` or :meth:`~Block.subgraph_define`.

    Blocks should only be created by calling :func:`Dot`,
    :meth:`~Block.subgraph`, or :meth:`~Block.subgraph_define`.  Executing
    :func:`Block` directly raises a :class:`RuntimeError`.
    """
    __slots__ = (
        "graphid", "d_grapha", "d_nodea", "d_edgea", "grapha",
        "subgraphmap", "nodes", "edges", "subgraphs",
        "_dot", "_parent"
    )
    def __init__(self):
        raise RuntimeError(
            "Block objects cannot be created directly")

    def _block_init(self, graphid:_NormID|None, dot:Dot,
                    parent:Block|None) -> None:
        self.graphid = graphid
        self.d_grapha:_Attrs = dict()
        self.d_nodea:_Attrs = dict()
        self.d_edgea:_Attrs = dict()
        self.grapha:_Attrs = dict()
        self.subgraphmap:dict[_SubgraphKey,Block] = dict()
        self.nodes:list[_NodeKey] = []
        self.edges:list[_Edge] = []
        self.subgraphs:list[Block] = []
        self._dot = dot
        self._parent = parent

    def graph_default(self, **attrs:ID|None) -> Self:
        """
        Establish or amend default graph attributes.

        :param attrs: New or amending attribute value assignments.
        """
        _set_attrs(self.d_grapha,attrs)
        return self

    def graph(self, **attrs:ID|None) -> Self:
        """
        Establish or amend graph attributes.

        :param attrs: New or amending attribute value assignments.
        """
        _set_attrs(self.grapha,attrs,True)
        return self

    def node_default(self, **attrs:ID|None) -> Self:
        """
        Establish or amend default node attributes.

        :param attrs: New or amending attribute value assignments.
        """
        _set_attrs(self.d_nodea,attrs)
        return self

    def node(self, id:ID, /, **attrs:ID|None) -> Self:
        """
        Define a node or amend its attributes.

        :param id: The node to define or amend.
        :param attrs: New or amending attribute value assignments.

        The Block object through which a node is defined determines where in
        the DOT language representation the corresponding node statement will
        appear.  However, node identity is global, so a node may be amended
        through any Block object.

        For example,

        .. code-block:: python

            dot = Dot()
            sub1 = dot.subgraph("Sub1")
            sub2 = dot.subgraph("Sub2")
            sub2.node("a", label="Defined in Sub2")
            sub1.node("a", fontsize=10)
            dot.node("a", color="blue")

        has the Dot language representation

        .. code-block:: graphviz

            graph {
                subgraph Sub1 {
                }
                subgraph Sub2 {
                    a [label="Defined in Sub2" fontsize=10 color=blue]
                }
            }
        """
        nodemap = self._dot.nodemap
        key = _normalize(id, "Node identifier")
        if key not in nodemap:
            self.nodes.append(key)
        _set_attrs(nodemap[key],attrs,True)
        return self

    def node_define(self, id:ID, /, **attrs:ID|None) -> Self:
        """
        Same as method :meth:`node`, except require the node to be undefined.

        :param id: The node to define.
        :param attrs: New attribute value assignments.
        :raises RuntimeError: The node is already defined.
        """
        nodemap = self._dot.nodemap
        key = _normalize(id, "Node identifier")
        if key in nodemap:
            raise RuntimeError(f"Node {key} already defined")
        self.nodes.append(key)
        _set_attrs(nodemap[key],attrs,True)
        return self

    def node_update(self, id:ID, /, **attrs:ID|None) -> Self:
        """
        Same as method :meth:`node`, except require the node to be defined.

        :param id: The node to amend.
        :param attrs: Amending attribute value assignments.
        :raises RuntimeError: The node is not defined.
        """
        nodemap = self._dot.nodemap
        key = _normalize(id, "Node identifier")
        if key not in nodemap:
            raise RuntimeError(f"Node {key} not defined")
        _set_attrs(nodemap[key],attrs,True)
        return self

    def node_is_defined(self, id:ID) -> bool:
        """
        Return True iff the identified node is defined.

        :param id: The node to test.
        """
        return _normalize(id, "Node identifier") in self._dot.nodemap

    def edge_default(self, **attrs:ID|None) -> Self:
        """
        Establish or amend default edge attributes.

        :param attrs: New or amending attribute value assignments.
        """
        _set_attrs(self.d_edgea,attrs)
        return self

    def _edge_preamble(self, point1:ID|Port, point2:ID|Port,
                       discriminant:ID|None
                       ) -> tuple[_EdgeKey, _NormPort, _NormPort, _NormDisc]:
        """
        Implement the common preamble of all edge identity based methods.
        """
        dot = self._dot
        normport1 = _NormPort(point1)
        normport2 = _NormPort(point2)

        if discriminant is not None:
            if not dot.multigraph:
                raise ValueError(
                    "Discriminant must be None for non-multigraphs")
            normdisc = _normalize(discriminant,"Edge discriminant")
        elif dot.multigraph:
            normdisc = Nonce("__D")
        else:
            normdisc = None

        node1 = normport1.node
        node2 = normport2.node

        if dot.directed or _id_key(node1) <= _id_key(node2):
            key = (node1,node2,normdisc)
        else:
            key = (node2,node1,normdisc)

        return key, normport1, normport2, normdisc

    def _edge(self, point1:ID|Port, point2:ID|Port,
              discriminant:ID|None, attrargs:dict[str,Any],
              must_exist=False, must_not_exist=False) -> Self:
        """
        Define or amend an edge, enforcing defined/not-defined constraints.
        """
        dot = self._dot
        key, normport1, normport2, normdisc = self._edge_preamble(
            point1,point2,discriminant)

        if (edge := (edgemap := dot.edgemap).get(key)) is None:
            edge = _Edge(dot.directed,normport1,normport2,normdisc)
            if must_exist:
                if dot.multigraph:
                    advice = " (missing or wrong discriminant?)"
                else:
                    advice = ""
                raise RuntimeError(f"Edge {edge.name()} not defined{advice}")
            edgemap[key] = edge
            self.edges.append(edge)
        else:
            if must_not_exist:
                raise RuntimeError(f"Edge {edge.name()} already defined")
            edge.update_ports(normport1,normport2)

        _set_attrs(edge.attrs,attrargs,True)
        return self

    def edge(self, point1:ID|Port, point2:ID|Port,
             discriminant:ID|None=None, /, **attrs:ID|None) -> Self:
        """
        Define an edge or amend its attributes and endpoints.

        :param point1: The first edge endpoint, either a node identifier or a
            port.  In the directed case, this is the tail of the arc.

        :param point2: The second edge endpoint, either a node identifier or a
            port.  In the directed case, this is the head of the arc.

        :param discriminant: A value allowing the application to refer to
            specific edges created in a multigraph.  Discriminants may only be
            provided for multigraphs, but are not required for multigraphs.  If
            provided, discriminants need only be unique for a given node pair.
            Discriminants do not appear in the DOT language representation.

        :param attrs: New or amending attribute value assignments.

        The Block object through which an edge is defined determines where in
        the DOT language representation the corresponding edge statement will
        appear.  However, edge identity is global, so an edge may be amended
        through any Block object.

        Consistent with the DOT language, only the ``id`` portion of a
        :class:`Port` is relevant to edge identification.  In the code below,
        the first :meth:`edge` call defines an edge, and the second amends the
        same edge's attributes.

        .. code-block:: python

            dot = Dot()
            dot.edge(Port("a",cp="n"), Port("b","output","s"), color="blue")
            dot.edge("a","b",style="dashed")

        The outcome of calling :meth:`edge` for an endpoint node pair between
        which there is an existing edge depends on whether or not the Dot
        object is multigraph and the specified discriminant.

        .. list-table::
            :header-rows: 1
            :align: center

            * - Multigraph
              - Specified Discriminant
              - Outcome
            * - No
              - (Not permitted)
              - Existing edge amended
            * - Yes
              - None
              - New edge defined
            * - Yes
              - Existing among node pair edges
              - Existing edge amended
            * - Yes
              - New among node pair edges
              - New edge defined

        When amending an edge, if an endpoint argument is a :class:`Port`, that
        specification replaces the endpoint's previous port (if any).  For
        example, the DOT representation of

        .. code-block:: python

            dot = Dot()
            dot.edge(Port("a", cp="s"), Port("b", cp="s"))
            dot.edge(Port("a", cp="n"), "b")

        includes the edge ``a:n -- b:s``.

        For non-directed graphs, amending an edge updates the edge's endpoint
        order if the given order differs.

        .. code-block:: python

            dot = Dot()
            dot.edge("a","b")   # Define a non-directed edge between a and b.
            dot.edge("b","a")   # Amend the edge

        The Dot object above has the DOT language representation

        .. code-block:: graphviz

            graph {
                b -- a
            }

        As in DOT, edge endpoint nodes need not be defined.  The output of

        .. code-block:: python

            dot = Dot()
            dot.edge("a","b",label="An example edge")
            print(dot,file=output_file)

        will include an edge statement, but no node statements.
        """
        return self._edge(point1,point2,discriminant,attrs)

    def edge_define(self, point1:ID|Port, point2:ID|Port,
                    discriminant:ID|None=None, /, **attrs:ID|None) -> Self:
        """
        Same as method :meth:`edge`, except require the edge to be undefined.

        :param point1: See :meth:`edge`.
        :param point2: See :meth:`edge`.
        :param discriminant: See :meth:`edge`.
        :raises RuntimeError: The edge is already defined.
        """
        return self._edge(point1,point2,discriminant,attrs,must_not_exist=True)

    def edge_update(self, point1:ID|Port, point2:ID|Port,
                    discriminant:ID|None=None, /, **attrs:ID|None) -> Self:
        """
        Same as method :meth:`edge`, except require the edge to be defined.

        :param point1: See :meth:`edge`.
        :param point2: See :meth:`edge`.
        :param discriminant: See :meth:`edge`.
        :raises RuntimeError: The edge is not defined.
        """
        return self._edge(point1,point2,discriminant,attrs,must_exist=True)

    def edge_is_defined(self, point1:ID|Port, point2:ID|Port,
                        discriminant:ID|None=None) -> bool:
        """
        Return True iff the identified edge is defined.

        :param point1: See :meth:`edge`.
        :param point2: See :meth:`edge`.
        :param discriminant: See :meth:`edge`.
        """
        key, _, _, _ = self._edge_preamble(point1,point2,discriminant)
        return key in self._dot.edgemap

    def subgraph(self, id:ID|None=None) -> Block:
        """
        Define or prepare to amend a subgraph.

        :param id: The subgraph to define or amend.

        :return: A new or existing Block object.  Graph attributes, attribute
            defaults, and nodes and edges defined through the block appear
            within a subgraph statement of the enveloping Dot object's DOT
            language representation.

        Subgraph identities are scoped to parent graphs or subgraphs, so

        .. code-block:: python

            dot = Dot(id="Name")
            dot.subgraph("Name").subgraph("Name").subgraph("Name")

        raises no exceptions and has the DOT language representation

        .. code-block:: graphviz

            graph Name {
                subgraph Name {
                    subgraph Name {
                        subgraph Name {
                        }
                    }
                }
            }
        """
        dot = self._dot
        if id is not None:
            graphid = _normalize(id, "Subgraph identifier")
            if (sub := self.subgraphmap.get(graphid)) is not None:
                return sub
        else:
            graphid = None
        sub = Block.__new__(Block)
        sub._block_init(graphid, dot, self)
        self.subgraphs.append(sub)
        if graphid is not None:
            self.subgraphmap[graphid] = sub
        return sub

    def subgraph_define(self, id:ID) -> Block:
        """
        Same as :meth:`subgraph`, except require the subgraph to be
        undefined.

        :param id: The subgraph to define.

        :raises RuntimeError: The subgraph is already defined.
        """
        key = _normalize(id,"Subgraph identifier")
        if key in self.subgraphmap:
            raise RuntimeError(f"Subgraph {key} already defined")
        return self.subgraph(id)

    def subgraph_update(self, id:ID) -> Block:
        """
        Same as :meth:`subgraph`, except require the subgraph to be
        defined.

        :param id: The subgraph to amend.

        :raises RuntimeError: The subgraph is not defined.
        """
        key = _normalize(id,"Subgraph identifier")
        if key not in self.subgraphmap:
            raise RuntimeError(f"Subgraph {key} not defined")
        return self.subgraph(id)

    def subgraph_is_defined(self, id:ID) -> bool:
        """
        Return True iff the identified subgraph is defined.

        :param id: The subgraph to test.
        """
        return _normalize(id,"Subgraph identifier") in self.subgraphmap

    def all_default(self, **attrs:ID|None) -> Self:
        """
        Establish or amend default graph, node, and edge attributes all at once.

        Executing ``block.all_default(**attrs)`` has the same effect as
        executing

        .. code-block:: python

            block.graph_default(**attrs)
            block.node_default(**attrs)
            block.edge_default(**attrs)
        """
        _set_attrs(self.d_grapha,attrs)
        _set_attrs(self.d_nodea,attrs)
        _set_attrs(self.d_edgea,attrs)
        return self

    def parent(self) -> Block|None:
        """
        Return the parent Block object, if there is one.  Otherwise return
        None.
        """
        return self._parent

    def dot(self) -> Dot:
        """
        Return the enveloping Dot object.
        """
        return self._dot

    def _statements(self, lines:list[str], indent:int, mien:_Mien,
                    resolver:_NonceResolver) -> None:
        """
        Append the block's statements to lines, indented as specified.
        """
        prefix     = "    " * indent
        base       = len(lines)
        blanklines = 0
        resolve    = resolver.resolve

        def statement(s:str, attrs:_Attrs|None):
            s = prefix + s
            if attrs:
                pieces = []
                for key, value in attrs.items():
                    value = resolve(value)
                    if key in _TEXT_ATTRS:
                        value = _prefer_quoted(value)
                    pieces.append(f"{key}={value}")
                s += " [" + ' '.join(pieces) + "]"
            lines.append(s)

        def blankline():
            nonlocal blanklines
            if lines[-1] != '':
                lines.append('')
                blanklines += 1

        blankline()
        if type(self) is Dot:
            d_grapha = mien.d_grapha
            d_nodea  = mien.d_nodea
            d_edgea  = mien.d_edgea
        else:
            d_grapha = self.d_grapha
            d_nodea  = self.d_nodea
            d_edgea  = self.d_edgea

        if d_grapha: statement("graph",d_grapha)
        if d_nodea:  statement("node",d_nodea)
        if d_edgea:  statement("edge",d_edgea)

        graphroles = mien.graphroles
        noderoles  = mien.noderoles
        edgeroles  = mien.edgeroles
        nodemap    = self._dot.nodemap
        graphid    = self.graphid
        grapha     = _integrate_role(mien.grapha if type(self) is Dot
                                     else self.grapha, graphroles,
                                     "graph",graphid)

        blankline()
        for key, value in grapha.items():
            if key != "label":
                value = resolve(value)
                if key in _TEXT_ATTRS:
                    value = _prefer_quoted(value)
                statement(f"{key}={value}",None)

        blankline()
        for nodekey in self.nodes:
            attrs = _integrate_role(nodemap[nodekey],noderoles,"node",nodekey)
            statement(resolve(nodekey),attrs)

        blankline()
        for edge in self.edges:
            attrs = _integrate_role(edge.attrs,edgeroles,"edge", edge)
            statement(edge.dot(resolver),attrs)

        for subgraph in self.subgraphs:
            blankline()
            lines.append(prefix + "subgraph " +
                         ("" if subgraph.graphid is None
                          else resolve(subgraph.graphid) + " ") + "{")
            subgraph._statements(lines,indent+1,mien,resolver)
            lines.append(prefix + "}")

        if "label" in grapha:
            blankline()
            label = resolve(grapha['label'])
            statement(f"label={_prefer_quoted(label)}",None)

        if not lines[-1]:
            lines.pop()
            blanklines -= 1

        if len(lines) - base - blanklines <= 8 or blanklines == 1:
            lines[base:] = [ line for line in lines[base:] if line ]


class Dot(Block):
    """
    A DOT language builder.

    :param directed: Make the graph directed.

    :param strict: Include the ``strict`` keyword.  This argument is present
        for completeness.  It's unlikely to be useful with Dot objects since
        :class:`Dot` guarantees edge uniqueness for non-multigraphs.

    :param multigraph: Support multiple edges between the same node pair
        (ordered pair in the directed case.)  This parameter affects the
        behavior of methods :meth:`~Block.edge`, :meth:`~Block.edge_define`,
        and :meth:`~Block.edge_update` but does not change the DOT language
        produced from the Dot object.

    :param id: The graph identifier.

    :param comment: Possibly multiline text prepended as a ``//`` style
        comment.

    :raises ValueError: If both ``strict`` and ``multigraph`` are True.
    """
    __slots__ = (
        "directed", "strict", "multigraph", "comment",
        "graphroles", "noderoles", "edgeroles",
        "nodemap", "edgemap", "theme"
    )
    def __init__(self, *, directed:bool=False, strict:bool=False,
                 multigraph:bool=False, id:ID|None=None,
                 comment:str|None = None):

        if multigraph and strict:
            raise ValueError("Cannot specify both multigraph and strict")

        self.directed   = directed
        self.strict     = strict
        self.multigraph = multigraph
        self.comment    = comment

        self.graphroles:_Roles = defaultdict(dict)
        self.noderoles:_Roles  = defaultdict(dict)
        self.edgeroles:_Roles  = defaultdict(dict)

        self.nodemap:dict[_NodeKey,_Attrs] = defaultdict(dict)
        self.edgemap:dict[_EdgeKey,_Edge]  = dict()
        self.theme:Dot|None = None

        graphid = None if id is None else _normalize(id, "Graph identifier")
        self._block_init(graphid, self, None)

    def __deepcopy__(self, memo:dict[int,Any]) -> Dot:

        #
        # Create a new copy, if there isn't one already in memo.
        #

        if (other := memo.get(selfid := id(self))) is not None:
            return other

        other = Dot.__new__(Dot)
        memo[selfid] = other

        #
        # We want the original and the copy to reference identical themes.
        #

        other.theme = self.theme

        #
        # The rest is standard.
        #

        other.directed    = deepcopy(self.directed,memo)
        other.strict      = deepcopy(self.strict,memo)
        other.multigraph  = deepcopy(self.multigraph,memo)
        other.graphid     = deepcopy(self.graphid,memo)
        other.comment     = deepcopy(self.comment,memo)
        other.d_grapha    = deepcopy(self.d_grapha,memo)
        other.d_nodea     = deepcopy(self.d_nodea,memo)
        other.d_edgea     = deepcopy(self.d_edgea,memo)
        other.grapha      = deepcopy(self.grapha,memo)
        other.graphroles  = deepcopy(self.graphroles,memo)
        other.noderoles   = deepcopy(self.noderoles,memo)
        other.edgeroles   = deepcopy(self.edgeroles,memo)
        other.nodemap     = deepcopy(self.nodemap,memo)
        other.edgemap     = deepcopy(self.edgemap,memo)
        other.subgraphmap = deepcopy(self.subgraphmap,memo)
        other.nodes       = deepcopy(self.nodes,memo)
        other.edges       = deepcopy(self.edges,memo)
        other.subgraphs   = deepcopy(self.subgraphs,memo)
        other._dot        = other
        other._parent     = None

        return other

    def is_multigraph(self) -> bool:
        """
        Return True iff this is a multigraph Dot object.
        """
        return self.multigraph

    def graph_role(self, role:str, /, **attrs:ID|None) -> Self:
        """
        Define a graph role or amend its attributes.

        :param role: The graph role to define or amend.
        :param attrs: New or amending attribute value assignments.
        """
        #
        # NOTE: Even though role names are limited to str, we normalize them
        # because they are normalized when assigned as attribute values.
        #
        _set_attrs(self.graphroles[_normalize(role,"Role name")],attrs)
        return self

    def node_role(self, role:str, /, **attrs:ID|None) -> Self:
        """
        Define a node role or amend its attributes.

        :param role: The node role to define or amend.
        :param attrs: New or amending attribute value assignments.
        """
        _set_attrs(self.noderoles[_normalize(role,"Role name")],attrs)
        return self

    def edge_role(self, role:str, /, **attrs:ID|None) -> Self:
        """
        Define an edge role or amend its attributes.

        :param role: The edge role to define or amend.
        :param attrs: New or amending attribute value assignments.
        """
        _set_attrs(self.edgeroles[_normalize(role,"Role name")],attrs)
        return self

    def all_role(self, role:str, /, **attrs:ID|None) -> Self:
        """
        Define or amend the attributes of same-named graph, node, and edge
        roles all at once.

        Executing ``dot.all_role(role, **attrs)`` has the same effect as
        executing

        .. code-block:: python

            dot.graph_role(role, **attrs)
            dot.node_role(role, **attrs)
            dot.edge_role(role, **attrs)
        """
        normrole = _normalize(role,"Role name")
        _set_attrs(self.graphroles[normrole],attrs)
        _set_attrs(self.noderoles[normrole],attrs)
        _set_attrs(self.edgeroles[normrole],attrs)
        return self

    def copy(self, *, id:ID|None=None, comment:str|None=None) -> Dot:
        """
        Return a deep copy of the Dot object.

        :param id: The copy's graph identifier.  If not provided, the copy will
            have the Dot object's graph identifier.

        :param comment: The copy's comment.  If not provided, the copy will
            have the Dot object's comment.

        If the Dot object is using a theme, the copy will use the identical
        theme.
        """
        result = deepcopy(self)
        if id is not None:
            result.graphid = _normalize(id,"Graph identifier")
        if comment is not None:
            result.comment = comment
        return result

    def use_theme(self, theme:Dot|None) -> Self:
        """
        Inherit graph, default graph, default node, default edge, and role
        attribute values from ``theme``.

        :class:`Dot` forms DOT language representations by merging inherited
        attribute values with a Dot object's own assigned values (which have
        precedence).  Inheritance can be chained, with themes inheriting from
        themes.  The final merged result incorporates attributes from the
        entire chain.

        Theme use is dynamic.  Any change to the theme inheritance chain or
        heritable attributes of a theme in the chain is immediately reflected
        in the Dot object's DOT language representation.

        :param theme: The attribute inheritance source or None.  If ``theme``
            is None, the Dot object does not inherit from any theme.

        :raises ValueError: Using the theme would create an inheritance cycle.
        """
        if theme is not None:
            if not isinstance(theme,Dot):
                # Dynamic check in case a programmer gets mixed up between a
                # Dot object and one of its blocks.
                raise RuntimeError("Theme must be a Dot object")
            current = theme
            while current is not None:
                if current is self:
                    raise ValueError("Using theme would create a cycle")
                current = current.theme
        self.theme = theme
        return self

    def __str__(self) -> str:
        """
        The DOT language representation of the Dot object.
        """
        lines = []

        if comment := self.comment:
            for commentline in comment.splitlines():
                lines.append("// " + commentline)
            lines.append("")

        mien = _Mien(self)
        resolver = _NonceResolver(self, mien)
        lines.append(("strict " if self.strict else "") +
                     ("digraph " if self.directed else "graph ") +
                     ("" if self.graphid is None else
                      resolver.resolve(self.graphid) + " ") +
                     "{")

        self._statements(lines,1,mien,resolver)

        lines.append("}\n")

        return '\n'.join(lines)

    def to_rendered(self, program:str|PathLike="dot", *, format="png",
                    dpi:float|None=None, size:int|float|str|None=None,
                    ratio:float|str|None=None, timeout:float|None=None,
                    directory:str|PathLike|None=None) -> bytes:
        """
        Render the Dot object by invoking a Graphviz program.  The input to the
        program is the object's DOT language representation.

        :param program: Which Graphviz program to use (dot by default).
            ``program`` should either be the name of the program or a path to
            the program.

        :param format: The output format desired (png by default).
            :meth:`to_rendered` converts the specified value to lowercase if it
            isn't already, then uses it to form the ``-T`` argument to the
            specified program.

        :param dpi: Render with this many pixels per inch.  See the Graphviz
            `dpi <https://graphviz.org/docs/attrs/dpi/>`_ attribute
            documentation.

        :param size: Specify a maximum or minimum size.  See the Graphviz
            `size <https://graphviz.org/docs/attrs/size/>`_ attribute
            documentation.

        :param ratio: Set the aspect ratio.  See the Graphviz `ratio
            <https://graphviz.org/docs/attrs/ratio/>`_ attribute documentation.

        :param timeout: Limit the program execution time to this many seconds.

        :param directory: If specified, ``program`` is interpreted as a path
            relative to ``directory``.

        :return: The output bytes of the specified program.

        :raises InvocationException: Could not invoke the program, likely
            because it wasn't found.

        :raises ProcessException: The invoked program exited with a non-zero
            status code.  :class:`ProcessException` objects include the status
            code and stderr of the program as properties.

        :raises TimeoutException: The invoked program took longer than
            ``timeout`` seconds to run and was killed.

        If the process's ``PATH`` includes directory ``/opt/graphviz/bin`` and
        that is the only directory in ``PATH`` including Graphviz executables,
        the following :meth:`to_rendered` calls are equivalent:

        .. code-block:: python

            data = dot.to_rendered(program="circo")

            data = dot.to_rendered(program="/opt/graphviz/bin/circo")

            data = dot.to_rendered(program="circo",
                                   directory="/opt/graphviz/bin")

            data = dot.to_rendered(program="graphviz/bin/circo",
                                   directory="/opt")

        """
        t_arg = f"-T{format.lower()}"

        input = str(self).encode()

        if directory is not None:
            program = PurePath(directory,program)

        program = str(program)

        command = [ program, t_arg ]

        if dpi is not None:
            command.append(f"-Gdpi={dpi}")

        if size is not None:
            command.append(f"-Gsize={size}")

        if ratio is not None:
            command.append(f"-Gratio={ratio}")

        try:
            completed = subprocess.run(
                command, input=input, capture_output=True,
                text=False, timeout=timeout, check=True)
        except CalledProcessError as ex:
            raise ProcessException(
                program, ex.returncode, ex.stderr) from None
        except TimeoutExpired as ex:
            assert timeout is not None
            raise TimeoutException(
                program, timeout, "" if ex.stderr is None
                else ex.stderr) from None
        except Exception as ex:
            raise InvocationException(program) from ex

        return completed.stdout

    def to_svg(self, program="dot", *, inline=False,
               dpi:float|None=None, size:int|float|str|None=None,
               ratio:float|str|None=None, timeout:float|None=None,
               directory:str|PathLike|None=None) -> str:
        """
        Convert the Dot object to an SVG string by invoking a Graphviz program.

        :param inline: Generate SVG without an XML header.  Be aware that
            older, still commonly installed versions of Graphviz do not support
            inline SVG generation.

        For the remaining parameters, and for the exceptions raised, see
        :meth:`to_rendered`.
        """
        format = "svg_inline" if inline else "svg"

        data = self.to_rendered(
            program=program, format=format, dpi=dpi, size=size,
            ratio=ratio, timeout=timeout, directory=directory)

        return data.decode()

    def save(self, filename:str|PathLike, program="dot", *,
             exclusive:bool=False, format:str|None=None,
             dpi:float|None=None, size:int|float|str|None=None,
             ratio:float|str|None=None, timeout:float|None=None,
             directory:str|PathLike|None=None) -> None:
        """
        Save a rendering of the Dot object to a file.  :meth:`save`
        generates the file data by invoking a Graphviz program.

        :param filename: The name of the file to write.

        :param exclusive: Fail if the file already exists.

        :raises ValueError: The format was not specified and could not be
            inferred from the file extension.

        :raises FileExistsError: The file already exists and option
            ``exclusive`` is true.

        For the remaining parameters, and for additional exceptions raised, see
        :meth:`to_rendered`.

        Parameter ``format`` is optional.  If not given, :meth:`save` attempts
        to infer the format from the file extension.  The file extensions for
        which :meth:`save` infers formats by case insensitive comparison are
        ``.svg``, ``.png``, ``.jpg``, ``.jpeg``, ``.gif``, and ``.pdf``.
        """
        filepath = Path(filename)

        if format is None:
            extension = filepath.suffix.removeprefix(".").lower()

            if extension in ('svg','png','jpg','jpeg','gif','pdf'):
                format = extension
            else:
                raise ValueError(f"Cannot infer format from {filename}")

        #
        # We choose to pull the data back to Python for writing to the file in
        # order to have more predictable error handling.
        #

        data = self.to_rendered(
            program=program, format=format, dpi=dpi, size=size,
            ratio=ratio, timeout=timeout, directory=directory)

        mode = "xb" if exclusive else "wb"

        with open(filepath,mode) as f:
            f.write(data)

    def show(self, program="dot", *, format:str="svg",
             dpi:float|None=None, size:int|float|str|None=None,
             ratio:float|str|None=None, timeout:float|None=None,
             directory:str|PathLike|None=None) -> None:
        """
        Display the Dot object in a Jupyter notebook as an IPython ``SVG`` or
        ``Image`` object.  :meth:`show` generates the data required by invoking
        a Graphviz program.

        :raises ShowException: :meth:`show()` could not complete because the
            program could not be invoked, it timed out, or it exited with a
            non-zero status code.  When :meth:`show()` raises
            :class:`ShowException`, it also displays a ``Markdown`` block
            explaining why it could not complete.

        :raises RuntimeError: IPython is not installed.

        For the parameters, see :meth:`to_rendered`.  The ``size`` parameter
        can be especially useful: a value such as ``"5,5"`` can help ensure the
        graph visually fits in the notebook.  Note the default format for
        :meth:`show` is ``'svg'``.
        """
        if display and Markdown and SVG and Image:
            try:
                format = format.lower()
                data = self.to_rendered(
                    program=program, format=format, dpi=dpi, size=size,
                    ratio=ratio, timeout=timeout, directory=directory)
                if format == 'svg':
                    display(SVG(data))
                else:
                    display(Image(data))
            except InvocationException as ex:
                cause = ex.__cause__
                assert cause
                display(Markdown(_SHOW_BAD_INVOKE_HTML.format(
                    program=html_escape(program),
                    excl=html_escape(cause.__class__.__name__),
                    exmsg=html_escape(str(cause)))))
                raise ShowException() from None
            except ProcessException as ex:
                display(Markdown(s := _SHOW_BAD_EXIT_HTML.format(
                    program=html_escape(program),
                    status=html_escape(str(ex.status)),
                    stderr=html_escape(ex.stderr))))
                raise ShowException() from None
            except TimeoutException as ex:
                display(Markdown(_SHOW_TIMEOUT_HTML.format(
                    program=html_escape(program),
                    timeout=html_escape(str(timeout)))))
                raise ShowException() from None
        else:
            _missing_ipython()

    def show_source(self) -> None:
        """
        Display the Dot object's DOT language representation in a Jupyter
        notebook as an IPython ``Code`` object.

        :raises RuntimeError: IPython is not installed.
        """
        if display and Code:
            display(Code(str(self),language="graphviz"))
        else:
            _missing_ipython()


class InvocationException(Exception):
    """
    An attempt to run a Graphviz program failed.

    .. attribute:: program
        :type: str

        The program that could not be run.
    """

    def __init__(self, program:str):
        self.program = program

    def __str__(self):
        return "Could not run program " + self.program


class ProcessException(Exception):
    """
    A Graphviz program exited with a non-zero status code.

    .. attribute:: program
        :type: str

        The program that ran.

    .. attribute:: status
        :type: int

        The program's non-zero exit status code.

    .. attribute:: stderr
        :type: str

        Text the program wrote to stderr.
    """
    program : str
    status  : int
    stderr  : str
    def __init__(self, program:str, status:int, stderr:str|bytes):
        self.program = program
        self.status  = status
        self.stderr  = (stderr.decode(errors='replace')
                        if type(stderr) is bytes else stderr) #type:ignore

    def __str__(self):
        return f"Program {self.program} exited with status {self.status}"


class TimeoutException(Exception):
    """
    A Graphviz program timed out.

    .. attribute:: program
        :type: str

        The program that timed out.

    .. attribute:: timeout
        :type: float

        The timeout value.

    .. attribute:: stderr
        :type: str

        Text the program wrote to stderr before timing out.
    """
    program : str
    timeout : float
    stderr  : str
    def __init__(self, program:str, timeout:float, stderr:str|bytes):
        self.program = program
        self.timeout = timeout
        self.stderr  = (stderr.decode(errors='replace')
                        if type(stderr) is bytes else stderr) #type:ignore

    def __str__(self):
        return f"Program {self.program} timed out after {self.timeout} seconds"


class ShowException(Exception):
    """
    :meth:`Dot.show` could not complete.
    """
    def __init__(self):
        pass

    def __str__(self):
        return "show() could not complete"


#
# HTML blocks for show() errors.  These are displayed in Markdown objects --
# not HTML objects -- because we want to inherit the notebook's markdown
# styling.  Using HTML instead of templated markdown text both gives us more
# control and makes escaping easier.  <pre> tags also mean we need do nothing
# special to handle multiline stderr.
#

_SHOW_BAD_INVOKE_HTML = """
<div style="margin-top:1.2em; font-size:140%">
The program <code>{program}</code> could not be invoked:
<pre style="margin-left:4ex; font-size:75%">
{excl}: {exmsg}
</pre></div>
"""

_SHOW_BAD_EXIT_HTML = """
<div style="margin-top:1.2em; font-size:140%">
The program <code>{program}</code> exited with status <code>{status}</code>:
<pre style="margin-left:4ex; font-size:75%">
{stderr}
</pre></div>
"""

_SHOW_TIMEOUT_HTML = """
<div style="margin-top:1.2em; font-size:140%">
The program <code>{program}</code> timed out after {timeout} seconds.
</div>
"""
