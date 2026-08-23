"""Behavior probes for the NetworkX versions this backend supports.

The package declares ``networkx>=3.4``, and a few functions changed shape inside
that range. Ask NetworkX's own implementation what it does once and cache the
answer, rather than comparing version strings: the behavior is what matters, and
a probe keeps working if a distribution backports or reverts a change.
"""

from __future__ import annotations

import warnings
from functools import lru_cache

import networkx as nx

__all__ = [
    "dominance_frontiers_includes_start",
    "hexagonal_lattice_periodic_is_clean",
    "hexagonal_lattice_positions_are_optional",
    "immediate_dominators_includes_start",
    "metric_closure_is_deprecated",
    "single_target_shortest_path_length_returns_dict",
    "star_graph_allows_directed",
]


def _orig(name):
    func = getattr(nx, name)
    return getattr(func, "orig_func", func)


@lru_cache(maxsize=None)
def immediate_dominators_includes_start() -> bool:
    """NetworkX 3.5 dropped the start node's self-domination from the result."""
    return 0 in _orig("immediate_dominators")(nx.DiGraph([(0, 1)]), 0)


@lru_cache(maxsize=None)
def dominance_frontiers_includes_start() -> bool:
    """NetworkX 3.5 started reporting the start node inside dominance frontiers."""
    result = _orig("dominance_frontiers")(nx.DiGraph([(0, 1), (1, 0)]), 0)
    return 0 in result[1]


@lru_cache(maxsize=None)
def metric_closure_is_deprecated() -> bool:
    """NetworkX 3.6 deprecated metric_closure for removal in 3.8."""
    from networkx.algorithms.approximation import steinertree

    func = getattr(steinertree.metric_closure, "orig_func", steinertree.metric_closure)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        func(nx.path_graph(2))
    return any(issubclass(w.category, DeprecationWarning) for w in caught)


@lru_cache(maxsize=None)
def hexagonal_lattice_positions_are_optional() -> bool:
    """NetworkX 3.6 started honoring ``with_positions=False`` in hex lattices."""
    G = _orig("hexagonal_lattice_graph")(1, 1, with_positions=False)
    return all("pos" not in data for _, data in G.nodes(data=True))


@lru_cache(maxsize=None)
def hexagonal_lattice_periodic_is_clean() -> bool:
    """NetworkX 3.6 stopped storing contraction attrs on periodic hex lattices."""
    G = _orig("hexagonal_lattice_graph")(2, 2, periodic=True, with_positions=False)
    return all("contraction" not in data for _, data in G.nodes(data=True))


@lru_cache(maxsize=None)
def star_graph_allows_directed() -> bool:
    """NetworkX 3.6 started accepting a directed ``create_using`` in star_graph."""
    try:
        _orig("star_graph")(1, create_using=nx.DiGraph)
    except nx.NetworkXError:
        return False
    return True


@lru_cache(maxsize=None)
def single_target_shortest_path_length_returns_dict() -> bool:
    """NetworkX 3.5 changed this from an iterator of pairs to a dict."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        result = _orig("single_target_shortest_path_length")(nx.DiGraph([(0, 1)]), 1)
    return isinstance(result, dict)
