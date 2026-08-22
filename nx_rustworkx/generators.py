"""Graph constructors dispatched by NetworkX class and generator priority."""

from __future__ import annotations

import networkx as nx

from nx_rustworkx.graph import RustworkxGraph

__all__ = [
    "graph__new__",
    "digraph__new__",
    "empty_graph",
    "from_edgelist",
    "GENERATORS",
]


def _is_multigraph_spec(obj) -> bool:
    if obj is None:
        return False
    if isinstance(obj, type):
        return issubclass(obj, nx.MultiGraph)
    return bool(getattr(obj, "is_multigraph", lambda: False)())


def _is_directed_spec(obj) -> bool:
    if obj is None:
        return False
    if isinstance(obj, type):
        return issubclass(obj, nx.DiGraph)
    return bool(obj.is_directed())


def _reject_multi(*specs):
    for spec in specs:
        if _is_multigraph_spec(spec):
            return "nx-rustworkx does not support MultiGraph or MultiDiGraph"
    return None


def _new_graph(*, directed: bool, incoming_graph_data=None, attr=None):
    attrs = dict(attr) if attr else {}
    attrs.pop("backend", None)
    return RustworkxGraph.from_incoming(
        incoming_graph_data,
        directed=directed,
        graph_attrs=attrs,
    )


def _can_run_new(cls, incoming_graph_data=None, **attr):
    _ = cls, attr
    if incoming_graph_data is not None and hasattr(incoming_graph_data, "is_multigraph"):
        if incoming_graph_data.is_multigraph():
            return "nx-rustworkx does not support MultiGraph or MultiDiGraph"
    return True


def graph__new__(cls, incoming_graph_data=None, **attr):
    """``nx.Graph(..., backend="rustworkx")`` constructor."""
    _ = cls
    return _new_graph(
        directed=False,
        incoming_graph_data=incoming_graph_data,
        attr=attr,
    )


graph__new__.can_run = _can_run_new
graph__new__.should_run = lambda *args, **kwargs: True


def digraph__new__(cls, incoming_graph_data=None, **attr):
    """``nx.DiGraph(..., backend="rustworkx")`` constructor."""
    _ = cls
    return _new_graph(
        directed=True,
        incoming_graph_data=incoming_graph_data,
        attr=attr,
    )


digraph__new__.can_run = _can_run_new
digraph__new__.should_run = lambda *args, **kwargs: True


def _can_run_empty(n=0, create_using=None, default=None, **kwargs):
    _ = n, kwargs
    return _reject_multi(create_using, default) or True


def empty_graph(n=0, create_using=None, default=None):
    """Empty rustworkx graph with ``n`` nodes (or an iterable of node IDs)."""
    reason = _reject_multi(create_using, default)
    if reason:
        raise nx.NetworkXError(reason)

    if isinstance(create_using, RustworkxGraph):
        G = create_using
        G.clear()
    else:
        directed = _is_directed_spec(create_using)
        if create_using is None:
            directed = _is_directed_spec(default)
        G = RustworkxGraph.empty(directed=directed)

    if isinstance(n, int):
        G.add_nodes_from(range(n))
    else:
        G.add_nodes_from(n)
    return G


empty_graph.can_run = _can_run_empty
empty_graph.should_run = lambda *args, **kwargs: True


def _can_run_edgelist(edgelist, create_using=None, **kwargs):
    _ = edgelist, kwargs
    return _reject_multi(create_using) or True


def from_edgelist(edgelist, create_using=None):
    """Build a rustworkx graph from an edgelist."""
    G = empty_graph(0, create_using=create_using)
    G.add_edges_from(edgelist)
    return G


from_edgelist.can_run = _can_run_edgelist
from_edgelist.should_run = lambda *args, **kwargs: True

GENERATORS = [
    "graph__new__",
    "digraph__new__",
    "empty_graph",
    "from_edgelist",
]
