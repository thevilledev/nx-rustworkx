"""Link-analysis algorithms dispatched to rustworkx."""

from __future__ import annotations

from nx_rustworkx.algorithms._utils import (
    as_directed_rx,
    as_rw_graph,
    default_can_run,
    edge_weight_fn,
    remap_scores,
)

__all__ = ["pagerank"]


def _remap_optional_dict(rwg, values):
    if values is None:
        return None
    return {rwg.node_to_index[node]: float(score) for node, score in values.items()}


def pagerank(
    G,
    alpha=0.85,
    personalization=None,
    max_iter=100,
    tol=1.0e-6,
    nstart=None,
    weight="weight",
    dangling=None,
):
    """PageRank via rustworkx. Undirected graphs are treated as bidirectional."""
    import rustworkx as rx

    rwg = as_rw_graph(G)
    scores = rx.pagerank(
        as_directed_rx(rwg),
        alpha=alpha,
        weight_fn=edge_weight_fn(weight),
        nstart=_remap_optional_dict(rwg, nstart),
        personalization=_remap_optional_dict(rwg, personalization),
        tol=tol,
        max_iter=max_iter,
        dangling=_remap_optional_dict(rwg, dangling),
    )
    return remap_scores(rwg, scores)


pagerank.can_run = default_can_run
