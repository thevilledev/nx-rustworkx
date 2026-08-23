"""Eccentricity-family distance measures via rustworkx's distance matrix."""

from __future__ import annotations

import math

import networkx as nx
import numpy as np
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    default_should_run,
    edge_weight_fn,
    reject_callable_weight,
)
from nx_rustworkx.algorithms.shortest_paths import _lengths_from_source

__all__ = ["eccentricity", "diameter", "radius", "center", "periphery"]

#: Automatic dispatch declines the all-pairs computation above this many
#: nodes: the distance matrix at the limit is 8 * 4096**2 bytes, ~134 MB.
#: ``backend="rustworkx"`` still runs, accepting the memory cost.
MAX_MATRIX_NODES = 4096


def _disconnected_error(rwg) -> nx.NetworkXError:
    if rwg.is_directed():
        return nx.NetworkXError(
            "Found infinite path length because the digraph is not strongly connected"
        )
    return nx.NetworkXError("Found infinite path length because the graph is not connected")


def _all_eccentricities(rwg, weight) -> dict:
    n = rwg.number_of_nodes()
    index_to_node = rwg.index_to_node
    if weight is None:
        matrix = rx.distance_matrix(rwg.rx_graph, null_value=math.inf)
        if n and bool(np.isinf(matrix).any()):
            raise _disconnected_error(rwg)
        row_max = matrix.max(axis=1) if n else []
        return {index_to_node[i]: int(row_max[i]) for i in range(n)}
    mapping = rx.all_pairs_dijkstra_path_lengths(rwg.rx_graph, edge_weight_fn(weight))
    ecc = {}
    for i in range(n):
        row = mapping[i]
        # Rows exclude the source itself and unreachable nodes.
        if len(row) != n - 1:
            raise _disconnected_error(rwg)
        ecc[index_to_node[i]] = max(row.values(), default=0.0)
    return ecc


def _eccentricity_of(rwg, node, weight):
    cast = int if weight is None else float
    lengths = _lengths_from_source(rwg, node, weight, "dijkstra", cast=cast)
    if len(lengths) != rwg.number_of_nodes():
        raise _disconnected_error(rwg)
    return max(lengths.values())


def _requested_nodes(rwg, v) -> list:
    """NetworkX's nbunch semantics: iterate ``v`` and keep the members."""
    try:
        candidates = iter(v)
    except TypeError:
        raise nx.NetworkXError(f"Node {v} is not in the graph.") from None
    return [node for node in candidates if rwg.has_node(node)]


def _can_run_eccentricity(G, v=None, sp=None, weight=None):
    _ = v
    if sp is not None:
        return "a precomputed sp falls back to NetworkX"
    return reject_callable_weight(weight) or True


def _matrix_size_reason(G) -> str | None:
    n = G.number_of_nodes()
    if n > MAX_MATRIX_NODES:
        mb = 8 * n * n // 2**20
        return (
            f"the all-pairs distance matrix for n={n} needs ~{mb} MB; "
            'pass backend="rustworkx" to accept the memory cost'
        )
    return None


def _should_run_eccentricity(G, v=None, sp=None, weight=None):
    _ = sp, weight
    if v is None:
        reason = _matrix_size_reason(G)
        if reason:
            return reason
    return default_should_run((G,), {})


def eccentricity(G, v=None, sp=None, weight=None):
    """Eccentricities from rustworkx's all-pairs distances.

    A single node or an nbunch computes per-source lengths instead of the
    full matrix.
    """
    _ = sp  # can_run declines a supplied sp
    rwg = as_rw_graph(G)
    if v is None:
        return _all_eccentricities(rwg, weight)
    if rwg.has_node(v):
        return _eccentricity_of(rwg, v, weight)
    return {node: _eccentricity_of(rwg, node, weight) for node in _requested_nodes(rwg, v)}


eccentricity.can_run = _can_run_eccentricity
eccentricity.should_run = _should_run_eccentricity
eccentricity.multigraph = True


def _can_run_extremes(G, e=None, usebounds=False, weight=None):
    _ = usebounds
    if e is not None:
        return "a precomputed eccentricity dict falls back to NetworkX"
    return reject_callable_weight(weight) or True


def _should_run_extremes(G, e=None, usebounds=False, weight=None):
    _ = e, usebounds, weight
    return _matrix_size_reason(G) or default_should_run((G,), {})


def diameter(G, e=None, usebounds=False, weight=None):
    """Maximum eccentricity; ``usebounds`` only selects NetworkX's algorithm."""
    _ = e, usebounds
    return max(eccentricity(G, weight=weight).values())


diameter.can_run = _can_run_extremes
diameter.should_run = _should_run_extremes
diameter.multigraph = True


def radius(G, e=None, usebounds=False, weight=None):
    """Minimum eccentricity; ``usebounds`` only selects NetworkX's algorithm."""
    _ = e, usebounds
    return min(eccentricity(G, weight=weight).values())


radius.can_run = _can_run_extremes
radius.should_run = _should_run_extremes
radius.multigraph = True


def center(G, e=None, usebounds=False, weight=None):
    """Nodes whose eccentricity equals the radius, in G's node order."""
    _ = e, usebounds
    ecc = eccentricity(G, weight=weight)
    r = min(ecc.values())
    return [node for node in ecc if ecc[node] == r]


center.can_run = _can_run_extremes
center.should_run = _should_run_extremes
center.multigraph = True


def periphery(G, e=None, usebounds=False, weight=None):
    """Nodes whose eccentricity equals the diameter, in G's node order."""
    _ = e, usebounds
    ecc = eccentricity(G, weight=weight)
    d = max(ecc.values())
    return [node for node in ecc if ecc[node] == d]


periphery.can_run = _can_run_extremes
periphery.should_run = _should_run_extremes
periphery.multigraph = True
