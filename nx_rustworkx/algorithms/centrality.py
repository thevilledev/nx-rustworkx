"""Centrality algorithms dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_directed_rx,
    as_rw_graph,
    can_run_directed,
    default_can_run,
    edge_weight_fn,
    reject_callable_weight,
    reject_multigraph,
    remap_scores,
    require_directed,
    require_nodes,
)

__all__ = [
    "betweenness_centrality",
    "closeness_centrality",
    "edge_betweenness_centrality",
    "eigenvector_centrality",
    "degree_centrality",
    "in_degree_centrality",
    "out_degree_centrality",
    "katz_centrality",
    "katz_centrality_numpy",
    "hits",
    "group_betweenness_centrality",
    "group_closeness_centrality",
    "group_degree_centrality",
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
        normalized=bool(normalized),
        endpoints=bool(endpoints),
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
        normalized=bool(normalized),
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
    if callable(distance):
        return "nx-rustworkx does not support custom weight callables"
    return True


def _distance_as_strength(distance):
    """Turn an edge-distance read into the connection strength rustworkx's
    Newman closeness kernel expects: ``strength = 1 / distance``."""
    import math

    weight_fn = edge_weight_fn(distance)

    def _fn(data):
        value = weight_fn(data)
        return math.inf if value == 0 else 1.0 / value

    return _fn


def closeness_centrality(
    G,
    u=None,
    distance=None,
    wf_improved=True,
    *,
    parallel_threshold=50,
    **kwargs,
):
    """Closeness via rustworkx; a string ``distance`` uses the weighted kernel."""
    _ = kwargs
    rwg = as_rw_graph(G)
    if distance is None:
        scores = rx.closeness_centrality(
            rwg.rx_graph,
            wf_improved=bool(wf_improved),
            parallel_threshold=parallel_threshold,
        )
    else:
        scores = rx.newman_weighted_closeness_centrality(
            rwg.rx_graph,
            _distance_as_strength(distance),
            wf_improved=bool(wf_improved),
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
    if rwg.number_of_nodes() == 0:
        raise nx.NetworkXPointlessConcept("cannot compute centrality for the null graph")
    try:
        scores = rx.eigenvector_centrality(
            rwg.rx_graph,
            weight_fn=edge_weight_fn(weight),
            max_iter=max_iter,
            tol=tol,
        )
    except rx.FailedToConverge as exc:
        raise nx.PowerIterationFailedConvergence(max_iter) from exc
    return remap_scores(rwg, scores)


eigenvector_centrality.can_run = _can_run_eigenvector


def _can_run_degree(G, *args, **kwargs):
    return reject_multigraph(G) or True


def _trivial_degree_centrality(rwg):
    """NetworkX reports 1 for every node when the graph has at most one node."""
    if rwg.number_of_nodes() <= 1:
        return {node: 1 for node in rwg.index_to_node}
    return None


def degree_centrality(G):
    """Degree centrality via rustworkx."""
    rwg = as_rw_graph(G)
    trivial = _trivial_degree_centrality(rwg)
    if trivial is not None:
        return trivial
    return remap_scores(rwg, rx.degree_centrality(rwg.rx_graph))


degree_centrality.can_run = _can_run_degree


def in_degree_centrality(G):
    """In-degree centrality via rustworkx. Directed graphs only."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    trivial = _trivial_degree_centrality(rwg)
    if trivial is not None:
        return trivial
    return remap_scores(rwg, rx.in_degree_centrality(rwg.rx_graph))


in_degree_centrality.can_run = can_run_directed


def out_degree_centrality(G):
    """Out-degree centrality via rustworkx. Directed graphs only."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    trivial = _trivial_degree_centrality(rwg)
    if trivial is not None:
        return trivial
    return remap_scores(rwg, rx.out_degree_centrality(rwg.rx_graph))


out_degree_centrality.can_run = can_run_directed


def _can_run_katz(
    G,
    alpha=0.1,
    beta=1.0,
    max_iter=1000,
    tol=1.0e-6,
    nstart=None,
    normalized=True,
    weight=None,
    **kwargs,
):
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    if nstart is not None:
        return "rustworkx katz_centrality does not support nstart"
    if not normalized:
        return "rustworkx katz_centrality always normalizes the result"
    return True


def _katz_beta(rwg, beta):
    """Translate NetworkX ``beta`` into the rustworkx index-keyed form."""
    if not isinstance(beta, dict):
        try:
            return float(beta)
        except (TypeError, ValueError) as exc:
            raise nx.NetworkXError("beta must be a number or a dictionary") from exc
    try:
        return {rwg.node_to_index[node]: float(value) for node, value in beta.items()}
    except KeyError as exc:
        raise nx.NetworkXError("beta dictionary must have a value for every node") from exc


def _katz(G, alpha, beta, max_iter, tol, weight):
    rwg = as_rw_graph(G)
    if rwg.number_of_nodes() == 0:
        return {}
    resolved = _katz_beta(rwg, beta)
    if isinstance(resolved, dict) and len(resolved) != rwg.number_of_nodes():
        raise nx.NetworkXError("beta dictionary must have a value for every node")
    try:
        scores = rx.katz_centrality(
            rwg.rx_graph,
            alpha=alpha,
            beta=resolved,
            weight_fn=edge_weight_fn(weight),
            max_iter=max_iter,
            tol=tol,
        )
    except rx.FailedToConverge as exc:
        raise nx.PowerIterationFailedConvergence(max_iter) from exc
    return remap_scores(rwg, scores)


def katz_centrality(
    G,
    alpha=0.1,
    beta=1.0,
    max_iter=1000,
    tol=1.0e-6,
    nstart=None,
    normalized=True,
    weight=None,
):
    """Katz centrality via rustworkx power iteration. Always L2-normalized."""
    _ = nstart, normalized
    return _katz(G, alpha, beta, max_iter, tol, weight)


katz_centrality.can_run = _can_run_katz


def _can_run_katz_numpy(G, alpha=0.1, beta=1.0, normalized=True, weight=None, **kwargs):
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    if not normalized:
        return "rustworkx katz_centrality always normalizes the result"
    return True


def katz_centrality_numpy(G, alpha=0.1, beta=1.0, normalized=True, weight=None):
    """Katz centrality via rustworkx. Matches NetworkX's numpy solver values."""
    _ = normalized
    return _katz(G, alpha, beta, 1000, 1.0e-12, weight)


katz_centrality_numpy.can_run = _can_run_katz_numpy


def _can_run_hits(G, max_iter=100, tol=1.0e-8, nstart=None, normalized=True, **kwargs):
    reason = reject_multigraph(G)
    if reason:
        return reason
    if not normalized:
        return "rustworkx hits always normalizes the result"
    return True


def hits(G, max_iter=100, tol=1.0e-8, nstart=None, normalized=True):
    """HITS hubs and authorities via rustworkx. Undirected edges count both ways."""
    _ = normalized
    rwg = as_rw_graph(G)
    if rwg.number_of_nodes() == 0:
        return {}, {}
    remapped_nstart = None
    if nstart is not None:
        remapped_nstart = {rwg.node_to_index[node]: float(value) for node, value in nstart.items()}
    try:
        hubs, authorities = rx.hits(
            as_directed_rx(rwg),
            weight_fn=edge_weight_fn("weight"),
            nstart=remapped_nstart,
            tol=tol,
            max_iter=max_iter,
        )
    except rx.FailedToConverge as exc:
        raise nx.PowerIterationFailedConvergence(max_iter) from exc
    return remap_scores(rwg, hubs), remap_scores(rwg, authorities)


hits.can_run = _can_run_hits


def _is_node(rwg, value) -> bool:
    """``value in G`` semantics: unhashable values are simply not nodes."""
    try:
        return value in rwg.node_to_index
    except TypeError:
        return False


def _resolve_groups(rwg, C):
    """Mirror NetworkX: ``C`` is either one group or a list of groups."""
    groups = list(C)
    if any(_is_node(rwg, el) for el in groups):
        return [groups], False
    return [list(group) for group in groups], True


def _can_run_group_betweenness(G, C, normalized=True, weight=None, endpoints=False, **kwargs):
    reason = reject_multigraph(G)
    if reason:
        return reason
    if weight is not None:
        return reject_callable_weight(weight) or (
            "rustworkx group_betweenness_centrality is unweighted only"
        )
    if endpoints:
        return "rustworkx group_betweenness_centrality does not support endpoints"
    return True


def group_betweenness_centrality(
    G,
    C,
    normalized=True,
    weight=None,
    endpoints=False,
    *,
    parallel_threshold=50,
):
    """Group betweenness centrality via rustworkx. Unweighted only."""
    _ = weight, endpoints
    rwg = as_rw_graph(G)
    groups, many = _resolve_groups(rwg, C)
    scores = [
        float(
            rx.group_betweenness_centrality(
                rwg.rx_graph,
                require_nodes(rwg, group, kind="C node"),
                normalized=bool(normalized),
                parallel_threshold=parallel_threshold,
            )
        )
        for group in groups
    ]
    return scores if many else scores[0]


group_betweenness_centrality.can_run = _can_run_group_betweenness


def _can_run_group_closeness(G, S, weight=None, **kwargs):
    reason = reject_multigraph(G)
    if reason:
        return reason
    if weight is not None:
        return reject_callable_weight(weight) or (
            "rustworkx group_closeness_centrality is unweighted only"
        )
    return True


def group_closeness_centrality(G, S, weight=None):
    """Group closeness centrality via rustworkx. Unweighted only."""
    _ = weight
    rwg = as_rw_graph(G)
    return float(rx.group_closeness_centrality(rwg.rx_graph, require_nodes(rwg, S, kind="S node")))


group_closeness_centrality.can_run = _can_run_group_closeness


def group_degree_centrality(G, S):
    """Group degree centrality via rustworkx."""
    rwg = as_rw_graph(G)
    return float(rx.group_degree_centrality(rwg.rx_graph, require_nodes(rwg, S, kind="S node")))


group_degree_centrality.can_run = _can_run_degree
