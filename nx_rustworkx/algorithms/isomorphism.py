"""Isomorphism checks dispatched to rustworkx VF2."""

from __future__ import annotations

import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph, reject_multigraph

__all__ = ["is_isomorphic"]


def _can_run_isomorphic(G1, G2, node_match=None, edge_match=None, **kwargs):
    _ = kwargs
    for graph in (G1, G2):
        reason = reject_multigraph(graph)
        if reason:
            return reason
    if node_match is not None or edge_match is not None:
        return "nx-rustworkx is_isomorphic is structural only in v0.1"
    return True


def is_isomorphic(G1, G2, node_match=None, edge_match=None):
    """Return True if G1 and G2 are structurally isomorphic."""
    _ = node_match, edge_match
    left = as_rw_graph(G1)
    right = as_rw_graph(G2)
    if left.is_directed() != right.is_directed():
        return False
    if left.number_of_nodes() != right.number_of_nodes():
        return False
    if left.number_of_edges() != right.number_of_edges():
        return False
    return bool(
        rx.is_isomorphic(
            left.rx_graph,
            right.rx_graph,
            id_order=False,
        )
    )


is_isomorphic.can_run = _can_run_isomorphic
