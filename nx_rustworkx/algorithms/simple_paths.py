"""Simple path enumeration dispatched to rustworkx."""

from __future__ import annotations

import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    reject_multigraph,
    remap_nodes,
    require_node,
)

__all__ = ["all_simple_paths"]


def _can_run_all_simple_paths(G, source, target, cutoff=None, **kwargs):
    _ = source
    reason = reject_multigraph(G)
    if reason:
        return reason
    if isinstance(target, (list, set, frozenset, tuple)) and target not in G:
        return "rustworkx all_simple_paths takes a single target"
    return True


def all_simple_paths(G, source, target, cutoff=None):
    """Yield every simple path between two nodes via rustworkx."""
    rwg = as_rw_graph(G)
    src = require_node(rwg, source, kind="Source")
    tgt = require_node(rwg, target, kind="Target")
    if src == tgt:
        # NetworkX yields the trivial path when source and target coincide.
        return iter([[source]])
    if cutoff is not None and cutoff < 1:
        return iter([])

    def _iter():
        # rustworkx counts nodes where NetworkX counts edges.
        paths = rx.all_simple_paths(
            rwg.rx_graph, src, tgt, cutoff=None if cutoff is None else cutoff + 1
        )
        for path in paths:
            yield remap_nodes(rwg, path)

    return _iter()


all_simple_paths.can_run = _can_run_all_simple_paths
