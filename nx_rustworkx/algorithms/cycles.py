"""Cycle enumeration dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    can_run_directed,
    can_run_undirected,
    remap_nodes,
    require_directed,
    require_undirected,
)

__all__ = ["chain_decomposition", "cycle_basis", "find_cycle", "simple_cycles"]


def _can_run_simple_cycles(G, length_bound=None, **kwargs):
    reason = can_run_directed(G)
    if reason is not True:
        return reason
    if length_bound is not None:
        return "rustworkx simple_cycles does not support length_bound"
    return True


def simple_cycles(G, length_bound=None):
    """Yield the elementary circuits of a directed graph."""
    _ = length_bound
    rwg = as_rw_graph(G)
    require_directed(rwg)

    def _iter():
        for cycle in rx.simple_cycles(rwg.rx_graph):
            yield remap_nodes(rwg, cycle)

    return _iter()


simple_cycles.can_run = _can_run_simple_cycles
simple_cycles.multigraph = True


def _can_run_cycle_basis(G, root=None, **kwargs):
    reason = can_run_undirected(G)
    if reason is not True:
        return reason
    if root is not None:
        return "rustworkx cycle_basis does not support root"
    return True


def cycle_basis(G, root=None):
    """Return a cycle basis of an undirected graph. The basis is not unique."""
    _ = root
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    return [remap_nodes(rwg, cycle) for cycle in rx.cycle_basis(rwg.rx_graph)]


cycle_basis.can_run = _can_run_cycle_basis


def _can_run_find_cycle(G, source=None, orientation=None, **kwargs):
    reason = can_run_directed(G)
    if reason is not True:
        return reason
    if orientation is not None:
        return "rustworkx find_cycle does not support orientation"
    return True


def find_cycle(G, source=None, orientation=None):
    """Return the edges of a cycle found via depth-first traversal."""
    _ = orientation
    rwg = as_rw_graph(G)
    require_directed(rwg)
    rx_graph = rwg.rx_graph
    if source is None:
        cycle = rx.digraph_find_cycle(rx_graph)
    else:
        sources = [source] if rwg.has_node(source) else list(source)
        cycle = []
        for start in sources:
            if start not in rwg.node_to_index:
                raise nx.NodeNotFound(f"Node {start} is not in G")
            cycle = rx.digraph_find_cycle(rx_graph, source=rwg.node_to_index[start])
            if len(cycle):
                break
    if not len(cycle):
        raise nx.NetworkXNoCycle("No cycle found.")
    index_to_node = rwg.index_to_node
    if rwg.is_multigraph():
        # NetworkX's edge_dfs reports the first key of G[u][v], the lowest index.
        edge_keys = rwg.edge_keys
        return [
            (
                index_to_node[u],
                index_to_node[v],
                edge_keys[min(rx_graph.edge_indices_from_endpoints(u, v))],
            )
            for u, v in cycle
        ]
    return [(index_to_node[u], index_to_node[v]) for u, v in cycle]


find_cycle.can_run = _can_run_find_cycle
find_cycle.multigraph = True


def _can_run_chain_decomposition(G, root=None, **kwargs):
    _ = root
    return can_run_undirected(G)


def chain_decomposition(G, root=None):
    """Yield the chains of a chain decomposition. The decomposition is not unique."""
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    index_to_node = rwg.index_to_node

    def _iter():
        # NetworkX validates the root lazily, on the first chain request.
        if root is not None and root not in rwg.node_to_index:
            raise nx.NodeNotFound(f"Root node {root} is not in G")
        source = None if root is None else rwg.node_to_index[root]
        for chain in rx.chain_decomposition(rwg.rx_graph, source=source):
            yield [(index_to_node[u], index_to_node[v]) for u, v in chain]

    return _iter()


chain_decomposition.can_run = _can_run_chain_decomposition
