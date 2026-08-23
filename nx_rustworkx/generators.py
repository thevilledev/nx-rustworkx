"""Graph constructors dispatched by NetworkX class and generator priority."""

from __future__ import annotations

import math
import numbers

import networkx as nx
import numpy as np
import rustworkx as rx
from rustworkx import generators as rxgen

from nx_rustworkx import _compat
from nx_rustworkx.graph import RustworkxGraph

__all__ = [
    "graph__new__",
    "digraph__new__",
    "empty_graph",
    "from_edgelist",
    "path_graph",
    "cycle_graph",
    "star_graph",
    "complete_graph",
    "barbell_graph",
    "lollipop_graph",
    "binomial_tree",
    "full_rary_tree",
    "karate_club_graph",
    "grid_2d_graph",
    "gnp_random_graph",
    "fast_gnp_random_graph",
    "gnm_random_graph",
    "dense_gnm_random_graph",
    "random_regular_graph",
    "stochastic_block_model",
    "random_geometric_graph",
    "barabasi_albert_graph",
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


def _validate_create_using(*specs) -> None:
    """Raise the TypeError NetworkX raises for non-graph ``create_using``."""
    for spec in specs:
        if spec is None or isinstance(spec, type):
            continue
        if not hasattr(spec, "adj"):
            raise TypeError("create_using is not a valid NetworkX graph type or instance")


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


def _should_run_always(*args, **kwargs):
    _ = args, kwargs
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
graph__new__.should_run = _should_run_always


def digraph__new__(cls, incoming_graph_data=None, **attr):
    """``nx.DiGraph(..., backend="rustworkx")`` constructor."""
    _ = cls
    return _new_graph(
        directed=True,
        incoming_graph_data=incoming_graph_data,
        attr=attr,
    )


digraph__new__.can_run = _can_run_new
digraph__new__.should_run = _should_run_always


def _can_run_empty(n=0, create_using=None, default=None, **kwargs):
    _ = n, kwargs
    return _reject_multi(create_using, default) or True


def empty_graph(n=0, create_using=None, default=None):
    """Empty rustworkx graph with ``n`` nodes (or an iterable of node IDs)."""
    _validate_create_using(create_using, default)
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
empty_graph.should_run = _should_run_always


def _can_run_edgelist(edgelist, create_using=None, **kwargs):
    _ = edgelist, kwargs
    return _reject_multi(create_using) or True


def from_edgelist(edgelist, create_using=None):
    """Build a rustworkx graph from an edgelist."""
    G = empty_graph(0, create_using=create_using)
    G.add_edges_from(edgelist)
    return G


from_edgelist.can_run = _can_run_edgelist
from_edgelist.should_run = _should_run_always


# --- rustworkx-kernel generators ------------------------------------------
#
# Each of these builds the graph in Rust and wraps it with the node-identity
# map, so the result is exactly NetworkX's graph but conversion-free for the
# rest of the pipeline. ``create_using`` selects directedness only; the return
# is always a ``RustworkxGraph``, never the passed-in instance, matching
# ``empty_graph`` above. The NetworkX parity harness strict-compares every one
# of these against NetworkX's own output.


def _nodes_list(n):
    """NetworkX's ``nodes_or_number`` convention: an int means ``range(n)``."""
    if isinstance(n, numbers.Integral):
        if n < 0:
            raise nx.NetworkXError(f"Negative number of nodes not valid: {n}")
        return range(int(n))
    return list(n)


def _empty_container(directed: bool, num_nodes: int = 0):
    if directed:
        return rxgen.directed_empty_graph(num_nodes, multigraph=False)
    return rxgen.empty_graph(num_nodes, multigraph=False)


def _wrap(rx_graph, nodes, *, directed: bool):
    """Wrap a kernel-built graph whose indices align with ``nodes``."""
    index_to_node = list(nodes)
    return RustworkxGraph(
        rx_graph,
        {node: i for i, node in enumerate(index_to_node)},
        index_to_node,
        directed=directed,
    )


def _raise_for_multi(create_using) -> None:
    _validate_create_using(create_using)
    reason = _reject_multi(create_using)
    if reason:
        raise nx.NetworkXError(reason)


def _can_run_n_create(n=None, create_using=None, **kwargs):
    _ = n, kwargs
    return _reject_multi(create_using) or True


def _can_run_undirected_pair(m=None, n=None, create_using=None, **kwargs):
    _ = m, n, kwargs
    reason = _reject_multi(create_using)
    if reason:
        return reason
    if _is_directed_spec(create_using):
        # NetworkX raises its own error for these; let it.
        return "not implemented for directed type"
    return True


def path_graph(n, create_using=None):
    """Path on ``n`` nodes (or the nodes of an iterable, in order)."""
    _raise_for_multi(create_using)
    nodes = _nodes_list(n)
    directed = _is_directed_spec(create_using)
    k = len(nodes)
    if k == 0:
        g = _empty_container(directed)
    elif directed:
        g = rxgen.directed_path_graph(k, multigraph=False)
    else:
        g = rxgen.path_graph(k, multigraph=False)
    return _wrap(g, nodes, directed=directed)


path_graph.can_run = _can_run_n_create
path_graph.should_run = _should_run_always


def cycle_graph(n, create_using=None):
    """Cycle on ``n`` nodes (or the nodes of an iterable, in order)."""
    _raise_for_multi(create_using)
    nodes = _nodes_list(n)
    directed = _is_directed_spec(create_using)
    k = len(nodes)
    if k == 0:
        g = _empty_container(directed)
    elif directed:
        g = rxgen.directed_cycle_graph(k, multigraph=False)
    elif k == 2:
        # NetworkX's 2-cycle collapses to a single undirected edge; the
        # rustworkx kernel emits a parallel pair here.
        g = rx.PyGraph(multigraph=False)
        g.add_nodes_from([None, None])
        g.add_edge(0, 1, None)
    else:
        g = rxgen.cycle_graph(k, multigraph=False)
    return _wrap(g, nodes, directed=directed)


cycle_graph.can_run = _can_run_n_create
cycle_graph.should_run = _should_run_always


def star_graph(n, create_using=None):
    """Star with center first: ``n`` leaves for an int, ``n[0]`` as center."""
    _raise_for_multi(create_using)
    directed = _is_directed_spec(create_using)
    if directed and not _compat.star_graph_allows_directed():
        raise nx.NetworkXError("Directed Graph not supported")
    nodes = range(len(_nodes_list(n)) + 1) if isinstance(n, numbers.Integral) else list(n)
    k = len(nodes)
    if k == 0:
        g = _empty_container(directed)
    elif directed:
        g = rxgen.directed_star_graph(k, multigraph=False)
    else:
        g = rxgen.star_graph(k, multigraph=False)
    return _wrap(g, nodes, directed=directed)


def _can_run_star(n=None, create_using=None, **kwargs):
    _ = n, kwargs
    reason = _reject_multi(create_using)
    if reason:
        return reason
    if _is_directed_spec(create_using) and not _compat.star_graph_allows_directed():
        # This NetworkX version raises its own error for directed stars.
        return "not implemented for directed type"
    return True


star_graph.can_run = _can_run_star
star_graph.should_run = _should_run_always


def complete_graph(n, create_using=None):
    """Complete graph on ``n`` nodes (or the nodes of an iterable)."""
    _raise_for_multi(create_using)
    nodes = _nodes_list(n)
    directed = _is_directed_spec(create_using)
    k = len(nodes)
    if k == 0:
        g = _empty_container(directed)
    elif directed:
        g = rxgen.directed_complete_graph(k, multigraph=False)
    else:
        g = rxgen.complete_graph(k, multigraph=False)
    return _wrap(g, nodes, directed=directed)


complete_graph.can_run = _can_run_n_create
complete_graph.should_run = _should_run_always


def barbell_graph(m1, m2, create_using=None):
    """Two complete graphs of ``m1`` nodes joined by an ``m2``-node path."""
    _raise_for_multi(create_using)
    if _is_directed_spec(create_using):
        raise nx.NetworkXError("Directed Graph not supported")
    if m1 < 2:
        raise nx.NetworkXError("Invalid graph description, m1 should be >=2")
    if m2 < 0:
        raise nx.NetworkXError("Invalid graph description, m2 should be >=0")
    g = rxgen.barbell_graph(int(m1), int(m2), multigraph=False)
    return _wrap(g, range(g.num_nodes()), directed=False)


barbell_graph.can_run = _can_run_undirected_pair
barbell_graph.should_run = _should_run_always


def lollipop_graph(m, n, create_using=None):
    """Complete graph on ``m`` nodes with an ``n``-node path attached."""
    _raise_for_multi(create_using)
    if _is_directed_spec(create_using):
        raise nx.NetworkXError("Directed Graph not supported")
    m_nodes = _nodes_list(m)
    candy = len(m_nodes)
    if candy < 2:
        raise nx.NetworkXError("Invalid description: m should indicate at least 2 nodes")
    n_list = _nodes_list(n)  # validates a negative int like NetworkX does
    if isinstance(m, numbers.Integral) and isinstance(n, numbers.Integral):
        n_nodes = range(candy, candy + len(n_list))
    else:
        n_nodes = n_list
    stick = len(n_nodes)
    labels = list(m_nodes) + list(n_nodes)
    if len(set(labels)) != candy + stick:
        raise nx.NetworkXError("Nodes must be distinct in containers m and n")
    g = rxgen.lollipop_graph(candy, stick, multigraph=False)
    return _wrap(g, labels, directed=False)


lollipop_graph.can_run = _can_run_undirected_pair
lollipop_graph.should_run = _should_run_always


def binomial_tree(n, create_using=None):
    """Binomial tree of order ``n`` (``2**n`` nodes)."""
    _raise_for_multi(create_using)
    directed = _is_directed_spec(create_using)
    if isinstance(n, numbers.Integral) and int(n) < 0:
        # NetworkX's loop over ``range(n)`` leaves the single seed node.
        g = _empty_container(directed, 1)
    elif directed:
        g = rxgen.directed_binomial_tree_graph(n, multigraph=False)
    else:
        g = rxgen.binomial_tree_graph(n, multigraph=False)
    return _wrap(g, range(g.num_nodes()), directed=directed)


binomial_tree.can_run = _can_run_n_create
binomial_tree.should_run = _should_run_always


def full_rary_tree(r, n, create_using=None):
    """Full ``r``-ary tree on ``n`` nodes."""
    _raise_for_multi(create_using)
    directed = _is_directed_spec(create_using)
    if isinstance(n, numbers.Integral) and n < 0:
        raise nx.NetworkXError(f"Negative number of nodes not valid: {n}")
    g = rxgen.full_rary_tree(r, n, multigraph=False)
    if directed:
        # NetworkX orients every edge parent-to-child, and parents always
        # carry the smaller index.
        d = rx.PyDiGraph(multigraph=False)
        d.add_nodes_from([None] * g.num_nodes())
        d.add_edges_from_no_data([(u, v) if u < v else (v, u) for u, v in g.edge_list()])
        g = d
    return _wrap(g, range(g.num_nodes()), directed=directed)


def _can_run_full_rary(r=None, n=None, create_using=None, **kwargs):
    _ = r, n, kwargs
    return _reject_multi(create_using) or True


full_rary_tree.can_run = _can_run_full_rary
full_rary_tree.should_run = _should_run_always


def karate_club_graph():
    """Zachary's Karate Club with the ``club`` attrs, weights, and name.

    The rustworkx kernel stores each node's club as its payload and each
    weight as a bare number; rebuild those as NetworkX attributes.
    """
    src = rxgen.karate_club_graph()
    g = rx.PyGraph(multigraph=False)
    k = src.num_nodes()
    g.add_nodes_from(range(k))
    g.add_edges_from([(u, v, {"weight": int(w)}) for u, v, w in src.weighted_edge_list()])
    return RustworkxGraph(
        g,
        {i: i for i in range(k)},
        list(range(k)),
        directed=False,
        graph_attrs={"name": "Zachary's Karate Club"},
        node_attrs={i: {"club": src.get_node_data(i)} for i in range(k)},
    )


karate_club_graph.can_run = _should_run_always
karate_club_graph.should_run = _should_run_always


def grid_2d_graph(m, n, periodic=False, create_using=None):
    """2D grid with NetworkX's ``(row, column)`` tuple node labels."""
    _raise_for_multi(create_using)
    if _is_directed_spec(create_using) or periodic:
        raise NotImplementedError(
            "nx-rustworkx implements grid_2d_graph for undirected, non-periodic grids"
        )
    rows = _nodes_list(m)
    cols = _nodes_list(n)
    if not rows or not cols:
        g = _empty_container(False)
        labels: list = []
    else:
        g = rxgen.grid_graph(rows=len(rows), cols=len(cols), multigraph=False)
        labels = [(i, j) for i in rows for j in cols]
    return _wrap(g, labels, directed=False)


def _can_run_grid_2d(m=None, n=None, periodic=False, create_using=None, **kwargs):
    _ = m, n, kwargs
    reason = _reject_multi(create_using)
    if reason:
        return reason
    if _is_directed_spec(create_using):
        return "directed grids fall back to NetworkX"
    if periodic:
        # Covers True and per-dimension tuples; NetworkX handles both.
        return "periodic grids fall back to NetworkX"
    return True


grid_2d_graph.can_run = _can_run_grid_2d
grid_2d_graph.should_run = _should_run_always

# --- random generators -----------------------------------------------------
#
# These sample with rustworkx's RNG, which cannot reproduce NetworkX's stream:
# the same seed yields a different, equally valid graph. Policy (see
# docs/design/native-generators.md): unseeded calls run natively; seeded calls
# raise NotImplementedError unless ``native_seeded_generators`` is enabled, so
# priority dispatch falls back to NetworkX's sampler (still returning a native
# graph through ``empty_graph``) while ``backend="rustworkx"`` surfaces the
# opt-in in the raised chain. ``can_run`` declines under NetworkX's parity
# harness, which strict-compares backend output against NetworkX's.

_SEEDED_GENERATORS_MSG = (
    "nx-rustworkx draws seeded random graphs from rustworkx's RNG, which "
    "yields a different (equally valid) graph than NetworkX's for the same "
    "seed; set nx.config.backends.rustworkx.native_seeded_generators = True "
    "to run seeded generators natively"
)


def _parity_harness_active() -> bool:
    """True while NetworkX's test suite compares backend output to NetworkX's."""
    dispatchable = getattr(nx.utils.backends, "_dispatchable", None)
    return bool(getattr(dispatchable, "_is_testing", False))


def _native_seeded_enabled() -> bool:
    try:
        return bool(nx.config.backends.rustworkx.native_seeded_generators)
    except Exception:
        return False


def _check_seed_policy(seed) -> None:
    """Reject an explicit seed unless the user opted into rustworkx's RNG."""
    if seed is not nx.utils.create_py_random_state(None) and not _native_seeded_enabled():
        raise NotImplementedError(_SEEDED_GENERATORS_MSG)


def _rx_seed(seed) -> int:
    """Derive a rustworkx seed from the RNG NetworkX normalized ``seed`` into.

    ``@py_random_state`` runs before dispatch, so ``seed`` always arrives as a
    ``random.Random``-compatible object. Drawing 64 bits is deterministic for
    a fixed user seed and fresh for the unseeded case.
    """
    getrandbits = getattr(seed, "getrandbits", None)
    if getrandbits is not None:
        return int(getrandbits(64))
    # A numpy-backed PythonRandomInterface has no getrandbits.
    return int(seed.randint(0, 2**32 - 1))


def _reject_create_using(create_using) -> None:
    if create_using is not None:
        raise NotImplementedError("nx-rustworkx random generators do not support create_using")


def _can_run_random_common(create_using):
    if _parity_harness_active():
        return (
            "the NetworkX parity harness compares backend graphs to NetworkX's; "
            "random samples cannot match its RNG stream"
        )
    if create_using is not None:
        return "create_using falls back to NetworkX"
    return True


def _can_run_gnp(n=None, p=None, seed=None, directed=False, *, create_using=None, **kwargs):
    _ = n, p, seed, directed, kwargs
    return _can_run_random_common(create_using)


def gnp_random_graph(n, p, seed=None, directed=False, *, create_using=None):
    """G(n, p) sampled by rustworkx; a valid draw, not NetworkX's draw."""
    _reject_create_using(create_using)
    if p >= 1:
        return complete_graph(n, create_using=nx.DiGraph if directed else None)
    nodes = _nodes_list(n)
    if p <= 0 or p != p:
        return _wrap(_empty_container(directed, len(nodes)), nodes, directed=directed)
    if not isinstance(n, numbers.Integral):
        # NetworkX's sampler iterates ``range(n)``; fail the same way.
        raise TypeError(f"'{type(n).__name__}' object cannot be interpreted as an integer")
    _check_seed_policy(seed)
    kernel = rx.directed_gnp_random_graph if directed else rx.undirected_gnp_random_graph
    g = kernel(int(n), float(p), seed=_rx_seed(seed))
    return _wrap(g, nodes, directed=directed)


gnp_random_graph.can_run = _can_run_gnp
gnp_random_graph.should_run = _should_run_always


def fast_gnp_random_graph(n, p, seed=None, directed=False, *, create_using=None):
    """Same G(n, p) kernel as ``gnp_random_graph``.

    NetworkX's two names differ only in sampling algorithm, so on this backend
    the same seed produces the same graph under both names.
    """
    return gnp_random_graph(n, p, seed=seed, directed=directed, create_using=create_using)


fast_gnp_random_graph.can_run = _can_run_gnp
fast_gnp_random_graph.should_run = _should_run_always


def _can_run_gnm(n=None, m=None, seed=None, directed=False, *, create_using=None, **kwargs):
    _ = n, m, seed, directed, kwargs
    return _can_run_random_common(create_using)


def gnm_random_graph(n, m, seed=None, directed=False, *, create_using=None):
    """G(n, m) sampled by rustworkx; a valid draw, not NetworkX's draw."""
    _reject_create_using(create_using)
    if n == 1:
        return _wrap(_empty_container(directed, 1), range(1), directed=directed)
    # Raises TypeError for non-numeric ``n`` exactly like NetworkX's arithmetic.
    max_edges = n * (n - 1) if directed else n * (n - 1) / 2.0
    if m >= max_edges:
        return complete_graph(n, create_using=nx.DiGraph if directed else None)
    nodes = _nodes_list(n)
    k = len(nodes)
    if m <= 0:
        return _wrap(_empty_container(directed, k), nodes, directed=directed)
    if k == 0:
        # NetworkX's sampler would fail drawing from an empty node list.
        raise IndexError("Cannot choose from an empty sequence")
    _check_seed_policy(seed)
    kernel = rx.directed_gnm_random_graph if directed else rx.undirected_gnm_random_graph
    # NetworkX samples while edge_count < m, so a fractional m rounds up.
    g = kernel(k, math.ceil(m), seed=_rx_seed(seed))
    return _wrap(g, nodes, directed=directed)


gnm_random_graph.can_run = _can_run_gnm
gnm_random_graph.should_run = _should_run_always


def _can_run_dense_gnm(n=None, m=None, seed=None, *, create_using=None, **kwargs):
    _ = seed, kwargs
    reason = _can_run_random_common(create_using)
    if reason is not True:
        return reason
    try:
        if n is not None and n < 2:
            return "degenerate sizes fall back to NetworkX"
        if m is not None and (m <= 0 or not isinstance(m, numbers.Integral)):
            # NetworkX's exact-count sampler never terminates cleanly for
            # these; let it behave however it does.
            return "degenerate m falls back to NetworkX"
    except TypeError:
        pass  # non-numeric arguments raise inside NetworkX; let it
    return True


def dense_gnm_random_graph(n, m, seed=None, *, create_using=None):
    """Same G(n, m) distribution as ``gnm_random_graph``, undirected only."""
    _reject_create_using(create_using)
    mmax = n * (n - 1) // 2
    if m >= mmax:
        return complete_graph(n)
    if n == 1:
        return _wrap(_empty_container(False, 1), range(1), directed=False)
    nodes = _nodes_list(n)
    _check_seed_policy(seed)
    g = rx.undirected_gnm_random_graph(len(nodes), int(m), seed=_rx_seed(seed))
    return _wrap(g, nodes, directed=False)


dense_gnm_random_graph.can_run = _can_run_dense_gnm
dense_gnm_random_graph.should_run = _should_run_always


def _can_run_regular(d=None, n=None, seed=None, *, create_using=None, **kwargs):
    _ = d, n, seed, kwargs
    return _can_run_random_common(create_using)


def random_regular_graph(d, n, seed=None, *, create_using=None):
    """``d``-regular graph from the same pairing model NetworkX uses.

    rustworkx's kernel documents itself as based on NetworkX's
    ``random_regular_graph``, so only the RNG differs.
    """
    _reject_create_using(create_using)
    if (n * d) % 2 != 0:
        raise nx.NetworkXError("n * d must be even")
    if not 0 <= d < n:
        raise nx.NetworkXError("the 0 <= d < n inequality must be satisfied")
    _check_seed_policy(seed)
    g = rx.random_regular_graph(int(n), int(d), seed=_rx_seed(seed))
    return _wrap(g, range(int(n)), directed=False)


random_regular_graph.can_run = _can_run_regular
random_regular_graph.should_run = _should_run_always


def _can_run_sbm(
    sizes=None,
    p=None,
    nodelist=None,
    seed=None,
    directed=False,
    selfloops=False,
    sparse=True,
    **kwargs,
):
    _ = sizes, p, nodelist, seed, directed, selfloops, sparse, kwargs
    return _can_run_random_common(None)


def stochastic_block_model(
    sizes, p, nodelist=None, seed=None, directed=False, selfloops=False, sparse=True
):
    """SBM sampled by rustworkx with NetworkX's partition and block attributes.

    ``sparse`` only selects NetworkX's sampling algorithm, so it is ignored.
    The validations below mirror NetworkX's, message for message.
    """
    _ = sparse
    if len(sizes) != len(p):
        raise nx.NetworkXException("'sizes' and 'p' do not match.")
    for row in p:
        if len(p) != len(row):
            raise nx.NetworkXException("'p' must be a square matrix.")
    if not directed:
        p_transpose = [list(i) for i in zip(*p)]
        for rows in zip(p, p_transpose):
            for pair in zip(rows[0], rows[1]):
                if abs(pair[0] - pair[1]) > 1e-08:
                    raise nx.NetworkXException("'p' must be symmetric.")
    for row in p:
        for prob in row:
            if prob < 0 or prob > 1:
                raise nx.NetworkXException("Entries of 'p' not in [0,1].")
    if nodelist is not None:
        if len(nodelist) != sum(sizes):
            raise nx.NetworkXException("'nodelist' and 'sizes' do not match.")
        if len(nodelist) != len(set(nodelist)):
            raise nx.NetworkXException("nodelist contains duplicate.")
        labels = list(nodelist)
    else:
        labels = list(range(sum(sizes)))
    _check_seed_policy(seed)
    kernel = rx.directed_sbm_random_graph if directed else rx.undirected_sbm_random_graph
    g = kernel(
        [int(s) for s in sizes],
        np.asarray(p, dtype=float),
        bool(selfloops),
        seed=_rx_seed(seed),
    )
    out = _wrap(g, labels, directed=directed)
    size_cumsum = [sum(sizes[0:x]) for x in range(len(sizes) + 1)]
    partition = [
        set(labels[size_cumsum[x] : size_cumsum[x + 1]]) for x in range(len(size_cumsum) - 1)
    ]
    out.graph["partition"] = partition
    out.graph["name"] = "stochastic_block_model"
    for block_id, block_nodes in enumerate(partition):
        for node in block_nodes:
            out.node_attrs[node] = {"block": block_id}
    return out


stochastic_block_model.can_run = _can_run_sbm
stochastic_block_model.should_run = _should_run_always


def _can_run_geometric(
    n=None, radius=None, dim=2, pos=None, p=2, seed=None, *, pos_name="pos", **kwargs
):
    _ = n, radius, dim, p, seed, pos_name, kwargs
    reason = _can_run_random_common(None)
    if reason is not True:
        return reason
    if pos is not None:
        return "explicit pos falls back to NetworkX"
    return True


def random_geometric_graph(n, radius, dim=2, pos=None, p=2, seed=None, *, pos_name="pos"):
    """Random geometric graph with rustworkx-sampled positions.

    Positions land on each node under ``pos_name``, as NetworkX stores them.
    """
    if pos is not None:
        raise NotImplementedError(
            "nx-rustworkx random_geometric_graph does not support explicit pos"
        )
    nodes = _nodes_list(n)
    k = len(nodes)
    if k == 0:
        return _wrap(_empty_container(False), nodes, directed=False)
    _check_seed_policy(seed)
    g = rx.random_geometric_graph(k, float(radius), dim=int(dim), p=float(p), seed=_rx_seed(seed))
    out = _wrap(g, nodes, directed=False)
    index_to_node = out.index_to_node
    out.node_attrs.update(
        {index_to_node[i]: {pos_name: g.get_node_data(i)["pos"]} for i in range(k)}
    )
    return out


random_geometric_graph.can_run = _can_run_geometric
random_geometric_graph.should_run = _should_run_always


def _can_run_ba(n=None, m=None, seed=None, initial_graph=None, *, create_using=None, **kwargs):
    _ = n, m, seed, kwargs
    reason = _can_run_random_common(create_using)
    if reason is not True:
        return reason
    if initial_graph is not None:
        return "initial_graph falls back to NetworkX"
    return True


def barabasi_albert_graph(n, m, seed=None, initial_graph=None, *, create_using=None):
    """Barabasi-Albert growth from NetworkX's star seed, attached in Rust.

    rustworkx's default initial condition differs from NetworkX's, so pass
    NetworkX's ``star_graph(m)`` seed explicitly; the growth process is then
    the same model and only the RNG differs.
    """
    _reject_create_using(create_using)
    if initial_graph is not None:
        raise NotImplementedError(
            "nx-rustworkx barabasi_albert_graph does not support initial_graph"
        )
    if m < 1 or m >= n:
        raise nx.NetworkXError(
            # The en dash matches NetworkX's error text exactly.
            f"Barabási–Albert network must have m >= 1 and m < n, m = {m}, n = {n}"  # noqa: RUF001
        )
    _check_seed_policy(seed)
    star = rxgen.star_graph(int(m) + 1, multigraph=False)
    g = rx.barabasi_albert_graph(int(n), int(m), seed=_rx_seed(seed), initial_graph=star)
    return _wrap(g, range(g.num_nodes()), directed=False)


barabasi_albert_graph.can_run = _can_run_ba
barabasi_albert_graph.should_run = _should_run_always

GENERATORS = [
    "graph__new__",
    "digraph__new__",
    "empty_graph",
    "from_edgelist",
    "path_graph",
    "cycle_graph",
    "star_graph",
    "complete_graph",
    "barbell_graph",
    "lollipop_graph",
    "binomial_tree",
    "full_rary_tree",
    "karate_club_graph",
    "grid_2d_graph",
    "gnp_random_graph",
    "fast_gnp_random_graph",
    "gnm_random_graph",
    "dense_gnm_random_graph",
    "random_regular_graph",
    "stochastic_block_model",
    "random_geometric_graph",
    "barabasi_albert_graph",
]
