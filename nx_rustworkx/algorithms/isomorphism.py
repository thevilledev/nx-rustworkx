"""Isomorphism checks dispatched to rustworkx VF2."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph

__all__ = [
    "is_isomorphic",
    "vf2pp_all_isomorphisms",
    "vf2pp_is_isomorphic",
    "vf2pp_isomorphism",
]


def _can_run_isomorphic(G1, G2, node_match=None, edge_match=None, **kwargs):
    _ = G1, G2, kwargs
    if node_match is not None or edge_match is not None:
        return "nx-rustworkx is_isomorphic is structural only in v0.1"
    return True


def is_isomorphic(G1, G2, node_match=None, edge_match=None):
    """Return True if G1 and G2 are structurally isomorphic."""
    _ = node_match, edge_match
    if G1.is_directed() != G2.is_directed():
        raise nx.NetworkXError("Graphs G1 and G2 are not of the same type.")
    left = as_rw_graph(G1)
    right = as_rw_graph(G2)
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
is_isomorphic.multigraph = True


def _can_run_vf2pp(G1, G2, node_label=None, default_label=None, **kwargs):
    _ = G1, G2, default_label
    if node_label is not None:
        return "nx-rustworkx vf2pp_is_isomorphic is structural only"
    return True


def vf2pp_is_isomorphic(G1, G2, node_label=None, default_label=None):
    """Return True if G1 and G2 are structurally isomorphic."""
    _ = node_label, default_label
    return is_isomorphic(G1, G2)


vf2pp_is_isomorphic.can_run = _can_run_vf2pp
vf2pp_is_isomorphic.multigraph = True


def _vf2_mappings(G1, G2):
    """Yield ``{G1 node: G2 node}`` isomorphism mappings, or nothing.

    NetworkX reports no mapping (rather than an error) for graphs of
    different directedness.
    """
    if G1.is_directed() != G2.is_directed():
        return
    left = as_rw_graph(G1)
    right = as_rw_graph(G2)
    if left.number_of_nodes() != right.number_of_nodes():
        return
    if left.number_of_edges() != right.number_of_edges():
        return
    if left.number_of_nodes() == 0:
        return  # NetworkX reports no mapping for two empty graphs
    left_ids = left.index_to_node
    right_ids = right.index_to_node
    for mapping in rx.vf2_mapping(left.rx_graph, right.rx_graph, id_order=False):
        yield {left_ids[a]: right_ids[b] for a, b in mapping.items()}


def vf2pp_isomorphism(G1, G2, node_label=None, default_label=None):
    """Return one structural isomorphism mapping, or None."""
    _ = node_label, default_label
    return next(_vf2_mappings(G1, G2), None)


vf2pp_isomorphism.can_run = _can_run_vf2pp
vf2pp_isomorphism.multigraph = True


def vf2pp_all_isomorphisms(G1, G2, node_label=None, default_label=None):
    """Yield every structural isomorphism mapping."""
    _ = node_label, default_label
    return _vf2_mappings(G1, G2)


vf2pp_all_isomorphisms.can_run = _can_run_vf2pp
