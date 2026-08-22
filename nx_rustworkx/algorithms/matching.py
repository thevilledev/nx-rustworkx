"""Matching algorithms dispatched to rustworkx."""

from __future__ import annotations

import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    can_run_undirected,
    edge_weight_fn,
    require_undirected,
)

__all__ = ["max_weight_matching"]


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
