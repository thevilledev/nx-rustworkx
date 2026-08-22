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
    "immediate_dominators_includes_start",
    "single_target_shortest_path_length_returns_dict",
]


def _orig(name):
    func = getattr(nx, name)
    return getattr(func, "orig_func", func)


@lru_cache(maxsize=None)
def immediate_dominators_includes_start() -> bool:
    """NetworkX 3.5 dropped the start node's self-domination from the result."""
    return 0 in _orig("immediate_dominators")(nx.DiGraph([(0, 1)]), 0)


@lru_cache(maxsize=None)
def single_target_shortest_path_length_returns_dict() -> bool:
    """NetworkX 3.5 changed this from an iterator of pairs to a dict."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        result = _orig("single_target_shortest_path_length")(nx.DiGraph([(0, 1)]), 1)
    return isinstance(result, dict)
