"""
Make using Graphviz from Python convenient.
"""
from __future__ import annotations
from collections import defaultdict
import copy
from dataclasses import dataclass
from html import escape as html_escape
from os import PathLike
from pathlib import PurePath
import subprocess
from subprocess import CalledProcessError, TimeoutExpired
from typing import Any, Mapping
import re

__version__ = "0.9.2dev1"

__all__ = "Markup", "Port", "Dot", "InvocationException", "ShowException"

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
        "IPython is required to show dot objects. "
        "Install with: pip install gvdot[ipython]")


type ID = str|int|float|bool|Markup
"""
    Values corresponding to the DOT language non-terminal *ID* used for both
    entity identifiers and attribute values.  Consistent with the grammar,

    - using an int ``x`` as an :type:`ID` is equivalent to using ``str(x)``
    - using a float ``x`` as an :type:`ID` is equivalent to using ``str(x)``
    - using ``Markup(x)`` as an :type:`ID` is different that using ``x``

    For convenience, given that Graphviz uses ``true`` and ``false`` for
    boolean values,

    - using ``True`` as an :type:`ID` is equivalent to using ``"true"``
    - using ``False`` as an :type:`ID` is equivalent to using ``"false"``
"""

#
# Make sure the purported ID is in fact an ID and return its normalized
# representation (a string).  We do extra work to avoid quoting when we can, in
# the hope this aids readability of the DOT language generated.
#

_SIMPLE_ID_RE = re.compile(
    r"[a-zA-Z_][a-zA-Z0-9_]*|" +
    r"-?([.][0-9]+|[0-9]+([.][0-9]*)?)")

_RESERVED_IDS = {
    "strict", "graph", "digraph", "node", "edge", "subgraph"
}

_NEEDESCAPE_RE = re.compile(r'["\n\r\\]')

def _normalize(id:Any, what:str) -> str:
    match id:
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
# Graphs, nodes, and edges all have attributes.  While from the grammar an
# attribute can be any ID, all attributes supported by Graphviz have names that
# are lexically identifiers in Python, and through this API are specified via
# keyword parameter names.
#

type _Attrs = dict[str,str]

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
# Graphviz programs allow additional attributes to be specified on the command
# line.  Convert attrs into a list of -G, -N, and -E command line arguments.
#

def _attr_args(graph_attrs:Mapping[str,ID]|None=None,
               node_attrs:Mapping[str,ID]|None=None,
               edge_attrs:Mapping[str,ID]|None=None) -> list[str]:

    def add(kind:str, attrs:Mapping[str,ID]):
        for name, value in attrs.items():
            if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*",name):
                raise ValueError(
                    f"Bad invocation attribute name: {repr(name)}")
            args.append(f"-{kind}{name}={value}")

    args = []
    if graph_attrs: add("G",graph_attrs)
    if node_attrs: add("N",node_attrs)
    if edge_attrs: add("E",edge_attrs)
    return args

#
# Return the flattened attributes of the possibly role-bearing object.
#

def _resolve_role(attrs:_Attrs, roles:dict[str,_Attrs],
                  what:str, identity:Any):
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
# We prefer quoted strings for attribute values that are general text.
#

_TEXT_ATTRS = { "label", "headlabel", "taillabel", "xlabel", "comment" }

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

#
# Unique values used as implicit edge disciminants in the multi-graph case when
# none is provided by the application.
#

class _Nonce:

    counter = 0

    __slots__ = "seqno"

    def __init__(self):
        _Nonce.counter = (seqno := _Nonce.counter) + 1
        self.seqno = seqno

    def __hash__(self):
        return hash(-self.seqno)

    def __eq__(self, other):
        return type(other) is _Nonce and self.seqno == other.seqno

    def __repr__(self):
        return f"_Nonce<{self.seqno}>"

    def __deepcopy__(self, memo):
        return self

#
# We normalize discriminants to strings if they given as IDs, otherwise (when
# given as None) they are normalized to nonces for multigraphs and None for
# non-multigraphs.
#

type _NormDisc = str | _Nonce | None

#
# Identify nodes, edges, and subgraphs internally.  Node keys and subgraph keys
# are normalized IDs.  Edge keys are normalized (node1,node2,discriminant)
# triples.  For non-directed graphs, node1 <= node2.
#

type _NodeKey = str

type _EdgeKey = tuple[_NodeKey,_NodeKey,_NormDisc]

type _SubgraphKey = str

#
# Edges have port specifications and attributes, and can be directed.
#

class _Edge:
    __slots__ = "normport1", "normport2", "normdisc", "directed", "attrs"

    def __init__(self, dot:Dot, normport1:_NormPort, normport2:_NormPort,
                 normdisc:_NormDisc):
        self.normport1 = normport1
        self.normport2 = normport2
        self.normdisc = normdisc
        self.directed = dot.directed
        self.attrs:_Attrs = dict()

    def update_ports(self, otherport1:_NormPort, otherport2:_NormPort):
        if not otherport1.implicit:
            self.normport1 = otherport1
        if not otherport2.implicit:
            self.normport2 = otherport2

    def __repr__(self):
        return (f"_Edge<{self}>")

    #
    # DOT language representation.
    #

    def __str__(self):
        return (str(self.normport1) +
                (" -> " if self.directed else " -- ") +
                str(self.normport2))

    #
    # Used in exception messages.
    #

    def name(self):
        s = str(self)
        if self.normdisc is not None:
            s += " / " + str(self.normdisc)
        return s


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


_COMPASS_PT = { "n", "ne", "e", "se", "s", "sw", "w", "nw", "c" }


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
        return f"_NormPort<{str(self)}>"

    def __str__(self):
        result = self.node
        if (name := self.name) is not None:
            if name in _COMPASS_PT: name = _prefer_quoted(name)
            result += ":" + name
        if (cp := self.cp) is not None:
            result += ":" + cp
        return result

    def __deepcopy__(self, memo):
        return self


class Dot:
    """
    A DOT language graph expression.

    :param directed: The graph is a directed graph.

    :param strict: The graph declaration will include the ``strict`` keyword.
        This argument is present for completeness.  It's unlikely to be useful
        with dot objects since :class:`Dot` guarantees edge uniqueness for
        non-multigraphs.

    :param multigraph: Support multiple edges between the same node pair
        (ordered pair in the directed case.)  This parameter affects the
        behavior of methods :meth:`edge`, :meth:`edge_define`, and
        :meth:`edge_update` but does not change the DOT language produced from
        the dot object.

    :param id: The graph identifier.

    :param comment: Possibly multiline text prepended as a ``//`` style
        comment.

    :raises ValueError: If both ``strict`` and ``multigraph`` are requested.

    Except as otherwise described, dot object methods return self to enable
    chained method invocations.
    """
    __slots__ = (
        "directed", "strict", "multigraph", "graphid",
        "comment", "d_grapha", "d_nodea", "d_edgea",
        "grapha", "noderoles", "edgeroles", "graphroles",
        "nodemap", "edgemap", "subgraphmap", "nodes",
        "edges", "subgraphs", "_parent",
    )
    def __init__(self, *, directed:bool=False, strict:bool=False,
                 multigraph:bool=False, id:ID|None=None,
                 comment:str|None = None):

        if multigraph and strict:
            raise ValueError("Cannot specify both multigraph and strict")

        self.directed = directed
        self.strict = strict
        self.multigraph = multigraph
        self.graphid:str|None = (None if id is None else
                                 _normalize(id, "Graph identifier"))
        self.comment = comment
        self.d_grapha:_Attrs = dict()
        self.d_nodea:_Attrs = dict()
        self.d_edgea:_Attrs = dict()
        self.grapha:_Attrs = dict()
        self.graphroles:dict[str,_Attrs] = defaultdict(dict)
        self.noderoles:dict[str,_Attrs] = defaultdict(dict)
        self.edgeroles:dict[str,_Attrs] = defaultdict(dict)
        self.nodemap:dict[_NodeKey,_Attrs] = defaultdict(dict)
        self.edgemap:dict[_EdgeKey,_Edge] = dict()
        self.subgraphmap:dict[_SubgraphKey,Dot] = dict()
        self.nodes:list[_NodeKey] = []
        self.edges:list[_Edge] = []
        self.subgraphs:list[Dot] = []
        self._parent:Dot|None = None

    def is_multigraph(self) -> bool:
        """
        Return True iff this is a multigraph dot object.
        """
        return self.multigraph

    def graph_default(self, **attrs:ID|None) -> Dot:
        """
        Specify or amend default graph attributes.
        """
        _set_attrs(self.d_grapha,attrs)
        return self

    def graph_role(self, role:str, /, **attrs:ID|None) -> Dot:
        """
        Define a graph role or amend its attributes.
        """
        _set_attrs(self.graphroles[_normalize(role,"Role name")],attrs)
        return self

    def graph(self, **attrs:ID|None) -> Dot:
        """
        Specify or amend the graph's attributes.
        """
        _set_attrs(self.grapha,attrs,True)
        return self

    def node_default(self, **attrs:ID|None) -> Dot:
        """
        Specify or amend default node attributes.
        """
        _set_attrs(self.d_nodea,attrs)
        return self

    def node_role(self, role:ID, /, **attrs:ID|None) -> Dot:
        """
        Define a node role or amend its attributes.
        """
        _set_attrs(self.noderoles[_normalize(role,"Role name")],attrs)
        return self

    def node(self, id:ID, /, **attrs:ID|None) -> Dot:
        """
        Define a node or amend its attributes.

        :param id: The node's identifier.

        :param attrs: New or amending attribute value assignments.
        """
        key = _normalize(id, "Node identifier")
        if key not in self.nodemap:
            self.nodes.append(key)
        _set_attrs(self.nodemap[key],attrs,True)
        return self

    def node_define(self, id:ID, /, **attrs:ID|None) -> Dot:
        """
        Same as method :meth:`node`, except require the node to be undefined.

        :raises RuntimeError: The node is already defined.
        """
        key = _normalize(id, "Node identifier")
        if key in self.nodemap:
            raise RuntimeError(f"Node {key} already defined")
        self.nodes.append(key)
        _set_attrs(self.nodemap[key],attrs,True)
        return self

    def node_update(self, id:ID, /, **attrs:ID|None) -> Dot:
        """
        Same as method :meth:`node`, except require the node to be defined.

        :raises RuntimeError: The node is not defined.
        """
        key = _normalize(id, "Node identifier")
        if key not in self.nodemap:
            raise RuntimeError(f"Node {key} not defined")
        _set_attrs(self.nodemap[key],attrs,True)
        return self

    def node_is_defined(self, id:ID) -> bool:
        """
        Return True iff the identified node is defined.
        """
        return _normalize(id, "Node identifier") in self.nodemap

    def edge_default(self, **attrs:ID|None) -> Dot:
        """
        Specify or amend default edge attributes.
        """
        _set_attrs(self.d_edgea,attrs)
        return self

    def edge_role(self, role:str, /, **attrs:ID|None) -> Dot:
        """
        Define an edge role or amend its attributes.
        """
        _set_attrs(self.edgeroles[_normalize(role,"Role name")],attrs)
        return self

    def _edge_preamble(self, point1:ID|Port, point2:ID|Port,
                       discriminant:ID|None
                       ) -> tuple[_EdgeKey, _NormPort, _NormPort, _NormDisc]:
        """
        Implement the common preamble of all edge identity based methods.
        """
        normport1 = _NormPort(point1)
        normport2 = _NormPort(point2)

        if discriminant is not None:
            if not self.multigraph:
                raise ValueError(
                    "Discriminant must be None for non-multigraphs")
            normdisc = _normalize(discriminant,"Edge discriminant")
        elif self.multigraph:
            normdisc = _Nonce()
        else:
            normdisc = None

        node1 = normport1.node
        node2 = normport2.node

        if self.directed or node1 <= node2:
            key = (node1,node2,normdisc)
        else:
            key = (node2,node1,normdisc)

        return key, normport1, normport2, normdisc

    def _edge(self, point1:ID|Port, point2:ID|Port,
              discriminant:ID|None, attrargs:dict[str,Any],
              must_exist=False, must_not_exist=False) -> Dot:
        """
        Define or amend an edge, enforcing defined/not-defined constraints.
        """
        key, normport1, normport2, normdisc = self._edge_preamble(
            point1,point2,discriminant)

        if (edge := (edgemap := self.edgemap).get(key)) is None:
            edge = _Edge(self,normport1,normport2,normdisc)
            if must_exist:
                if self.multigraph:
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
             discriminant:ID|None=None, /, **attrs:ID|None) -> Dot:
        """
        Define an edge or amend its attributes and port specifications.

        :param point1: The first edge endpoint, either a node identifier or a
            port.  In the directed case, this is the source of the arc.

        :param point2: The second edge endpoint, either a node identifier or a
            port.  In the directed case, this is the destination of the arc.

        :param discriminant: A value allowing the application to refer to
            specific edges created in a multigraph.  A discriminant may only be
            provided for multigraphs, but are not required for multigraphs.  If
            provided, discriminants need only be unique among edges of their
            associated node pair.  Discriminants do not appear in the DOT
            language representation.

        :param attrs: New or amending attribute value assignments.

        Consistent with the DOT language, only the ``id`` portion of a
        :class:`Port` is relevant to edge identification.  In the code below,
        the first statement defines an edge, and the second amends the same
        edge's attributes.

        .. code-block:: python

            dot = Dot()
            dot.edge(Port("a",cp="n"), Port("b","output","s"), color="blue")
            dot.edge("a","b",style="dashed")

        The outcome of calling :meth:`edge` with the endpoint node IDs of an
        already defined edge depends on the constructor ``multigraph`` parameter
        and whether or not a discriminant is specified.

        - Non-multigraph: the defined edge is amended.
        - Multigraph, no discriminant: a new edge is defined
        - Multigraph, distinct discriminant: a new edge is defined
        - Multigraph, same discriminant: the defined edge is amended

        When amending an edge, if an endpoint argument is a :class:`Port`, that
        specification replaces the endpoint's previous specification (if any).
        For example, the DOT representation of

        .. code-block:: python

            dot = Dot()
            dot.edge(Port("a", cp="s"), Port("b", cp="s"))
            dot.edge(Port("a", cp="n"), "b")

        includes the edge ``a:n -- b:s``.

        As in DOT, edge endpoint nodes need not be defined.  The output of

        .. code-block:: python

            dot = Dot()
            dot.edge("a","b",label="An example edge")
            print(dot,file=output_file)

        will include an edge statement, but no node statements.
        """
        return self._edge(point1,point2,discriminant,attrs)

    def edge_define(self, point1:ID|Port, point2:ID|Port,
                    discriminant:ID|None=None, /, **attrs:ID|None) -> Dot:
        """
        Same as method :meth:`edge`, except require the edge to be undefined.

        :raises RuntimeError: The edge is already defined.
        """
        return self._edge(point1,point2,discriminant,attrs,must_not_exist=True)

    def edge_update(self, point1:ID|Port, point2:ID|Port,
                    discriminant:ID|None=None, /, **attrs:ID|None) -> Dot:
        """
        Same as method :meth:`edge`, except require the edge to be defined.

        :raises RuntimeError: The edge is not defined.
        """
        return self._edge(point1,point2,discriminant,attrs,must_exist=True)

    def edge_is_defined(self, point1:ID|Port, point2:ID|Port,
                        discriminant:ID|None=None) -> bool:
        """
        Return True iff the identified edge is defined.
        """
        key, _, _, _ = self._edge_preamble(point1,point2,discriminant)
        return key in self.edgemap

    def subgraph(self, id:ID|None=None) -> Dot:
        """
        Define or prepare to amend a subgraph.

        :param id: The subgraph identifier.

        :return: A new or existing child dot object.  Graph attributes,
            attribute defaults, and nodes and edges defined through the child
            will appear within a subgraph statement of the root dot object's
            DOT language representation.

        :raises ValueError: A subgraph with that identity is already defined.

        In DOT, node identifiers are scoped to the root graph, so nodes and
        edges cannot be redefined within a child.  Also, nodes and edge
        attributes can be amended through any dot object in the hierarchy,
        regardless of the dot object through which they were defined.

        Roles are similarly scoped to the root graph.  Role specifications or
        amendments made through a subgraph dot object are visible throughout
        the graph.

        Subgraphs, on the other hand, are scoped to their parent.  So, the
        assertions below all hold.

        .. code:: python

            dot = Dot()
            sub1 = dot.subgraph(id="sub1")
            sub1_sub2 = sub1.subgraph(id="sub2")
            assert dot.subgraph(id="sub1") is sub1
            assert sub1.subgraph(id="sub2") is sub1_sub2
            assert dot.subgraph(id="sub2") is not sub1_sub2
        """
        if id is not None:
            key = _normalize(id, "Subgraph identifier")
            if (subdot := self.subgraphmap.get(key)) is not None:
                return subdot
        #
        # Here we have a Python weakness on display: no multiple constructors
        # means no clean way to have the child constructed differently.  We
        # choose to perform surgery on the child after construction rather than
        # pollute Dot's public constructor.  Note we do not replace
        # subgraphmap, since subgraphs are scoped to their parent.
        #
        subdot = Dot(directed=self.directed, strict=self.strict,
                     multigraph=self.multigraph, id=id)
        subdot.nodemap = self.nodemap
        subdot.edgemap = self.edgemap
        subdot.noderoles = self.noderoles
        subdot.edgeroles = self.edgeroles
        subdot.graphroles = self.graphroles
        subdot._parent = self
        self.subgraphs.append(subdot)
        if id is not None:
            self.subgraphmap[key] = subdot
        return subdot

    def subgraph_define(self, id:ID) -> Dot:
        """
        Same as :meth:`subgraph`, except require the subgraph to be
        undefined.

        :raises RuntimeError: The subgraph is already defined.
        """
        key = _normalize(id,"Subgraph identifier")
        if key in self.subgraphmap:
            raise RuntimeError(f"Subgraph {key} already defined")
        return self.subgraph(id)

    def subgraph_update(self, id:ID) -> Dot:
        """
        Same as :meth:`subgraph`, except require the subgraph to be
        defined.

        :raises RuntimeError: The subgraph is not defined.
        """
        key = _normalize(id,"Subgraph identifier")
        if key not in self.subgraphmap:
            raise RuntimeError(f"Subgraph {key} not defined")
        return self.subgraph(id)

    def subgraph_is_defined(self, id:ID) -> bool:
        """
        Return True iff the identified subgraph is defined.
        """
        return _normalize(id,"Subgraph identifier") in self.subgraphmap

    def all_default(self, **attrs:ID|None) -> Dot:
        """
        Specify or amend default graph, node, and edge attributes all at once.

        Executing ``dot.all_default(**attrs)`` has the same effect as executing

        .. code-block:: python

            dot.graph_default(**attrs)
            dot.node_default(**attrs)
            dot.edge_default(**attrs)
        """
        _set_attrs(self.d_grapha,attrs)
        _set_attrs(self.d_nodea,attrs)
        _set_attrs(self.d_edgea,attrs)
        return self

    def all_role(self, role:str, /, **attrs:ID|None) -> Dot:
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

    def parent(self) -> Dot|None:
        """
        The dot object's parent if the object is a subgraph, otherwise None if
        the dot object is a root.
        """
        return self._parent

    def copy(self, *, id:ID|None=None, comment:str|None=None) -> Dot:
        """
        Return a deep copy of the dot object.

        :param id: The copy's graph identifier.  If not provided, the copy will
            have this graph's identifier.

        :param comment: The copy's comment.  If not provided, the copy will
            have this graph's comment.
        """
        result = copy.deepcopy(self)
        if id is not None:
            result.graphid = _normalize(id,"Graph identifier")
        if comment is not None:
            result.comment = comment
        return result

    def use_theme(self, source:Dot) -> Dot:
        """
        Incorporate another dot object's graph, default graph, default node,
        default edge, and role attributes.

        :param source: The attribute source.

        If an attribute in ``source`` already has a value in this graph, this
        graph's value prevails.
        """
        def incorporate_attrs(target:_Attrs, source:_Attrs):
            for key, value in source.items():
                if key not in target:
                    target[key] = value

        def incorporate_roles(target:dict[str,_Attrs],
                              source:dict[str,_Attrs]):
            for role, role_attrs in source.items():
                if role in target:
                    incorporate_attrs(target[role],role_attrs)
                else:
                    target[role] = role_attrs.copy()

        incorporate_attrs(self.d_grapha,source.d_grapha)
        incorporate_attrs(self.d_nodea,source.d_nodea)
        incorporate_attrs(self.d_edgea,source.d_edgea)
        incorporate_attrs(self.grapha,source.grapha)
        incorporate_roles(self.graphroles,source.graphroles)
        incorporate_roles(self.noderoles,source.noderoles)
        incorporate_roles(self.edgeroles,source.edgeroles)

        return self

    def _statements(self, lines:list[str], indent:int):
        """
        Append the dot object's statements to lines, indented as specified.
        """
        prefix = "    " * indent
        base = len(lines)
        blanklines = 0

        def statement(s:str, attrs:_Attrs|None):
            s = prefix + s
            if attrs:
                pieces = []
                for key, value in attrs.items():
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
        if d_grapha := self.d_grapha: statement("graph",d_grapha)
        if d_nodea  := self.d_nodea:  statement("node",d_nodea)
        if d_edgea  := self.d_edgea:  statement("edge",d_edgea)

        graphroles = self.graphroles
        noderoles  = self.noderoles
        edgeroles  = self.edgeroles
        nodemap    = self.nodemap
        graphid    = self.graphid
        grapha     = _resolve_role(self.grapha,graphroles,"graph",graphid)

        blankline()
        for key, value in grapha.items():
            if key != "label":
                if key in _TEXT_ATTRS:
                    value = _prefer_quoted(value)
                statement(f"{key}={value}",None)

        blankline()
        for nodekey in self.nodes:
            attrs = _resolve_role(nodemap[nodekey],noderoles,"node", nodekey)
            statement(nodekey,attrs)

        blankline()
        for edge in self.edges:
            attrs = _resolve_role(edge.attrs,edgeroles,"edge", edge)
            statement(str(edge),attrs)

        for subgraph in self.subgraphs:
            blankline()
            lines.append(prefix + "subgraph " +
                         ("" if subgraph.graphid is None
                          else subgraph.graphid + " ") + "{") #type:ignore
            subgraph._statements(lines,indent+1)
            lines.append(prefix + "}")

        if "label" in grapha:
            blankline()
            statement(f"label={_prefer_quoted(grapha['label'])}",None)

        if not lines[-1]:
            lines.pop()
            blanklines -= 1

        if len(lines) - base - blanklines <= 8 or blanklines == 1:
            lines[base:] = [ line for line in lines[base:] if line ]

    def __str__(self) -> str:
        """
        The DOT language representation of the dot object.
        """
        lines = []

        if comment := self.comment:
            for commentline in comment.splitlines():
                lines.append("// " + commentline)
            lines.append("")

        lines.append(("strict " if self.strict else "") +
                     ("digraph " if self.directed else "graph ") +
                     ("" if self.graphid is None else
                      self.graphid + " ") + #type:ignore
                     "{")

        self._statements(lines,1)

        lines.append("}\n")

        return '\n'.join(lines)

    def _run_program(self, text:bool, program:str,
                     directory:str|PathLike|None, timeout:float|None,
                     t_arg:str, graph_attrs:Mapping[str,ID]|None,
                     node_attrs:Mapping[str,ID]|None,
                     edge_attrs:Mapping[str,ID]|None) -> str|bytes:
        """
        Run a Graphviz program.
        """
        input = str(self)

        if not text:
            input = input.encode()

        if directory is not None:
            program = str(PurePath(directory,program))

        command = [ program, t_arg,
                    *_attr_args(graph_attrs, node_attrs, edge_attrs) ]

        try:
            completed = subprocess.run(
                command, input=input, capture_output=True,
                text=text, timeout=timeout, check=True)
        except BaseException as ex:
            if isinstance(ex,CalledProcessError):
                raise
            elif isinstance(ex,TimeoutExpired):
                raise
            else:
                raise InvocationException(program) from ex

        return completed.stdout

    def to_svg(self, program="dot", *, inline=False,
               directory:str|PathLike|None=None,
               timeout:float|None=None,
               graph_attrs:Mapping[str,ID]|None=None,
               node_attrs:Mapping[str,ID]|None=None,
               edge_attrs:Mapping[str,ID]|None=None) -> str:
        """
        Convert the dot object to an SVG string by invoking a Graphviz program
        through the subprocess module.

        :param program: Which Graphviz program to use (dot by default).

        :param inline: Generate SVG without an XML header.

        :param directory: Where to find the program executable.  If not
            specified, the program must be found on the process's ``PATH``.

        :param timeout: Limit the program execution time to this many seconds.

        :param graph_attrs: Additional graph attribute values to pass to the
            program on the command line via the ``-G`` option.

        :param node_attrs: Additional node attribute values to pass to the
            program on the command line via the ``-N`` option.

        :param edge_attrs: Additional edge attribute values to pass to the
            program on the command line via the ``-E`` option.

        :return: An SVG string.

        :raises InvocationException: Could not invoke the program, likely
            because it wasn't found.

        :raises subprocess.CalledProcessError: The invoked program exited with
            a non-zero status code.  :class:`~subprocess.CalledProcessError`
            objects include the status code, stdout, and stderr of the program
            as properties.

        :raises subprocess.TimeoutExpired: The invoked program took longer than
            ``timeout`` seconds to run and was killed.

        Example:

        .. code-block:: python

            from IPython.display import display, SVG
            dot = Dot()
            dot.edge("a","b",label="Render")
            dot.edge("b","c",label="as")
            dot.edge("c","a",label="SVG")
            display(SVG(dot.to_svg()))
        """
        t_arg = "-Tsvg_inline" if inline else "-Tsvg"

        stdout = self._run_program(True, program, directory, timeout, t_arg,
                                   graph_attrs, node_attrs, edge_attrs)

        assert type(stdout) is str

        return stdout

    def to_rendered(self, program="dot", *, format="png",
                    timeout:float|None=None,
                    directory:str|PathLike|None=None,
                    graph_attrs:Mapping[str,ID]|None=None,
                    node_attrs:Mapping[str,ID]|None=None,
                    edge_attrs:Mapping[str,ID]|None=None) -> bytes:
        """
        Render the dot object by invoking a Graphviz program through the
        subprocess module.

        :param program: Which Graphviz program to use (dot by default).

        :param format: The output format desired (png by default).
            :meth:`to_rendered` uses the value of ``format`` to form the ``-T``
            argument to the specified program.

        :param directory: Where to find the program executable.  If not
            specified, the program must be found on the process's ``PATH``.

        :param timeout: Limit the program execution time to this many seconds.

        :param graph_attrs: Additional graph attribute values to pass to the
            program on the command line via the ``-G`` option.

        :param node_attrs: Additional node attribute values to pass to the
            program on the command line via the ``-N`` option.

        :param edge_attrs: Additional edge attribute values to pass to the
            program on the command line via the ``-E`` option.

        :return: The output bytes of the specified program.

        :raises InvocationException: Could not invoke the program, likely
            because it wasn't found.

        :raises subprocess.CalledProcessError: The invoked program exited with
            a non-zero status code.  :class:`~subprocess.CalledProcessError`
            objects include the status code, stdout, and stderr of the program
            as properties.

        :raises subprocess.TimeoutExpired: The invoked program took longer than
            ``timeout`` seconds to run and was killed.

        Example:

        .. code-block:: python

            dot = Dot().graph(dpi=300)
            dot.edge("a","b",label="Render")
            dot.edge("b","c",label="as")
            dot.edge("c","a",label="image")
            with open("example.png","wb") as f:
                f.write(dot.to_rendered())
        """
        t_arg = f"-T{format}"

        stdout = self._run_program(False, program, directory, timeout, t_arg,
                                   graph_attrs, node_attrs, edge_attrs)

        assert type(stdout) is bytes

        return stdout

    def show(self, program="dot", *,
             format:str="svg", size:str|None=None,
             directory:str|PathLike|None=None,
             timeout:float|None=None,
             graph_attrs:Mapping[str,ID]|None=None,
             node_attrs:Mapping[str,ID]|None=None,
             edge_attrs:Mapping[str,ID]|None=None) -> None:
        """
        Display the dot object in a Jupyter notebook as an SVG or Image object.
        :meth:`show` generates the SVG or Image data by invoking a Graphviz program
        through the subprocess module.

        :param program: Which Graphviz program to use (dot by default).

        :param format: The output format desired (svg by default).  If the
            format is "svg" (upper, lower, or mixed case), :meth:`show` will
            generate SVG and display a ``IPython.display.SVG`` object.
            Otherwise, :meth:`show` will generate image data and display a
            ``IPython.display.Image`` object.

        :param size: Add a size attribute to the graph before rendering.  A
            value such as ``"5,5"`` can help ensure the graph visually fits in
            the notebook.

        :param directory: Where to find the program executable.  If not
            specified, the program must be found on the process's ``PATH``.

        :param timeout: Limit the program execution time to this many seconds.

        :param graph_attrs: Additional graph attribute values to pass to the
            program on the command line via the ``-G`` option.  If parameter
            ``size`` is also specified, and ``graph_attrs`` contains a ``size``
            entry, that entry is overwritten with the ``size`` parameter value.

        :param node_attrs: Additional node attribute values to pass to the
            program on the command line via the ``-N`` option.

        :param edge_attrs: Additional edge attribute values to pass to the
            program on the command line via the ``-E`` option.

        :raises ShowException: :meth:`show()` could not complete because the
            program could not be invoked, it timed out, or it exited with a
            non-zero status code.  When :meth:`show()` raises
            :class:`ShowException`, it also displays a Markdown block
            explaining why it could not complete.

        :raises RuntimeError: IPython is not installed.
        """
        if display and Markdown and SVG and Image:
            if size is not None:
                d = dict()
                if graph_attrs is not None: d.update(graph_attrs)
                d['size'] = size
                graph_attrs = d
            try:
                if format is not None and format.lower() == 'svg':
                    display(SVG(self.to_svg(
                        program=program, timeout=timeout, directory=directory,
                        graph_attrs=graph_attrs, node_attrs=node_attrs,
                        edge_attrs=edge_attrs)))
                elif format is not None:
                    display(Image(self.to_rendered(
                        program=program, timeout=timeout, directory=directory,
                        graph_attrs=graph_attrs, node_attrs=node_attrs,
                        edge_attrs=edge_attrs)))
            except InvocationException as ex:
                cause = ex.__cause__
                assert cause
                display(Markdown(_SHOW_BAD_INVOKE_HTML.format(
                    program=html_escape(program),
                    excl=html_escape(cause.__class__.__name__),
                    exmsg=html_escape(str(cause)))))
                raise ShowException() from None
            except CalledProcessError as ex:
                stderr = ex.stderr
                if type(stderr) is bytes:
                    stderr = stderr.decode()
                display(Markdown(s := _SHOW_BAD_EXIT_HTML.format(
                    program=html_escape(program),
                    status=html_escape(str(ex.returncode)),
                    stderr=html_escape(stderr))))
                raise ShowException() from None
            except TimeoutExpired as ex:
                display(Markdown(_SHOW_TIMEOUT_HTML.format(
                    program=html_escape(program),
                    timeout=html_escape(str(timeout)))))
                raise ShowException() from None
        else:
            _missing_ipython()

    def show_source(self) -> None:
        """
        Display the dot object's DOT language representation in a Jupyter
        notebook as a ``IPython.display.Code`` object.
        """
        if display and Code:
            display(Code(str(self),language="graphviz"))
        else:
            _missing_ipython()


class InvocationException(BaseException):
    """
    An attempt to run a Graphviz program failed.

    .. attribute:: program
        :type: str

        The program that could not be run.
    """

    def __init__(self, program:str):
        self.program = program

    def __str__(self):
        return f"Could not run program " + self.program


class ShowException(BaseException):
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
