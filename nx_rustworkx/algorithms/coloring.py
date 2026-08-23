"""Graph coloring dispatched to rustworkx."""

from __future__ import annotations

import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph, can_run_undirected, require_undirected

__all__ = ["greedy_color"]

# rustworkx's Degree strategy colors nodes in decreasing degree order, which is
# what NetworkX calls largest_first; Saturation is DSATUR and IndependentSet is
# the greedy independent-set strategy.
_STRATEGIES = {
    "largest_first": rx.ColoringStrategy.Degree,
    "saturation_largest_first": rx.ColoringStrategy.Saturation,
    "DSATUR": rx.ColoringStrategy.Saturation,
    "independent_set": rx.ColoringStrategy.IndependentSet,
}


def _can_run_greedy_color(G, strategy="largest_first", interchange=False, **kwargs):
    reason = can_run_undirected(G)
    if reason is not True:
        return reason
    if callable(strategy) or strategy not in _STRATEGIES:
        return f"rustworkx greedy_color does not implement strategy={strategy!r}"
    if interchange:
        return "rustworkx greedy_color does not support interchange"
    return True


def greedy_color(G, strategy="largest_first", interchange=False):
    """Color the graph greedily with the requested rustworkx strategy."""
    _ = interchange
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    index_to_node = rwg.index_to_node
    colors = rx.graph_greedy_color(rwg.rx_graph, strategy=_STRATEGIES[strategy])
    return {index_to_node[i]: int(color) for i, color in colors.items()}


greedy_color.can_run = _can_run_greedy_color
