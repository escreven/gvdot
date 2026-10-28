from collections import defaultdict
import math
from collections.abc import Iterator
from typing import Counter, Literal
from ._core import Block, Dot, _Edge, _NormID, _Mien, _integrate_role, _Attrs

#
# Make available algorithm versions visible to tests.  (impose_order() does not
# use _AVAILABLE_VERSIONS; its check is baked into the code.)
#

_AVAILABLE_VERSIONS = (1,)

#
# Minimal graph type support.
#

class _Graph:
    __slots__ = "adj",

    adj:dict[_NormID,list[_NormID]]

    def __init__(self):
        self.adj = {}


class _Digraph:
    __slots__ = "in_adj", "out_adj"

    in_adj:dict[_NormID,list[_NormID]]
    out_adj:dict[_NormID,list[_NormID]]

    def __init__(self):
        self.in_adj = {}
        self.out_adj = {}

    #
    # Having add_arc filter out duplicates simplifies _directed_from().
    #

    def add_arc(self, node1:_NormID, node2:_NormID) -> None:
        assert node1 != node2, f"Self-loop of {node1}"
        out_adj = self.out_adj
        in_adj = self.in_adj
        if (out_adj_node1 := out_adj.get(node1)) is None:
            out_adj[node1] = [ node2 ]
            in_adj[node1] = []
        else:
            if node2 in out_adj_node1: return
            out_adj_node1.append(node2)
        if (in_adj_node2 := in_adj.get(node2)) is None:
            out_adj[node2] = []
            in_adj[node2] = [ node1 ]
        else:
            in_adj_node2.append(node1)

#
# A stable iteration order set.
#

type _NodeSet = dict[_NormID, Literal[True]]

#
# Return a dict of eccentricity by node.
#

def _eccentricity(graph:_Graph) -> dict[_NormID,int]:

    #
    # D[i][j] is the shortest path length between the i-th and j-th node using
    # nodes 0..k-1 as intermediates.  D is a full matrix symmetric around the
    # main diagonal; a version which used only a lower triangular matrix was
    # about a third slower.
    #

    adj = graph.adj
    N = len(adj)
    D = [ [ N ] * N for _ in range(N) ]

    #
    # Self and direct paths.
    #

    index = { node:i for i, node in enumerate(adj) }

    for i, u_adj in enumerate(adj.values()):
        D_i = D[i]
        D_i[i] = 0
        for v in u_adj:
            j = index[v]
            D_i[j] = 1
            D[j][i] = 1

    #
    # Floyd-Warshall.
    #

    for k in range(N):
        D_k = D[k]
        for i in range(N):
            D_i = D[i]
            d_i_k = D_i[k]
            for j in range(i+1):
                d_k_j = D_k[j]
                d_i_j = D_i[j]
                if d_i_j > (d_i_k_j := d_i_k + d_k_j):
                    D_i[j] = d_i_k_j
                    D[j][i] = d_i_k_j

    #
    # Accumulate eccentricities to E.
    #

    E = [ max(D[i]) for i in range(N) ]

    return { node: E[i] for i, node in enumerate(adj) }

#
# Return a dict mapping nodes to rank based on the given DAG.  A node's rank is
# the length of the longest path from a digraph source node (of which there is
# only one, the root).
#

def _compute_ranks(digraph:_Digraph) -> dict[_NormID,int]:

    in_adj = digraph.in_adj
    out_adj = digraph.out_adj
    map:dict[_NormID,int] = { }

    remaining = { node: len(in_adj_node)
                  for node, in_adj_node in in_adj.items() }

    rank = 0
    cohort = [ node for node, count in remaining.items() if count == 0 ]

    while cohort:
        next_cohort:list[_NormID] = []
        for node in cohort:
            map[node] = rank
            for other in out_adj[node]:
                count = remaining[other]
                if count == 1:
                    next_cohort.append(other)
                else:
                    remaining[other] = count - 1
        cohort = next_cohort
        rank += 1

    return map

#
# Return the difference between the largest and smallest interior rank
# populations, where a rank's population includes its nodes and the arcs that
# wholly span it.
#

def _raggedness(digraph:_Digraph, rank_map:dict) -> float:
    counts = Counter(rank_map.values())
    if len(counts) < 4:
        return 0
    for u, u_out_adj in digraph.out_adj.items():
        for v in u_out_adj:
            for rank in range(rank_map[u]+1,rank_map[v]):
                counts[rank] += 1
    min_rank = min(counts)
    max_rank = max(counts)
    del counts[min_rank]
    del counts[max_rank]
    values = list(counts.values())
    return max(values) - min(values)

#
# Call an arc rigid if the predecessor and successor nodes have a rank
# difference of one.  The pile at a node is that node and all nodes that can be
# reached from it by rigid paths.
#
# _pile_analyze() returns the height of the pile at node and a forecast of the
# ranks of the pile nodes if node is pushed down one rank.
#

def _pile_analyze(
        digraph:_Digraph, node:_NormID,
        rank_map:dict[_NormID,int]) -> tuple[int, dict[_NormID,int]]:

    out_adj = digraph.out_adj

    cohort = [ node ]
    height = 0
    rank   = rank_map[node]
    forecast:dict[_NormID,int] = { node:rank+1 }

    while cohort:
        height += 1
        next_cohort:list[_NormID] = []
        next_rank = rank + 1
        for node in cohort:
            for other in out_adj[node]:
                if rank_map[other] == next_rank and other not in forecast:
                    next_cohort.append(other)
                    forecast[other] = next_rank + 1
        cohort = next_cohort
        rank = next_rank

    return height, forecast

#
# Check _directed_from() invariants.
#

def _verify_direct_from(
        graph:_Graph,
        digraph:_Digraph,
        rank_map:dict[_NormID,int],
        pending_nodes:list[_NodeSet],
        pending_degree:dict[_NormID,int]):

    adj = graph.adj

    assert rank_map == _compute_ranks(digraph)

    check_pending_degree = { node: sum(1 for other in adj[node]
                             if rank_map[node] == rank_map[other])
                             for node in adj }

    assert pending_degree == check_pending_degree

    for node, rank in rank_map.items():
        if pending_degree[node] > 0:
            assert node in pending_nodes[rank]

    for rank_pending in pending_nodes:
        for node in rank_pending:
            assert pending_degree[node] > 0

    for node in adj:
        assert node in rank_map

    for u, u_adj in adj.items():
        for v in u_adj:
            assert (v in digraph.out_adj[u] or
                    u in digraph.out_adj[v] or
                    rank_map[u] == rank_map[v] and
                    u in pending_nodes[rank_map[u]] and
                    v in pending_nodes[rank_map[v]])

#
# Determine a directed acyclic analogue of the given connected simple graph of
# at least two nodes.  Every edge in the input graph will have a corresponding
# arc in the DAG.  The DAG has a root, a single source node.  _directed()
# returns a dict mapping nodes to ranks, where a node's rank is the longest
# path length from the root to the node.  The DAG can be reconstructed from
# this map: the endpoints of an edge must be on different ranks (since they
# must have different longest paths from the root in the DAG); thus the
# corresponding arc direction can be determined by comparing endpoint ranks.
#

_verify = False

def _directed(graph:_Graph) -> dict[_NormID,int]:

    adj = graph.adj

    #
    # We choose roots to explore based on a target eccentricity.
    #
    # Rationale for the target: The root node will occupy rank zero.  We would
    # like the arrangement of the remaining nodes to be roughly square.  That
    # square would have a height sqrt(N-1), where N is the number of nodes.  To
    # ensure at least that height, there needs to be a shortest path length
    # sqrt(N-1) from the root to nodes at the bottom of the square.
    #

    target_e = math.sqrt(len(adj) - 1)

    E = _eccentricity(graph)

    best_node_e = min((E[node] for node in adj),
                      key=lambda node_e:(math.fabs(target_e - node_e)))


    def choices():
        for node in adj:
            if E[node] == best_node_e:
                digraph, rank_map = _directed_from(graph,node)
                cost = (_raggedness(digraph,rank_map), -len(adj[node]))
                yield cost, rank_map

    return min(choices(), key=lambda choice: choice[0])[1]

def _directed_from(graph:_Graph, root:_NormID
                   ) -> tuple[_Digraph,dict[_NormID,int]]:

    adj = graph.adj

    #
    # We build a directed analogue of graph starting from root.  At every step,
    # digraph will remain acyclic.
    #

    digraph = _Digraph()
    add_arc = digraph.add_arc

    #
    # We initially rank every node based on its shortest path length to the
    # root in the input graph.  We assign directions to edges that cross these
    # ranks from low to high.
    #

    cohort:_NodeSet = { root: True }
    marked:_NodeSet = { root: True }

    while cohort:
        next_cohort:_NodeSet = {}
        for node in cohort:
            for other in adj[node]:
                if other not in marked:
                    add_arc(node,other)
                    next_cohort[other] = True
        marked |= next_cohort
        cohort = next_cohort

    #
    # The rest of the direction assignments also depend on rank computations,
    # but from this point forward, a node's rank will be the longest path
    # length from the root to the node in the directed graph.
    #
    # rank_map is a dict mapping nodes to those ranks.
    #

    rank_map = _compute_ranks(digraph)

    #
    # We call an input graph edge pending if it has not yet been assigned a
    # direction.  We call a node pending if it has any pending edges.  The
    # pending degree of a node is the number of incident pending edges.
    #
    # Any pending node must be on its initially assigned rank, since all of its
    # edges become resolved if it's ever shifted down.  Because we always
    # assign a direction to edges between nodes on different ranks, all pending
    # edges are between nodes on the same rank.
    #
    # pending_nodes[r] is the set of pending nodes on rank r.
    #
    # pending_degree[node] is the pending degree of node.
    #

    max_rank = max(rank_map.values())
    pending_nodes:list[_NodeSet] = [ {} for _ in range(max_rank + 1) ]
    pending_degree:dict[_NormID,int] = {}

    for node in adj:
        node_rank = rank_map[node]
        node_pd = sum(rank_map[other] == node_rank for other in adj[node])
        pending_degree[node] = node_pd
        if node_pd > 0:
            pending_nodes[node_rank][node] = True

    #
    # We prioritize edges for direction assignment by maximal endpoint
    # pending degree, then maximal secondary endpoint pending degree.
    #

    def edge_priority(edge:tuple[_NormID,_NormID]):
        u, v = edge
        u_pd = pending_degree[u]
        v_pd = pending_degree[v]
        return (rank_map[u], max(u_pd,v_pd), min(u_pd,v_pd))

    #
    # Assign edge directions until there are no more pending nodes.
    #

    current_rank = len(pending_nodes) - 1

    while current_rank > 0:

        current_pending = pending_nodes[current_rank]

        if not current_pending:
            current_rank -= 1
            continue

        #
        # Choose a pending edge to direct.
        #

        u, v = max(((u, v) for u in current_pending for v in adj[u]
                    if rank_map[v] == current_rank),
                   key=edge_priority)

        #
        # Consider each direction for the edge.  Choose a direction that shifts
        # down the shortest pile, and if the piles are equal height, the
        # direction that creates the most opportunity for immediate follow up
        # assignment.
        #

        u_ph, u_pf = _pile_analyze(digraph,u,rank_map)
        v_ph, v_pf = _pile_analyze(digraph,v,rank_map)

        if u_ph > v_ph or (u_ph == v_ph and
                           pending_degree[v] >= pending_degree[u]):
            add_arc(u,v)
            rank_map.update(v_pf)
            node = v
        else:
            add_arc(v,u)
            rank_map.update(u_pf)
            node = u

        #
        # node has been pushed down one rank.  It is no longer pending, and its
        # previously pending edges are now between nodes of unequal rank.
        # Assign those edges a direction, which may cause adjacent nodes to
        # become resolved.
        #

        del current_pending[node]
        pending_degree[node] = 0

        for other in adj[node]:
            if other in current_pending:
                add_arc(other,node)
                other_pd = pending_degree[other] - 1
                pending_degree[other] = other_pd
                if other_pd == 0:
                    del current_pending[other]

        if _verify:
            _verify_direct_from(graph,digraph,rank_map,
                                pending_nodes,pending_degree)

    return digraph, rank_map

#
# Yield the connected components of graph.
#

def _connected_components(graph:_Graph) -> Iterator[_Graph]:

    adj = graph.adj

    component:_NodeSet = {}
    marked:_NodeSet = {}

    def visit(node:_NormID):
        component[node] = True
        stack = [ node ]
        while stack:
            node = stack.pop()
            for other in adj[node]:
                if other not in component:
                    component[other] = True
                    stack.append(other)

    for node in adj:
        if node not in marked:
            visit(node)
            subgraph = _Graph()
            subgraph.adj = { node: adj[node].copy() for node in component }
            yield subgraph
            marked |= component
            component.clear()


#
# Many edge attributes are sensitive to endpoint order, even in an undirected
# graph.  _HEAD_TAIL_PAIRS are attributes that are tail (first endpoint) or
# head (second endpoint) specific with duals specific to the other endpoint.
# When impose_order() rewrites an edge to appear in the opposite order, it
# renames these attributes to their duals so the attribute continues to apply
# to the same endpoint.
#
# Attribute "dir" can also be endpoint order sensitive if it has value
# "forward" or "back".  In that case, the value of "dir" is flipped between
# "forward" and "back" if the associated edge is reordered.
#
# _ORDER_SENSITIVE are all edge attributes that may need to be renamed or
# modified on reordering.
#

_HEAD_TAIL_PAIRS =(
    ("arrowhead"   , "arrowtail"),
    ("headclip"    , "tailclip"),
    ("headhref"    , "tailhref"),
    ("headlabel"   , "taillabel"),
    ("headport"    , "tailport"),
    ("headtarget"  , "tailtarget"),
    ("headtooltip" , "tailtooltip"),
    ("headURL"     , "tailURL"),
    ("lhead"       , "ltail"),
    ("samehead"    , "sametail"),
)

_ORDER_SENSITIVE = ({ "dir" } |
    set(name for pair in _HEAD_TAIL_PAIRS for name in pair))

#
# Remove and return the order sensitive attributes.  "dir" is always extracted
# no matter what its value.  (attrs is always a default edge attributes dict.)
#

def _extract_order_sensitive(attrs:_Attrs) -> _Attrs:
    result = {}
    for name in _ORDER_SENSITIVE:
        if (value := attrs.get(name)) is not None:
            del attrs[name]
            result[name] = value
    return result

#
# Update the given attributes so that any order sensitive attributes reflect an
# order reversal.
#

def _reverse_order_sensitive(attrs:_Attrs) -> None:
    stash = {}
    for name1, name2 in _HEAD_TAIL_PAIRS:
        if (value := attrs.get(name1)) is not None:
            stash[name2] = value
            del attrs[name1]
        if (value := attrs.get(name2)) is not None:
            stash[name1] = value
            del attrs[name2]
    attrs.update(stash)
    if (value := attrs.get("dir")):
        if value == "forward":
            attrs["dir"] = "back"
        elif value == "back":
            attrs["dir"] = "forward"

#
# Like dict.update() except only add a (key,value) from other if key is missing
# from the target.
#

def _update_if_missing(target:_Attrs, other:_Attrs):
    for name, value in other.items():
        if name not in target:
            target[name] = value

#
# Return a copy of dot with all themes and roles integrated, and all order
# sensitive edge attributes moved down from default attribute dicts to the
# edges that would normally inherit them.
#

def _transform(dot:Dot) -> Dot:

    #
    # Flatten themes and integrate node and edge roles.
    #

    dot  = dot.copy()
    mien = _Mien(dot)

    dot.graphroles = defaultdict(dict)
    dot.noderoles  = defaultdict(dict)
    dot.edgeroles  = defaultdict(dict)
    dot.theme      = None
    dot.d_grapha   = mien.d_grapha
    dot.d_nodea    = mien.d_nodea
    dot.d_edgea    = mien.d_edgea
    dot.grapha     = mien.grapha

    graphroles = mien.graphroles
    noderoles  = mien.noderoles
    edgeroles  = mien.edgeroles

    nodemap = dot.nodemap
    for nodekey, attrs in list(nodemap.items()):
        nodemap[nodekey] = _integrate_role(attrs,noderoles,"node",nodekey)

    edgemap = dot.edgemap
    for edge in edgemap.values():
        edge.attrs = _integrate_role(edge.attrs,edgeroles,"edge",edge)

    #
    # Walk the Block tree, including the Dot object, integrating graph
    # attributes and moving order sensitive attributes down to edges.
    #

    def transform_block(block:Block, parent_osa:_Attrs) -> None:

        block.grapha = _integrate_role(block.grapha, graphroles,
                                       "graph", block.graphid)

        osa = _extract_order_sensitive(block.d_edgea)
        _update_if_missing(osa,parent_osa)

        for edge in block.edges:
            _update_if_missing(edge.attrs,osa)

        for subgraph in block.subgraphs:
            transform_block(subgraph, osa)

    transform_block(dot,{})

    return dot


def impose_order(dot:Dot, *, hide_arrow:bool=True, version:int=1) -> Dot:
    """
    Return a directed, modified deep copy of an undirected Dot object with
    edges oriented to possibly improve its layout by the Graphviz
    :program:`dot` program.

    :param dot: The undirected Dot object to copy and direct.

    :param hide_arrow: Set the default edge attribute ``arrowhead`` to ``none``
        if it's not already defined in the Dot object or its theme.  That
        overrides the :program:`dot` program's use of arrowheads to depict
        direction, making the result appear undirected.

    :param version: The reorganization algorithm version to use.  The edge
        orientation chosen by :func:`impose_order` is stable for a given
        ``version`` value.  If the algorithm changes, the default value
        (currently 1) will be incremented, but prior version numbers should
        produce the same directed graph given the same input.

    :return: A directed Dot object with the same nodes, edges, and subgraphs as
        ``dot``, with ``dot``'s theme and role attributes incorporated as
        default and entity attributes, but no theme or roles itself.

    :raises ValueError: The input Dot object is already directed, or the
        version number specified is not available.

    The input Dot object is not modified.  The returned Dot object will have
    the same nodes, edges, and subgraphs as the input object.  If the input Dot
    object is multigraph, the returned object will be multigraph, and all edges
    between a given node pair will have the same direction.

    The returned Dot object will not have a theme or any roles; instead,
    whatever attributes are defined by the input object's theme or roles will
    be integrated into the returned object as default or entity attributes.
    Furthermore, any edge-order sensitive attributes will be moved from the
    returned object's default edge attribute lists down to individual edges.
    This facilitates endpoint attribute preservation.

    Endpoint Attribute Preservation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The edge attributes below apply to only one endpoint of an edge.  (In the
    case of an undirected graph, "tail" means first and "head" means second.)
    If :func:`impose_order` changes the endpoint order of an edge, it rewrites
    these attributes using converse names so that specified values still apply
    to the intended endpoint.

    .. list-table::
        :align: center

        * - arrowhead
          - arrowtail
        * - headclip
          - tailclip
        * - headhref
          - tailhref
        * - headlabel
          - taillabel
        * - headport
          - tailport
        * - headtarget
          - tailtarget
        * - headtooltip
          - tailtooltip
        * - headURL
          - tailURL
        * - lhead
          - ltail
        * - samehead
          - sametail

    In addition, edge attribute ``dir`` value ``forward`` is changed to
    ``back``, and value ``back`` is changed to ``forward``.

    Use
    ~~~

    The canonical use of :func:`impose_order` is to call it immediately before
    rendering.

    .. code-block:: python

        impose_order(dot).show()               # Display in a notebook
        impose_order(dot).save("output.svg")   # Save to a file

    Although rendering immediately is typical, the Dot object returned by
    :func:`impose_order` is fully functional, and can be grown, amended, or
    have a theme assigned.  However, applications must be aware that input
    theme and role attributes have been integrated, roles are no longer defined
    or assigned, order sensitive edge attributes have been moved to edges, and
    what are undirected edges of the input are now unpredictably directed in
    the returned object.  A simple approach to handle that last concern is

    .. code-block:: python

        ordered_dot = impose_order(dot)
        ...
        for u, v in critical_edges:
            if ordered_dot.edge_is_defined(u,v):
                ordered_dot.edge_update(u,v,role="critical")
            else:
                ordered_dot.edge_update(v,u,role="critical")
    """
    if dot.directed:
        raise ValueError("Cannot impose order on a directed graph")

    if version not in (1,):
        raise ValueError(f"Algorithm version {version} is unknown")

    result = _transform(dot)
    result.directed = True

    if hide_arrow:
        theme_or_dot = dot
        while theme_or_dot is not None:
            if 'arrowhead' in theme_or_dot.d_edgea:
                break
            theme_or_dot = theme_or_dot.theme
        else:
            result.d_edgea['arrowhead'] = 'none'

    #
    # Collapse parallel edges into a simple working graph.  Keep the copied
    # Dot edges so their ports, discriminants, attributes, and blocks survive
    # the direction assignments.  Self-loops do not affect the ordering.
    #

    graph = _Graph()
    adj = graph.adj
    for node in result.nodemap:
        adj[node] = []

    edge_map:dict[tuple[_NormID,_NormID],list[_Edge]] = {}

    for (u,v,_), edge in result.edgemap.items():
        if (edges := edge_map.get((u,v))) is None:
            edge_map[u,v] = [ edge ]
            u_adj = adj.setdefault(u,[])
            v_adj = adj.setdefault(v,[])
            if u != v:
                u_adj.append(v)
                v_adj.append(u)
        else:
            edges.append(edge)

    #
    # Order each component.
    #
    # The rank maps of each component are merged together in a composite rank
    # map with (component_index,rank) values.  The component index makes it
    # easy to separate the nodes and edges of the components in the output Dot
    # object.
    #

    composite_rank_map:dict[_NormID,tuple[int,int]] = {}

    for index, subgraph in enumerate(_connected_components(graph)):
        if len(subgraph.adj) == 1:
            (singleton,) = subgraph.adj
            rank_map = { singleton: 0 }
        else:
            rank_map = _directed(subgraph)
        for node, rank in rank_map.items():
            composite_rank_map[node] = (index,rank)

    #
    # Direct every result edge.
    #

    result.edgemap.clear()

    for (u,v), edges in edge_map.items():
        if composite_rank_map[u] > composite_rank_map[v]:
            u, v = v, u
        for edge in edges:
            if edge.normport1.node != u:
                edge.normport1, edge.normport2 = (
                    edge.normport2, edge.normport1)
                _reverse_order_sensitive(edge.attrs)
            edge.directed = True
            result.edgemap[u,v,edge.normdisc] = edge

    #
    # Order block nodes and edges by rank.
    #

    def order_block(block:Block):
        block.nodes.sort(
            key=lambda node: composite_rank_map[node])
        block.edges.sort(
            key=lambda edge: composite_rank_map[edge.normport1.node])
        for subgraph in block.subgraphs:
            order_block(subgraph)

    order_block(result)

    return result
