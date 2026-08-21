"""DAG algorithms dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_directed_rx,
    as_rw_graph,
    can_run_directed,
    default_can_run,
    reject_multigraph,
    remap_nodes,
    require_directed,
)
__all__ = [
    "is_directed_acyclic_graph",
    "topological_sort",
    "topological_generations",
    "ancestors",
    "descendants",
    "descendants_at_distance",
    "dag_longest_path",
    "dag_longest_path_length",
    "transitive_reduction",
    "immediate_dominators",
]


def _raise_if_cyclic(exc):
    raise nx.NetworkXUnfeasible("Graph contains a cycle.") from exc


def is_directed_acyclic_graph(G):
    """Return True if the graph is a directed acyclic graph."""
    rwg = as_rw_graph(G)
    if not rwg.is_directed():
        return False
    return bool(rx.is_directed_acyclic_graph(rwg.rx_graph))


is_directed_acyclic_graph.can_run = lambda G, *a, **k: reject_multigraph(G) or True


def topological_sort(G):
    """Yield nodes in a topological order. Any valid order may be returned."""
    rwg = as_rw_graph(G)
    require_directed(rwg)

    def _iter():
        try:
            order = rx.topological_sort(rwg.rx_graph)
        except rx.DAGHasCycle as exc:
            _raise_if_cyclic(exc)
        yield from remap_nodes(rwg, order)

    return _iter()


topological_sort.can_run = can_run_directed


def topological_generations(G):
    """Yield each topological generation. NetworkX documents these as sets."""
    rwg = as_rw_graph(G)
    require_directed(rwg)

    def _iter():
        try:
            generations = rx.topological_generations(rwg.rx_graph)
        except rx.DAGHasCycle as exc:
            _raise_if_cyclic(exc)
        for generation in generations:
            yield remap_nodes(rwg, generation)

    return _iter()


topological_generations.can_run = can_run_directed


def _reachability(G, source, kind):
    rwg = as_rw_graph(G)
    if source not in rwg.node_to_index:
        raise nx.NetworkXError(f"The node {source} is not in the graph.")
    index = rwg.node_to_index[source]
    directed = as_directed_rx(rwg)
    found = rx.ancestors(directed, index) if kind == "ancestors" else rx.descendants(directed, index)
    index_to_node = rwg.index_to_node
    return {index_to_node[i] for i in found}


def ancestors(G, source):
    """Return every node with a path to ``source``."""
    return _reachability(G, source, "ancestors")


ancestors.can_run = lambda G, *a, **k: reject_multigraph(G) or True


def descendants(G, source):
    """Return every node reachable from ``source``."""
    return _reachability(G, source, "descendants")


descendants.can_run = ancestors.can_run


def descendants_at_distance(G, source, distance):
    """Return the nodes exactly ``distance`` hops from ``source``."""
    rwg = as_rw_graph(G)
    if source not in rwg.node_to_index:
        raise nx.NetworkXError(f"The node {source} is not in the graph.")
    index = rwg.node_to_index[source]
    layers = rx.bfs_layers(rwg.rx_graph, [index])
    for depth, layer in enumerate(layers):
        if depth == distance:
            return set(remap_nodes(rwg, layer))
    return set()


descendants_at_distance.can_run = ancestors.can_run


def _reachable_indices(rwg, start_index) -> set[int]:
    """Indices NetworkX's dominance helpers report on: start plus descendants."""
    return {start_index} | {int(i) for i in rx.descendants(rwg.rx_graph, start_index)}


def _dag_weight_fn(weight, default_weight):
    fallback = float(default_weight)

    def _fn(_source, _target, data):
        if isinstance(data, dict):
            value = data.get(weight, fallback)
            return fallback if value is None else float(value)
        if data is None:
            return fallback
        return float(data)

    return _fn


def _can_run_dag_longest_path(
    G, weight="weight", default_weight=1, topo_order=None, **kwargs
):
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    if not G.is_directed():
        return "not implemented for undirected type"
    if topo_order is not None:
        return "rustworkx dag_longest_path does not accept a topo_order"
    return True


def dag_longest_path(G, weight="weight", default_weight=1, topo_order=None):
    """Return a longest path in a DAG. Ties are broken by rustworkx."""
    _ = topo_order
    rwg = as_rw_graph(G)
    require_directed(rwg)
    try:
        path = rx.dag_weighted_longest_path(
            rwg.rx_graph, _dag_weight_fn(weight, default_weight)
        )
    except rx.DAGHasCycle as exc:
        _raise_if_cyclic(exc)
    return remap_nodes(rwg, path)


dag_longest_path.can_run = _can_run_dag_longest_path


def dag_longest_path_length(G, weight="weight", default_weight=1):
    """Return the length of a longest path in a DAG."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    try:
        length = rx.dag_weighted_longest_path_length(
            rwg.rx_graph, _dag_weight_fn(weight, default_weight)
        )
    except rx.DAGHasCycle as exc:
        _raise_if_cyclic(exc)
    return length


dag_longest_path_length.can_run = _can_run_dag_longest_path


def transitive_reduction(G):
    """Return the transitive reduction of a DAG."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    if not rx.is_directed_acyclic_graph(rwg.rx_graph):
        raise nx.NetworkXError("Directed Acyclic Graph required for transitive_reduction")
    reduced, index_map = rx.transitive_reduction(rwg.rx_graph)
    index_to_node = [None] * reduced.num_nodes()
    for old_index, new_index in index_map.items():
        index_to_node[new_index] = rwg.index_to_node[old_index]
    out = nx.DiGraph()
    out.add_nodes_from(rwg.index_to_node)
    out.add_edges_from(
        (index_to_node[u], index_to_node[v]) for u, v in reduced.edge_list()
    )
    return out


transitive_reduction.can_run = can_run_directed


def immediate_dominators(G, start):
    """Return the immediate dominator of every node reachable from ``start``."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    if start not in rwg.node_to_index:
        raise nx.NetworkXError("start is not in G")
    index = rwg.node_to_index[start]
    index_to_node = rwg.index_to_node
    reachable = _reachable_indices(rwg, index)
    result = {
        index_to_node[node]: index_to_node[dominator]
        for node, dominator in rx.immediate_dominators(rwg.rx_graph, index).items()
        if node in reachable
    }
    # NetworkX drops the start node's self-domination from the result.
    result.pop(start, None)
    return result


immediate_dominators.can_run = can_run_directed
