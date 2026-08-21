"""Centrality algorithms dispatched to rustworkx."""

from __future__ import annotations

import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    default_can_run,
    edge_weight_fn,
    reject_callable_weight,
    reject_multigraph,
    remap_scores,
)

__all__ = [
    "betweenness_centrality",
    "edge_betweenness_centrality",
    "closeness_centrality",
    "eigenvector_centrality",
]


def _can_run_betweenness(
    G,
    k=None,
    normalized=True,
    weight=None,
    endpoints=False,
    seed=None,
    **kwargs,
):
    reason = reject_multigraph(G)
    if reason:
        return reason
    if k is not None:
        return "rustworkx betweenness_centrality does not support k-sampling"
    if weight is not None:
        return reject_callable_weight(weight) or (
            "rustworkx betweenness_centrality is unweighted only"
        )
    return True


def betweenness_centrality(
    G,
    k=None,
    normalized=True,
    weight=None,
    endpoints=False,
    seed=None,
    *,
    parallel_threshold=50,
    **kwargs,
):
    """Unweighted Brandes betweenness via rustworkx."""
    _ = k, weight, seed, kwargs
    rwg = as_rw_graph(G)
    scores = rx.betweenness_centrality(
        rwg.rx_graph,
        normalized=normalized,
        endpoints=endpoints,
        parallel_threshold=parallel_threshold,
    )
    return remap_scores(rwg, scores)


betweenness_centrality.can_run = _can_run_betweenness


def _can_run_edge_betweenness(
    G,
    k=None,
    normalized=True,
    weight=None,
    seed=None,
    **kwargs,
):
    reason = reject_multigraph(G)
    if reason:
        return reason
    if k is not None:
        return "rustworkx edge_betweenness_centrality does not support k-sampling"
    if weight is not None:
        return reject_callable_weight(weight) or (
            "rustworkx edge_betweenness_centrality is unweighted only"
        )
    return True


def edge_betweenness_centrality(
    G,
    k=None,
    normalized=True,
    weight=None,
    seed=None,
    *,
    parallel_threshold=50,
    **kwargs,
):
    """Unweighted edge betweenness via rustworkx."""
    _ = k, weight, seed, kwargs
    rwg = as_rw_graph(G)
    scores = rx.edge_betweenness_centrality(
        rwg.rx_graph,
        normalized=normalized,
        parallel_threshold=parallel_threshold,
    )
    edge_map = rwg.rx_graph.edge_index_map()
    index_to_node = rwg.index_to_node
    out = {}
    for edge_index, score in scores.items():
        src, tgt, _data = edge_map[edge_index]
        out[(index_to_node[src], index_to_node[tgt])] = float(score)
    return out


edge_betweenness_centrality.can_run = _can_run_edge_betweenness


def _can_run_closeness(G, u=None, distance=None, wf_improved=True, **kwargs):
    reason = reject_multigraph(G)
    if reason:
        return reason
    if distance is not None:
        return reject_callable_weight(distance) or (
            "rustworkx closeness_centrality is unweighted only"
        )
    return True


def closeness_centrality(
    G,
    u=None,
    distance=None,
    wf_improved=True,
    *,
    parallel_threshold=50,
    **kwargs,
):
    """Unweighted closeness via rustworkx."""
    _ = distance, kwargs
    rwg = as_rw_graph(G)
    scores = rx.closeness_centrality(
        rwg.rx_graph,
        wf_improved=wf_improved,
        parallel_threshold=parallel_threshold,
    )
    remapped = remap_scores(rwg, scores)
    if u is not None:
        return remapped[u]
    return remapped


closeness_centrality.can_run = _can_run_closeness


def _can_run_eigenvector(
    G,
    max_iter=100,
    tol=1.0e-6,
    nstart=None,
    weight=None,
    **kwargs,
):
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    if nstart is not None:
        return "rustworkx eigenvector_centrality does not support nstart"
    return True


def eigenvector_centrality(
    G,
    max_iter=100,
    tol=1.0e-6,
    nstart=None,
    weight=None,
    **kwargs,
):
    """Eigenvector centrality via rustworkx power iteration."""
    _ = nstart, kwargs
    rwg = as_rw_graph(G)
    scores = rx.eigenvector_centrality(
        rwg.rx_graph,
        weight_fn=edge_weight_fn(weight),
        max_iter=max_iter,
        tol=tol,
    )
    return remap_scores(rwg, scores)


eigenvector_centrality.can_run = _can_run_eigenvector
