"""Cycle enumeration dispatched to rustworkx."""

from __future__ import annotations

import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    can_run_directed,
    can_run_undirected,
    remap_nodes,
    require_directed,
    require_undirected,
)

__all__ = ["simple_cycles", "cycle_basis"]


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
