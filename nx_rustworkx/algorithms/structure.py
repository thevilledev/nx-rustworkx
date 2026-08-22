"""Whole-graph structural properties dispatched to rustworkx."""

from __future__ import annotations

import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_directed_rx,
    as_rw_graph,
    reject_multigraph,
    remap_nodes,
)

__all__ = ["is_bipartite", "isolates", "number_of_isolates", "transitivity"]


def _can_run(G, *args, **kwargs):
    return reject_multigraph(G) or True


def is_bipartite(G):
    """Return True if the graph is bipartite."""
    rwg = as_rw_graph(G)
    graph = as_directed_rx(rwg) if rwg.is_directed() else rwg.rx_graph
    return bool(rx.is_bipartite(graph))


is_bipartite.can_run = _can_run


def isolates(G):
    """Yield the nodes with no neighbors."""
    rwg = as_rw_graph(G)
    return iter(remap_nodes(rwg, rx.isolates(rwg.rx_graph)))


isolates.can_run = _can_run


def number_of_isolates(G):
    """Return the number of nodes with no neighbors."""
    rwg = as_rw_graph(G)
    return len(rx.isolates(rwg.rx_graph))


number_of_isolates.can_run = _can_run


def transitivity(G):
    """Return the fraction of all possible triangles present in the graph."""
    rwg = as_rw_graph(G)
    return float(rx.transitivity(rwg.rx_graph))


transitivity.can_run = _can_run
