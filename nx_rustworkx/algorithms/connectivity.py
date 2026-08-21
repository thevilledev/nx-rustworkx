"""Connectivity algorithms dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph, reject_multigraph, remap_components

__all__ = [
    "is_connected",
    "is_weakly_connected",
    "connected_components",
    "weakly_connected_components",
    "number_connected_components",
]


def _null_graph_guard(rwg):
    if rwg.number_of_nodes() == 0:
        raise nx.NetworkXPointlessConcept(
            "Connectivity is undefined for the null graph."
        )


def _can_run_undirected(G, **kwargs):
    reason = reject_multigraph(G)
    if reason:
        return reason
    if G.is_directed():
        return "not implemented for directed type"
    return True


def _can_run_directed(G, **kwargs):
    reason = reject_multigraph(G)
    if reason:
        return reason
    if not G.is_directed():
        return "not implemented for undirected type"
    return True


def is_connected(G):
    """Return True if the undirected graph is connected."""
    rwg = as_rw_graph(G)
    _null_graph_guard(rwg)
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")
    try:
        return bool(rx.is_connected(rwg.rx_graph))
    except rx.NullGraph as exc:
        raise nx.NetworkXPointlessConcept(
            "Connectivity is undefined for the null graph."
        ) from exc


is_connected.can_run = _can_run_undirected


def is_weakly_connected(G):
    """Return True if the directed graph is weakly connected."""
    rwg = as_rw_graph(G)
    _null_graph_guard(rwg)
    if not rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for undirected type")
    try:
        return bool(rx.is_weakly_connected(rwg.rx_graph))
    except rx.NullGraph as exc:
        raise nx.NetworkXPointlessConcept(
            "Connectivity is undefined for the null graph."
        ) from exc


is_weakly_connected.can_run = _can_run_directed


def connected_components(G):
    """Generate connected components of an undirected graph."""
    rwg = as_rw_graph(G)
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")
    return iter(remap_components(rwg, rx.connected_components(rwg.rx_graph)))


connected_components.can_run = _can_run_undirected


def weakly_connected_components(G):
    """Generate weakly connected components of a directed graph."""
    rwg = as_rw_graph(G)
    if not rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for undirected type")
    return iter(remap_components(rwg, rx.weakly_connected_components(rwg.rx_graph)))


weakly_connected_components.can_run = _can_run_directed


def number_connected_components(G):
    """Return the number of connected components in an undirected graph."""
    rwg = as_rw_graph(G)
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")
    return int(rx.number_connected_components(rwg.rx_graph))


number_connected_components.can_run = _can_run_undirected
