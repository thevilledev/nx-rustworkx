"""Matching algorithms dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    can_run_undirected,
    edge_weight_fn,
    require_undirected,
)

__all__ = ["is_matching", "is_maximal_matching", "max_weight_matching"]


def _can_run_max_weight_matching(G, maxcardinality=False, weight="weight", **kwargs):
    reason = can_run_undirected(G)
    if reason is not True:
        return reason
    if callable(weight):
        return "nx-rustworkx does not support custom weight callables"
    # rustworkx's blossom implementation only takes integer edge weights.
    for _u, _v, data in G.edges(data=True):
        value = data.get(weight, 1)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            if not (isinstance(value, float) and value.is_integer()):
                return "rustworkx max_weight_matching requires integer edge weights"
    return True


def max_weight_matching(G, maxcardinality=False, weight="weight"):
    """Return a maximum-weight matching as a set of node pairs."""
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    weight_fn = edge_weight_fn(weight)
    pairs = rx.max_weight_matching(
        rwg.rx_graph,
        max_cardinality=bool(maxcardinality),
        weight_fn=lambda data: int(weight_fn(data)),
    )
    index_to_node = rwg.index_to_node
    return {(index_to_node[u], index_to_node[v]) for u, v in pairs}


max_weight_matching.can_run = _can_run_max_weight_matching


def _matching_index_pairs(rwg, matching):
    """Validate a matching the way NetworkX does and map it to index pairs.

    Returns ``None`` when the matching is trivially invalid (a self-loop),
    which NetworkX reports as False rather than an error.
    """
    if isinstance(matching, dict):
        # Mirror nx.matching_dict_to_set: drop mirrored pairs, reject self-loops.
        edges = set()
        for edge in matching.items():
            u, v = edge
            if (v, u) in edges or edge in edges:
                continue
            if u == v:
                raise nx.NetworkXError(f"Selfloops cannot appear in matchings {edge}")
            edges.add(edge)
        matching = edges
    pairs = set()
    for edge in matching:
        if len(edge) != 2:
            raise nx.NetworkXError(f"matching has non-2-tuple edge {edge}")
        u, v = edge
        if u not in rwg.node_to_index or v not in rwg.node_to_index:
            raise nx.NetworkXError(f"matching contains edge {edge} with node not in G")
        if u == v:
            return None
        pairs.add((rwg.node_to_index[u], rwg.node_to_index[v]))
    return pairs


def is_matching(G, matching):
    """Return True if ``matching`` is a valid matching of the graph."""
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    pairs = _matching_index_pairs(rwg, matching)
    if pairs is None:
        return False
    return bool(rx.is_matching(rwg.rx_graph, pairs))


is_matching.can_run = can_run_undirected
is_matching.multigraph = True


def is_maximal_matching(G, matching):
    """Return True if ``matching`` is a maximal matching of the graph."""
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    pairs = _matching_index_pairs(rwg, matching)
    if pairs is None:
        return False
    return bool(rx.is_maximal_matching(rwg.rx_graph, pairs))


is_maximal_matching.can_run = can_run_undirected
