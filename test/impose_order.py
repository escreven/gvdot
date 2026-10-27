from __future__ import annotations
from datetime import datetime, timezone
import os
import re
import lzma
import json
from random import Random
from itertools import combinations
from collections import defaultdict
from dataclasses import replace
from typing import Iterable, Iterator
from gvdot import Dot, Port, _impose, impose_order, _AVAILABLE_VERSIONS
from utility import expect_ex, parse, svg_parse, svg_dimensions
from utility import GraphLine, DotLine, NodeLine, EdgeLine
from utility import SubgraphLine, EndLine, EdgeDAttrLine

#
# Multigraphs can have multiple identical edges, and for tests below, the
# cardinality of those identical edges matters.  If EdgeLine were hashable, an
# alternative would be class Counter.
#

class _EdgeBag(list[EdgeLine]):

    def __eq__(self, other) -> bool:
        if not isinstance(other,_EdgeBag):
            return False
        if len(self) != len(other):
            return False
        other = other.copy()
        for line1 in self:
            for j, line2 in enumerate(other):
                if line1 == line2:
                    del other[j]
                    break
            else:
                return False
        return True

    def __ne__(self,other) -> bool:
        return not self.__eq__(other)

#
# Extract the node portion of an endpoint string.  Tests are not allowed to
# have quoted node names or HTML node names.
#

def _endpoint_node(endpoint:str):
    return endpoint.split(':',maxsplit=1)[0]

#
# Parse a dot object's DOT lines into a body with node and edge statements
# removed, a located node dictionary, and a located edge dictionary.
#
# A location is a tuple expressing where in the DOT language an entity appears
# structurally.  () means at the top.  ('a','b') means in subgraph b under
# subgraph 'a'.  If a subgraph does not have a graph id, it is assigned an
# integer identifier based on appearance order in the DOT language.  That means
# for these tests, subgraph IDs must not be explicitly given as an integer.
#

type _Location = tuple[str,...]
type _LocNodeDict = dict[tuple[_Location,str,],NodeLine]
type _LocEdgeDict = dict[tuple[_Location,str,str],_EdgeBag]

def _separate(lines:list[DotLine]) -> tuple[
        list[DotLine],_LocNodeDict,_LocEdgeDict]:

    body     = list[DotLine]()
    nodes    = dict()
    edges    = defaultdict(_EdgeBag)
    location = list[str]()
    anon_id  = 0

    for line in lines:
        match line:
            case SubgraphLine(graphid):
                if graphid is None:
                    anon_id += 1
                    graphid = str(anon_id)
                location.append(graphid)
                body.append(line)

            case EndLine():
                if location:
                    location.pop()
                body.append(line)

            case NodeLine(nodeid):
                nodes[tuple(location),nodeid] = line

            case EdgeLine(endpoint1,endpoint2):
                node1 = _endpoint_node(endpoint1)
                node2 = _endpoint_node(endpoint2)
                edges[tuple(location),node1,node2].append(line)

            case _:
                body.append(line)

    return body, nodes, edges

#
# Normalize the orientation of the given edges, including clearing the
# directed flag.  Normalizing the orientation of undirected edges is not a
# noop; undirected endpoints still have a textual order.
#

def _normalize_orientation(edges:_LocEdgeDict) -> _LocEdgeDict:

    result:_LocEdgeDict = dict()
    for (loc, _, _), lines in edges.items():
        newlines = _EdgeBag()
        for line in lines:
            node1 = _endpoint_node(line.endpoint1)
            node2 = _endpoint_node(line.endpoint2)
            if node1 > node2:
                node1, node2 = node2, node1
                newline = replace(line,
                                  endpoint1=line.endpoint2,
                                  endpoint2=line.endpoint1,
                                  directed=False)
            else:
                newline = replace(line, directed=False)
            newlines.append(newline)
        existing = result.get((loc,node1,node2))
        if existing is not None:
            existing.extend(newlines)
        else:
            result[loc, node1, node2] = newlines

    return result

#
# Find the GraphLine.  (It might not be first -- it can follow comments).
#

def _graph_line(lines:list[DotLine]) -> GraphLine:
    for line in lines:
        match line:
            case GraphLine():
                return line
    raise AssertionError("Body has no GraphLine")

#
# Find and return the arrowhead attribute value in the top-level default edge
# attributes, deleting that arrowhead attribute if found.
#

def _pop_arrowhead(lines:list[DotLine]):
    level = 0
    for i, line in enumerate(lines):
        match line:
            case SubgraphLine():
                level += 1
            case EndLine():
                level -= 1
            case EdgeDAttrLine(attrs):
                if level == 0:
                    if (value := attrs.pop('arrowhead',None)) is not None:
                        if not attrs:
                            del lines[i]
                        return value
    return None

#
# When multigraph is False, raise AssertionError unless there is exactly one
# EdgeLine with the specified endpoints and that EdgeLine has the given
# attributes.
#
# When multigraph is True, raise AssertionError unless there is at least one
# EdgeLine with the specified endpoints and given attributes.
#

def _require_edge_attrs(lines:list[DotLine], endpoint1:str, endpoint2:str,
                        attrs:dict[str,str], multigraph=False):
    found_endpoints = False
    found_attrs = False

    for line in lines:
        if (type(line) is EdgeLine
                and line.endpoint1 == endpoint1
                and line.endpoint2 == endpoint2):
            if not multigraph:
                assert not found_endpoints
            found_endpoints = True
            if line.attrs == attrs:
                found_attrs = True
            elif not multigraph:
                raise AssertionError(
                    f"For {endpoint1}->{endpoint2} found {line.attrs} "
                    f"expected {attrs}")

    assert found_endpoints, (
        f"Found no edge for {endpoint1}->{endpoint2}")

    assert found_attrs, (
        f"Found no {endpoint1}->{endpoint2} with {attrs} ")

#
# Strip order sensitive edge attributes.
#

def _remove_keys(attrs:dict[str,str], keys:Iterable[str]) -> bool:
    any = False
    for name in keys:
        if name in attrs:
            del attrs[name]
            any = True
    return any

_OSA = (
    'arrowhead', 'arrowtail',
    'headclip', 'tailclip',
    'headhref', 'tailhref',
    'headlabel', 'taillabel',
    'headport', 'tailport',
    'headtarget', 'tailtarget',
    'headtooltip', 'tailtooltip',
    'headURL', 'tailURL',
    'lhead', 'ltail',
    'samehead', 'sametail',
    'dir')

def _strip_osa(lines:list[DotLine], dattr_allowed=True) -> None:
    index = 0
    while index < len(lines):
        line = lines[index]
        match line:
            case EdgeDAttrLine(attrs):
                if _remove_keys(attrs,_OSA):
                    assert dattr_allowed, (
                        f"Found order sensitive attribute in {line}")
                    if not attrs:
                        del lines[index]
                    continue
            case EdgeLine(attrs=attrs):
                _remove_keys(attrs,_OSA)
        index += 1

#
# Require odot to be a directed analogue of dot.
#
# IMPORTANT: Order sensitive attributes are not compared, though _require_da()
# does require odot to have no order sensitive default attributes other than a
# required arrowhead='none'.
#

def _require_da(dot:Dot, odot:Dot, arrowhead:str|None='none'):

    dot_lines = parse(str(dot))
    odot_lines = parse(str(odot))

    #
    # dot must be undirected, while odot must be directed.
    #

    dot_graph_line = _graph_line(dot_lines)
    odot_graph_line = _graph_line(odot_lines)
    assert not dot_graph_line.directed
    assert odot_graph_line.directed

    #
    # odot's default arrowhead
    #

    odot_arrowhead = _pop_arrowhead(odot_lines)
    assert odot_arrowhead == arrowhead

    #
    # Strip order sensitive edge attributes.
    #

    _strip_osa(dot_lines)
    _strip_osa(odot_lines, dattr_allowed=False)

    #
    # Separate out nodes and edges.
    #

    dot_body, dot_nodes, dot_edges = _separate(dot_lines)
    odot_body, odot_nodes, odot_edges = _separate(odot_lines)

    #
    # The bodies (except the directed flag), located nodes, and orientation
    # normalized located edges must be identical.
    #

    odot_graph_line.directed = False
    if dot_body != odot_body:
        print("Bodies not equal.")
        print()
        for line in dot_body:
            print(line)
        print()
        for line in odot_body:
            print(line)
        print()
        raise AssertionError("Mismatched bodies")

    if dot_nodes != odot_nodes:
        print("Nodes not equal.")
        print()
        for node in dot_nodes:
            print(node)
        print()
        for node in odot_nodes:
            print(node)
        print()
        raise AssertionError("Mismatched nodes")

    norm_dot_edges = _normalize_orientation(dot_edges)
    norm_odot_edges = _normalize_orientation(odot_edges)

    if norm_dot_edges != norm_odot_edges:
        print("Edges not equal.")
        print()
        for key, value in norm_dot_edges.items():
            print(f"{key}: {value}")
        print()
        for key, value in norm_odot_edges.items():
            print(f"{key}: {value}")
        print()
        raise AssertionError("Mismatched edges")

    #
    # All arcs between the same pair of nodes must have the same direction.
    # (Self-loops are excluded from set arcs because loops don't have a
    # direction.)
    #

    arcs = set((node1,node2)
               for lines in odot_edges.values()
               for line in lines
               if (node1 := _endpoint_node(line.endpoint1)) !=
                  (node2 := _endpoint_node(line.endpoint2)))

    for lines in odot_edges.values():
        for line in lines:
            assert (_endpoint_node(line.endpoint2),
                    _endpoint_node(line.endpoint1)) not in arcs, (
                        f"Inconsistent direction for {line}")

#
# Return a measure of a Dot object's rendered non-squareness.
#

def _elongation(dot:Dot) -> float:
    svg = svg_parse(dot.to_svg())
    width, height, _ = svg_dimensions(svg)
    ratio = width / height
    return ratio if ratio >= 1.0 else 1 / ratio

#
# Return the edges of a random graph with nodes 0..node_count-1 and edge_count
# non-self connections, where a connection is 1..max_parallel edges.  Requires
# Theta(node_count^2) time.
#
# NOTE: We use our own shuffle because only Random.random() is guaranteed to be
# stable across Python versions.
#

def _random_graph(node_count:int, edge_count:int, seed:int,
                  max_parallel:int=1) -> list[tuple[int,int]]:

    if edge_count == 0:
        return []

    rand = Random(seed)
    need = edge_count
    outof = node_count * (node_count - 1) // 2
    edges = []

    def _shuffle():
        n = len(edges)
        for i in range(n-1):
            j = i + int((n - i) * rand.random())
            edges[i], edges[j] = edges[j], edges[i]

    for node1 in range(node_count-1):
        for node2 in range(node1+1, node_count):
            if rand.random() < (need / outof):
                for _ in range(1 + int(max_parallel * rand.random())):
                    edges.append((node1,node2))
                need -= 1
                if need == 0:
                    _shuffle()
                    return edges
            outof -= 1

    assert False


def test_directed_not_allowed():
    """
    Directed Dot object input is not allowed.
    """
    dot = Dot(directed=True)
    expect_ex(ValueError,lambda: impose_order(dot))


def test_version_available():
    """
    Specifying an unavailable version should raise ValueError.
    """
    dot = Dot()
    for version in range(min(_AVAILABLE_VERSIONS)-1,
                         max(_AVAILABLE_VERSIONS)+2):
        if version in _AVAILABLE_VERSIONS:
            impose_order(dot,version=version)
        else:
            expect_ex(ValueError,lambda: impose_order(dot,version=version))


def test_empty():
    """
    Order may be imposed on empty graphs.
    """
    dot = Dot()
    _require_da(dot,impose_order(dot))

    dot = Dot(id="Empty", comment="As you wish.")
    dot.graph(orientation=45, label="Empty Graph")
    dot.graph_default(bgcolor="blue")
    dot.node_default(shape="circle")
    dot.edge_default(penwidth=1.5)
    subdot = dot.subgraph()
    subdot.graph(color="red")
    subsubdot = subdot.subgraph("Nested")
    subsubdot.node_default(shape="square")
    _require_da(dot,impose_order(dot))


def test_hide_arrow():
    """
    Arrow hiding is suppressed by an impose_order() parameter or by the
    existence of a top-level arrowhead default edge attribute.  Only a
    top-level edge default attribute matters.
    """
    # Parameter
    dot = Dot()
    dot.edge("a","b")
    _require_da(dot,impose_order(dot,hide_arrow=False), arrowhead=None)

    # Default edge attribute
    dot = Dot()
    dot.edge_default(arrowhead='box')
    dot.edge("a","b")
    _require_da(dot,impose_order(dot), arrowhead=None)

    # A theme's default edge attribute
    theme = Dot().edge_default(arrowhead='box')
    dot = Dot().use_theme(theme)
    dot.edge("a","b")
    _require_da(dot,impose_order(dot), arrowhead=None)

    # Specified other places (should not suppress)
    dot = Dot()
    dot.all_role("a",arrowhead='box')
    dot.graph_default(arrowhead='box')
    dot.node_default(arrowhead='box')
    dot.graph(arrowhead='box')
    dot.node("a",arrowhead='box')
    dot.edge("a","b",arrowhead='box')
    dot.subgraph().edge_default(arrowhead='box')
    odot = impose_order(dot)
    _require_da(dot,odot, arrowhead='none')


def test_components_and_loops():
    """
    Separate components, explicit isolated nodes, implicit endpoints, and
    self-loops must all survive.
    """
    dot = Dot()
    dot.node('alone')
    dot.node('a').node('b').node('c')
    dot.edge('a','b').edge('b','c')
    dot.edge('x','y').edge('y','z')
    dot.edge(Port('x',cp='e'),Port('x',cp='w'),label='Loop')
    odot = impose_order(dot)
    _require_da(dot,odot)


def test_various_shapes():
    """
    Order can be imposed on graphs regardless of shape, including paths,
    cycles, cliques, and graphs with unequal branches.  On average, the ordered
    renderings of these graphs should be more square than unordered.
    """
    shapes = [
        [(i,i+1) for i in range(7)],
        [(i,(i+1)%7) for i in range(7)],
        list(combinations(range(6),2)),
        [(0,i) for i in range(1,7)],
        [(0,1),(0,2),(1,2),(1,3),(2,4),(3,4),(4,5),(5,6)],
        [(0,1),(0,2),(0,3),(1,2),(2,3),(1,4),(4,5),(3,6)],
    ]

    dot_elongation = 1.0
    odot_elongation = 1.0

    for edges in shapes:

        dot = Dot()
        for node in sorted({node for edge in edges for node in edge}):
            dot.node(node,label=f'Node {node}')
        for node1, node2 in edges:
            dot.edge(node1, node2)

        odot = impose_order(dot)
        _require_da(dot,odot)

        dot_elongation *= _elongation(dot)
        odot_elongation *= _elongation(odot)

    assert odot_elongation < dot_elongation


def test_random_graphs():
    """
    Imposing order on random graphs (generated with a fixed seed) must succeed
    without failing internal invariant checks.  On average, the ordered
    renderings of these graph should be more square than unordered.
    """
    iterations = 10
    node_count = 100
    edge_count = 120

    dot_elongation = 1.0
    odot_elongation = 1.0

    verify_save = _impose._verify

    try:
        _impose._verify = True

        for i in range(iterations):

            seed = 1000 + i
            dot = Dot()
            for node in range(node_count):
                dot.node(node)
            for node1, node2 in _random_graph(node_count, edge_count, seed):
                dot.edge(node1,node2)

            odot = impose_order(dot)
            _require_da(dot,odot)

            dot_elongation *= _elongation(dot)
            odot_elongation *= _elongation(odot)
    finally:
        _impose._verify = verify_save

    assert odot_elongation < dot_elongation


def test_random_multigraphs():
    """
    Imposing order on random multigraphs (generated with a fixed seed) must
    result in all parallel edges having the same direction.
    """
    iterations   = 10
    node_count   = 100
    edge_count   = 120 # Base count before duplication
    max_parallel = 5   # There will be 1..max_parallel edges per connected
                       # node pair.

    for i in range(iterations):

        seed = 2000 + i
        dot = Dot(multigraph=True)
        for node in range(node_count):
            dot.node(node)
        for label, (node1, node2) in enumerate(
                _random_graph(node_count, edge_count,
                              seed, max_parallel)):
            dot.edge(node1,node2,label=label)

        #
        # NOTE: _require_da() verifies consistent parallel arc direction.
        #

        odot = impose_order(dot)
        _require_da(dot,odot)


def test_edges_preserved():
    """
    Edges in subgraphs must remain in subgraphs, must keep their attributes,
    and must maintain their port specifications.
    """
    dot = Dot()
    dot.edge("a",Port("b","first"),color="red")
    sub1 = dot.subgraph("sub1")
    sub1.edge(Port("b","second","s"), Port("c","third"),color="blue")
    sub2 = dot.subgraph("sub2")
    sub2.edge("c","d",color="green",style="dashed")
    sub2_sub1 = sub2.subgraph("sub2.sub1")
    sub2_sub1.edge("d","e",style="dotted",arrowhead="box")
    dot.edge(Port("e","up","n"),Port("f","down","s"))

    odot = impose_order(dot)
    _require_da(dot,odot)


def test_multigraph_edges_preserved():
    """
    Multigraph edges with and without discriminants must remain in subgraphs,
    must keep their attributes, and must maintain their port specifications.
    """
    dot = Dot(multigraph=True)
    dot.edge("a",Port("b","first"),0,color="red")
    dot.edge("a",Port("b","first","w"),1,color="green")
    sub1 = dot.subgraph("sub1")
    sub1.edge(Port("b","second","s"), Port("c","third"),color="blue")
    sub1.edge(Port("b","third","nw"), "c",color="white")
    sub1.edge(Port("b",cp="n"), Port("c",cp="e"),color="yellow")
    sub2 = dot.subgraph("sub2")
    sub2.edge("c","d",color="green",style="dashed")
    sub2_sub1 = sub2.subgraph("sub2.sub1")
    sub2_sub1.edge("d","e",2,style="dotted",arrowhead="box")
    sub2_sub1.edge("d","e",3,style="solid",arrowhead="diamond")
    dot.edge(Port("e","up","n"),Port("f","down","s"))

    odot = impose_order(dot)
    _require_da(dot,odot)


def test_roles_and_themes():
    """
    Themes and role attributes are integrated into directed analogues, but the
    themes and roles themselves are no longer present.
    """
    #
    # Theme and role attributes should be included.
    #
    theme = Dot().graph(label="Theme Label 1")
    theme.graph_role("theme_graph_role",tgr_a=11,tgr_b=21)
    theme.node_role("theme_node_role",ter_a=12,ter_b=22)
    theme.edge_role("theme_edge_role",tnr_a=13,tnr_b=23)
    theme.graph_default(tgd_a=14,tgd_b=24)
    theme.edge_default(ted_a=15,ted_b=25)
    theme.node_default(tnd_a=16,tnd_b=26)
    theme.graph(tg_a=17,tg_b=27)

    dot = Dot().use_theme(theme)
    dot.graph_role("direct_graph_role",dgr_a=31,dgr_b=41)
    dot.node_role("direct_node_role",der_a=32,der_b=42)
    dot.edge_role("direct_edge_role",dnr_a=33,dnr_b=43)
    dot.graph_default(dgd_a=34,dgd_b=44)
    dot.edge_default(ded_a=35,ded_b=45)
    dot.node_default(dnd_a=36,dnd_b=46)
    dot.graph(dg_a=37,dg_b=47)

    dot.graph(role="theme_graph_role")
    dot.node("a",role="theme_node_role")
    dot.node("b",role="direct_node_role")
    dot.node("c")
    dot.edge("a","b",role="theme_edge_role")
    dot.edge("b","c",role="direct_edge_role")
    dot.edge("c","d")
    sub1 = dot.subgraph(id="sub1")
    sub1.graph(role="theme_graph_role")
    sub2 = dot.subgraph(id="sub2")
    sub2.graph(role="direct_graph_role")

    odot = impose_order(dot)
    _require_da(dot,odot)

    #
    # The theme should be connected to dot but not odot.
    #

    theme.graph(new_theme_attr="should not appear")
    assert re.search("new_theme_attr",str(dot))
    assert not re.search("new_theme_attr",str(odot))

    #
    # The roles should be defined in dot but not in odot.
    #

    str(dot.copy().node("x",role="direct_node_role"))
    str(dot.copy().node("x",role="theme_node_role"))
    str(dot.copy().edge("x","y",role="direct_edge_role"))
    str(dot.copy().edge("x","y",role="theme_edge_role"))
    (withsub1 := dot.copy()).subgraph().graph(role="direct_graph_role")
    (withsub2 := dot.copy()).subgraph().graph(role="theme_graph_role")
    str(withsub1)
    str(withsub2)

    role_not_defined = re.compile("Role.*not defined")

    def expect_missing_role(subject:Dot):
        assert role_not_defined.search(
            str(expect_ex(RuntimeError,lambda: str(subject))))

    expect_missing_role(odot.copy().node("x",role="direct_node_role"))
    expect_missing_role(odot.copy().node("x",role="theme_node_role"))
    expect_missing_role(odot.copy().edge("x","y",role="direct_edge_role"))
    expect_missing_role(odot.copy().edge("x","y",role="theme_edge_role"))
    (withsub1 := odot.copy()).subgraph().graph(role="direct_graph_role")
    (withsub2 := odot.copy()).subgraph().graph(role="theme_graph_role")
    expect_missing_role(withsub1)
    expect_missing_role(withsub2)


_OSA_VALUES = {
    "arrowhead": "normal",
    "arrowtail": "vee",
    "headclip": "true",
    "tailclip": "false",
    "headhref": "headlink",
    "tailhref": "taillink",
    "headlabel": "head",
    "taillabel": "tail",
    "headport": "n",
    "tailport": "s",
    "headtarget": "blank",
    "tailtarget": "self",
    "headtooltip": "Headtip",
    "tailtooltip": "Tailtip",
    "headURL": "headurl",
    "tailURL": "tailurl",
    "lhead": "clusterhead",
    "ltail": "clustertail",
    "samehead": "headgroup",
    "sametail": "tailgroup",
    "dir": "forward",
}

def test_endpoint_attrs():
    """
    Endpoint order sensitive attributes should preserve their endpoint
    association when edges are reordered.  They should also be moved from
    default edge attribute lists to edges.
    """
    #
    # Setup attributes to specify and check.  The point of the quoted_ forms is
    # that gvdot quotes all label-like attributes containing human readable
    # text.
    #

    def swap_head_tail(value:str) -> str:
        if "head" in value:
            return value.replace("head", "tail", 1)
        return value.replace("tail", "head", 1)

    reversed_OSA_VALUES = {
        swap_head_tail(name): 'back' if name == "dir" else value
        for name, value in _OSA_VALUES.items()
    }

    quoted_OSA_VALUES = {
        name: f'"{value}"' if name in ('headlabel','taillabel') else value
        for name, value in _OSA_VALUES.items()
    }

    quoted_reversed_OSA_VALUES = {
        name: f'"{value}"' if name in ('headlabel','taillabel') else value
        for name, value in reversed_OSA_VALUES.items()
    }

    #
    # Edge attributes.
    #
    # NOTE: This test and the ones below assume that for edges a--b, b--c, b is
    # going to become the root, resulting in arcs b-->a, b-->c.  That's not
    # specified, but it is also hard to see why it would change.
    #

    dot = Dot()
    dot.edge("a","b",**_OSA_VALUES)
    dot.edge("b","c",**_OSA_VALUES)
    odot = impose_order(dot)
    _require_da(dot,odot)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",quoted_reversed_OSA_VALUES)
    _require_edge_attrs(lines,"b","c",quoted_OSA_VALUES)

    #
    # Default edge attributes.
    #

    dot = Dot()
    dot.edge_default(**_OSA_VALUES)
    dot.edge("a","b")
    dot.edge("b","c")
    odot = impose_order(dot)
    _require_da(dot,odot,arrowhead=None)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",quoted_reversed_OSA_VALUES)
    _require_edge_attrs(lines,"b","c",quoted_OSA_VALUES)

    #
    # Default edge attributes inherited into subgraph.
    #

    dot = Dot()
    dot.edge_default(**_OSA_VALUES)
    subdot = dot.subgraph()
    subdot.edge("a","b")
    subdot.edge("b","c")
    odot = impose_order(dot)
    _require_da(dot,odot,arrowhead=None)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",quoted_reversed_OSA_VALUES)
    _require_edge_attrs(lines,"b","c",quoted_OSA_VALUES)

    #
    # Edge role attributes.
    #

    dot = Dot()
    dot.edge_role("test",**_OSA_VALUES)
    dot.edge("a","b",role="test")
    dot.edge("b","c",role="test")
    odot = impose_order(dot)
    _require_da(dot,odot)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",quoted_reversed_OSA_VALUES)
    _require_edge_attrs(lines,"b","c",quoted_OSA_VALUES)

    #
    # Theme default edge attributes.
    #

    theme = Dot().edge_default(**_OSA_VALUES)
    dot = Dot().use_theme(theme)
    dot.edge("a","b")
    dot.edge("b","c")
    odot = impose_order(dot)
    _require_da(dot,odot,arrowhead=None)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",quoted_reversed_OSA_VALUES)
    _require_edge_attrs(lines,"b","c",quoted_OSA_VALUES)

    #
    # Theme role edge attributes.
    #

    theme = Dot().edge_role("test",**_OSA_VALUES)
    dot = Dot().use_theme(theme)
    dot.edge("a","b",role="test")
    dot.edge("b","c",role="test")
    odot = impose_order(dot)
    _require_da(dot,odot)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",quoted_reversed_OSA_VALUES)
    _require_edge_attrs(lines,"b","c",quoted_OSA_VALUES)

    #
    # We now know dir="forward" becomes dir="back".  Test the converse.
    #

    dot = Dot()
    dot.edge("a","b",dir="back")
    dot.edge("b","c",dir="back")
    odot = impose_order(dot)
    _require_da(dot,odot)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",{ "dir": "forward" })
    _require_edge_attrs(lines,"b","c",{ "dir": "back" })

    #
    # Only values "forward" and "back" of dir are changed.
    #

    dot = Dot()
    dot.edge("a","b",dir="both")
    dot.edge("b","c",dir="none")
    odot = impose_order(dot)
    _require_da(dot,odot)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",{ "dir": "both" })
    _require_edge_attrs(lines,"b","c",{ "dir": "none" })


def test_default_merge_precedence():
    """
    Edge defaults defined closer to the edge definitions have precedence.
    """
    theme = Dot().edge_default(
        headclip="true",tailclip="false",
        headhref="x",tailhref="x",
        headlabel="x",taillabel="x",
        headport="x",tailport="x"
    )

    dot = Dot().use_theme(theme)
    dot.edge_default(
        headhref="headlink",tailhref="taillink",
        headlabel="x",taillabel="x",
        headport="x",tailport="x"
    )

    subdot = dot.subgraph()
    subdot.edge_default(
        headlabel="head",taillabel="tail",
        headport="x",tailport="x"
    )

    subsubdot = subdot.subgraph()
    subsubdot.edge_default(
        headport="n",tailport="s"
    )

    subsubdot.edge("a","b")
    subsubdot.edge("b","c")

    odot = impose_order(dot)
    _require_da(dot,odot)

    lines = parse(str(odot))
    _require_edge_attrs(lines,"b","a",{
        "headclip": "false", "tailclip": "true",
        "headhref": "taillink", "tailhref": "headlink",
        "headlabel": '"tail"', "taillabel": '"head"',
        "headport": "s", "tailport": "n",
    })
    _require_edge_attrs(lines,"b","c",{
        "headclip": "true", "tailclip": "false",
        "headhref": "headlink", "tailhref": "taillink",
        "headlabel": '"head"', "taillabel": '"tail"',
        "headport": "n", "tailport": "s",
    })


def test_multigraph_endpoint_attrs():
    """
    Order sensitive edge attributes should be preserved correctly for
    multigraph parallel edges.
    """
    dot = Dot(multigraph=True)
    dot.edge("a","b",headclip="true")
    dot.edge("a","b",tailhref="taillink")
    dot.edge("a","b",headlabel="head")
    dot.edge("a","b",tailport="s")
    dot.edge("b","c",headtarget="blank")
    dot.edge("b","c",tailtooltip="Tailtip")
    dot.edge("b","c",headURL="headurl")
    dot.edge("b","c",ltail="clustertail")
    odot = impose_order(dot)
    _require_da(dot,odot)

    lines = parse(str(odot))

    def check_attrs(endpoint1,endpoint2,**kwargs):
        _require_edge_attrs(lines,endpoint1,endpoint2,kwargs,multigraph=True)

    check_attrs("b","a",tailclip="true")
    check_attrs("b","a",headhref="taillink")
    check_attrs("b","a",taillabel='"head"')
    check_attrs("b","a",headport="s")
    check_attrs("b","c",headtarget="blank")
    check_attrs("b","c",tailtooltip="Tailtip")
    check_attrs("b","c",headURL="headurl")
    check_attrs("b","c",ltail="clustertail")


def test_unaliased():
    """
    Elements of a dot object and its directed analogue are not aliased.
    """
    def edge(dot:Dot,node1,node2,**kwargs):
        if dot.edge_is_defined(node1,node2):
            dot.edge(node1,node2,**kwargs)
        else:
            dot.edge(node2,node1,**kwargs)

    def modify(dot:Dot):
        dot.graph_default(gd=2)
        dot.node_default(nd=2)
        dot.edge_default(ed=2)
        dot.graph(ga=2)
        dot.node("a",na=2)
        dot.node("c",na=2)
        edge(dot,"a","b",ea=2)
        dot.edge("a","c",ea=2)
        dot.subgraph("sub1").node("d")
        dot.subgraph("sub2").node("e")
        dot.all_role("somerole",ra=2)

    #
    # Modify dot after order imposed.
    #

    dot = Dot()
    dot.graph_default(gd=1)
    dot.node_default(nd=1)
    dot.edge_default(ed=1)
    dot.graph(ga=1)
    dot.node("a",na=1)
    dot.edge("a","b",ea=1)
    dot.subgraph("sub1").node("b")
    dot.all_role("somerole",ra=1)

    dot_str = str(dot)
    odot = impose_order(dot)
    _require_da(dot,odot)
    assert str(dot) == dot_str

    odot_str = str(odot)
    modify(dot)
    assert str(odot) == odot_str

    #
    # Modify ordered dot after order imposed.
    #

    dot = Dot()
    dot.graph_default(gd=1)
    dot.node_default(nd=1)
    dot.edge_default(ed=1)
    dot.graph(ga=1)
    dot.node("a",na=1)
    dot.edge("a","b",ea=1)
    dot.subgraph("sub1").node("b")
    dot.all_role("somerole",ra=1)

    dot_str = str(dot)
    odot = impose_order(dot)
    _require_da(dot,odot)
    assert str(dot) == dot_str

    dot_str = str(dot)
    modify(odot)
    assert str(dot) == dot_str


def test_stability():
    """
    The directed analogue constructions for a given algorithm version should
    never change.
    """
    for version in _AVAILABLE_VERSIONS:
        _test_stability(version)

#
# Extract an int node list and edge list from a Dot object.  The Dot object's
# endpoints must be simple -- no ports or compass points.  The order of nodes
# and edges returned matches the order in str(dot).
#
# NOTE: For the edges, we return a list of 2-element lists to be compatible
# with the JSON data.
#

def _int_nodes_and_edges(dot:Dot) -> tuple[
        list[int],list[list[int]]]:

    lines = parse(str(dot))
    nodes = []
    edges = []

    for line in lines:
        match line:
            case NodeLine(nodeid):
                nodes.append(int(nodeid))
            case EdgeLine(endpoint1,endpoint2):
                edges.append([int(endpoint1), int(endpoint2)])

    return nodes, edges

#
# Given a basename, which names a file in the same directory as this module,
# return a path to the file.
#

def _filename(basename:str) -> str:

    if '__file__' not in globals():
        raise RuntimeError("Impose order tests requires __file__")

    dir = os.path.dirname(__file__)
    if not dir: dir = '.'

    return dir + "/" + basename

#
# Yield a (name, dot) pair for every corpus element.  _corpus_dots() adds nodes
# and edges in the order they are found in the file.  While edges are
# explicitly given in the corpus, nodes are added as seen in an edge list --
# Dot.node() filters out the duplicates.
#

def _corpus_dots() -> Iterator[tuple[str,Dot]]:

    filename = _filename("stability-corpus.json.xz")

    with lzma.open(filename, "rt") as f:
        doc = json.load(f)

    if doc['type'] != "stability-corpus":
        raise RuntimeError("Stability corpus file has wrong type")

    for name, edges in doc['corpus'].items():
        dot = Dot()
        for u, v in edges:
            dot.node(u)
            dot.node(v)
            dot.edge(u,v)
        yield name, dot

#
# Generate the stability expect file for the specified algorithm version.
#

def _generate_stability_expect(version:int):

    expect_filename = _filename(f"stability-expect-{version}.json.xz")

    if os.path.isfile(expect_filename):
        raise RuntimeError(f"File {expect_filename} already exists")

    expect:dict[str,dict] = {}

    for name, dot in _corpus_dots():
        expect_dot = impose_order(dot,version=version)
        nodes, edges = _int_nodes_and_edges(expect_dot)
        expect[name] = {
            'nodes': nodes,
            'edges': edges }

    doc = {
        'type': "stability-expect",
        'date': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        'algorithm-version': version,
        'expect': expect,
    }

    with lzma.open(expect_filename,mode="wt") as f:
        json.dump(doc,f)

#
# Ensure the current impose_order() implementation produces the expected
# results for the given algorithm version number.
#

def _test_stability(version:int):

    expect_filename = _filename(f"stability-expect-{version}.json.xz")

    with lzma.open(expect_filename, "rt") as f:
        doc = json.load(f)

    if doc['type'] != "stability-expect":
        raise RuntimeError("Stability expect file has wrong type")

    if doc['algorithm-version'] != version:
        raise RuntimeError(
            f"Stability expect file algorithm version "
            f"is {doc['algorithm-version']}, expected {version}")

    expect = doc['expect']

    for name, corpus_dot in _corpus_dots():

        entry = expect[name]
        expect_nodes = entry['nodes']
        expect_edges = entry['edges']

        actual_dot = impose_order(corpus_dot,version=version)
        actual_nodes, actual_edges = _int_nodes_and_edges(actual_dot)

        assert actual_nodes == expect_nodes, (
            f"Unstable nodes for {name} and algorithm version {version}")

        assert actual_edges == expect_edges, (
            f"Unstable edges for {name} and algorithm version {version}")

#
# Stability expect generation and testing can be invoked from the command line:
#
#       python3 impose_order.py stability generate VERSION
#
#       python3 impose_order.py stability test VERSION
#
# where VERSION is an available version number.  Both commands fail if the
# expected corpus file, stability-corpus.json.xz does not exist.  Generation
# fails if stability-expect-VERSION.json.xz exists.
#

def _main():

    import argparse

    parser = argparse.ArgumentParser()
    actions = parser.add_subparsers(dest="action", required=True)
    stability = actions.add_parser("stability")
    subactions = stability.add_subparsers(dest="subaction", required=True)

    for name, handler in (("generate", _generate_stability_expect),
                          ("test", _test_stability)):
        subparser = subactions.add_parser(name)
        subparser.add_argument("version", type=int, metavar="VERSION")
        subparser.set_defaults(handler=handler)

    args = parser.parse_args()
    args.handler(args.version)

if __name__ == "__main__":
    _main()
