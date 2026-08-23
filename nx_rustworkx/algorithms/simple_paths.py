"""Simple path enumeration dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    remap_nodes,
    require_node,
)

__all__ = ["all_simple_paths"]


def _resolve_targets(rwg, target):
    """Mirror NetworkX: a single node, or an iterable whose missing nodes are
    silently skipped. A non-node, non-iterable target is NodeNotFound."""
    if rwg.has_node(target):
        return [rwg.node_to_index[target]]
    try:
        candidates = dict.fromkeys(target)  # dedup, keeping first-seen order
    except TypeError as exc:
        raise nx.NodeNotFound(f"target node {target} not in graph") from exc
    return [rwg.node_to_index[node] for node in candidates if node in rwg.node_to_index]


def all_simple_paths(G, source, target, cutoff=None):
    """Yield every simple path from ``source`` to the target node or nodes."""
    rwg = as_rw_graph(G)
    src = require_node(rwg, source, kind="Source")
    targets = _resolve_targets(rwg, target)
    if cutoff is not None and cutoff < 1:
        return iter([])

    def _iter():
        for tgt in targets:
            if tgt == src:
                # NetworkX yields the trivial path when source and target coincide.
                yield [source]
                continue
            # rustworkx counts nodes where NetworkX counts edges.
            paths = rx.all_simple_paths(
                rwg.rx_graph, src, tgt, cutoff=None if cutoff is None else cutoff + 1
            )
            for path in paths:
                yield remap_nodes(rwg, path)

    return _iter()


all_simple_paths.multigraph = True
