"""Native generators must return rustworkx-backed graphs NetworkX would build."""

from __future__ import annotations

import networkx as nx
import pytest

from nx_rustworkx import generators
from nx_rustworkx.convert import rustworkx_graph_to_nx
from nx_rustworkx.graph import RustworkxGraph


def assert_matches_networkx(name, *args, **kwargs):
    """Backend output, converted back, must equal NetworkX's exactly.

    NetworkX's own test harness applies the same strict comparison to every
    generator the backend claims, so this is the acceptance bar. Where the
    installed NetworkX rejects the arguments (semantics moved between 3.4 and
    3.6), the backend must reject them the same way.
    """
    ours = getattr(generators, name)
    orig = getattr(nx, name).orig_func
    try:
        expected = orig(*args, **kwargs)
    except Exception as exc:
        with pytest.raises(type(exc)):
            ours(*args, **kwargs)
        return
    got = ours(*args, **kwargs)
    assert isinstance(got, RustworkxGraph)
    converted = rustworkx_graph_to_nx(got)
    assert nx.utils.graphs_equal(converted, expected)


def assert_raises_like_networkx(name, *args, **kwargs):
    ours = getattr(generators, name)
    orig = getattr(nx, name).orig_func
    with pytest.raises(Exception) as expected:
        orig(*args, **kwargs)
    with pytest.raises(type(expected.value)):
        ours(*args, **kwargs)


SIZES = [0, 1, 2, 3, 8, 40]
NODE_ITERABLES = [[], ["a"], ["a", "b"], ["a", "b", "c", "d"], [(0, 1), (2, 3), 7]]


@pytest.mark.parametrize("name", ["path_graph", "cycle_graph", "star_graph", "complete_graph"])
@pytest.mark.parametrize("n", SIZES + NODE_ITERABLES)
@pytest.mark.parametrize("create_using", [None, nx.DiGraph])
def test_simple_generators_match(name, n, create_using):
    assert_matches_networkx(name, n, create_using)


@pytest.mark.parametrize("name", ["path_graph", "cycle_graph", "star_graph", "complete_graph"])
def test_simple_generators_reject_negative_n(name):
    assert_raises_like_networkx(name, -1)


@pytest.mark.parametrize("m1,m2", [(2, 0), (2, 3), (5, 1), (4, 4)])
def test_barbell_matches(m1, m2):
    assert_matches_networkx("barbell_graph", m1, m2)


@pytest.mark.parametrize("m1,m2", [(1, 2), (0, 0), (4, -1)])
def test_barbell_rejects_like_networkx(m1, m2):
    assert_raises_like_networkx("barbell_graph", m1, m2)


@pytest.mark.parametrize(
    "m,n",
    [(2, 0), (2, 3), (5, 1), (3, 4), ([1, 2, 3], "abc"), (["a", "b", "c"], 2), (3, "ab")],
)
def test_lollipop_matches(m, n):
    assert_matches_networkx("lollipop_graph", m, n)


@pytest.mark.parametrize(
    "m,n",
    [(1, 2), (4, -1), ([1, 2], [2, 3]), ([1, 1, 2], "ab"), ([1, 2, 3], 2)],
)
def test_lollipop_rejects_like_networkx(m, n):
    assert_raises_like_networkx("lollipop_graph", m, n)


@pytest.mark.parametrize("n", [0, 1, 2, 4, 5])
@pytest.mark.parametrize("create_using", [None, nx.DiGraph])
def test_binomial_tree_matches(n, create_using):
    assert_matches_networkx("binomial_tree", n, create_using)


@pytest.mark.parametrize("r,n", [(0, 0), (0, 5), (1, 5), (2, 0), (2, 1), (2, 15), (3, 20)])
@pytest.mark.parametrize("create_using", [None, nx.DiGraph])
def test_full_rary_tree_matches(r, n, create_using):
    assert_matches_networkx("full_rary_tree", r, n, create_using)


@pytest.mark.parametrize(
    "m,n",
    [(0, 0), (0, 3), (1, 1), (1, 5), (3, 4), (5, 5), (range(2), "ab"), (2, [10, 20])],
)
def test_grid_2d_matches(m, n):
    assert_matches_networkx("grid_2d_graph", m, n)


def test_grid_2d_periodic_and_directed_fall_back():
    assert generators.grid_2d_graph.can_run(3, 3, periodic=True) is not True
    assert generators.grid_2d_graph.can_run(3, 3, create_using=nx.DiGraph) is not True
    assert generators.grid_2d_graph.can_run(3, 3) is True
    # NetworkX treats a per-dimension tuple as periodic input; fall back for
    # any truthy value rather than reimplementing that parsing.
    assert generators.grid_2d_graph.can_run(3, 3, periodic=(False, False)) is not True


def test_karate_club_matches():
    got = generators.karate_club_graph()
    expected = nx.karate_club_graph.orig_func()
    assert isinstance(got, RustworkxGraph)
    assert nx.utils.graphs_equal(rustworkx_graph_to_nx(got), expected)
    assert got.graph["name"] == "Zachary's Karate Club"
    assert got.nodes[0]["club"] == "Mr. Hi"


@pytest.mark.parametrize(
    "name",
    [
        "path_graph",
        "cycle_graph",
        "star_graph",
        "complete_graph",
        "barbell_graph",
        "lollipop_graph",
        "binomial_tree",
        "full_rary_tree",
        "grid_2d_graph",
    ],
)
def test_multigraph_create_using_falls_back(name):
    func = getattr(generators, name)
    args = (
        (4, 3)
        if name in {"barbell_graph", "lollipop_graph", "full_rary_tree", "grid_2d_graph"}
        else (4,)
    )
    assert func.can_run(*args, create_using=nx.MultiGraph) is not True
    with pytest.raises(nx.NetworkXError):
        func(*args, create_using=nx.MultiGraph)


def test_generator_dispatch_returns_backend_graph():
    """Explicit backend= must produce a native graph for the named generators."""
    G = nx.path_graph(10, backend="rustworkx")
    assert isinstance(G, RustworkxGraph)
    H = nx.complete_graph(6, create_using=nx.DiGraph, backend="rustworkx")
    assert isinstance(H, RustworkxGraph)
    assert H.is_directed()


def test_generator_priority_uses_kernels():
    nx.config.backend_priority.generators = ["rustworkx"]
    try:
        G = nx.karate_club_graph()
        assert isinstance(G, RustworkxGraph)
        H = nx.grid_2d_graph(3, 4)
        assert isinstance(H, RustworkxGraph)
        assert (0, 0) in H
    finally:
        nx.config.backend_priority.generators = []


def test_generated_graph_supports_mutation():
    """Kernel containers report multigraph=True; add_edge must still replace."""
    G = generators.path_graph(4)
    G.add_edge(0, 1, weight=7)  # existing edge: replace, not parallel
    assert G.number_of_edges() == 3
    assert G[0][1] == {"weight": 7}
    G.add_edge(0, 3)
    assert G.number_of_edges() == 4
    G.remove_node(3)
    assert G.number_of_nodes() == 3


def test_generated_graph_flows_into_algorithms():
    G = generators.cycle_graph(50)
    lengths = nx.single_source_shortest_path_length(G, 0, backend="rustworkx")
    assert lengths[25] == 25


# --- random generators ------------------------------------------------------

RANDOM_NAMES = [
    "gnp_random_graph",
    "fast_gnp_random_graph",
    "gnm_random_graph",
    "dense_gnm_random_graph",
]


def _rng(seed):
    return nx.utils.create_py_random_state(seed)


@pytest.fixture
def native_seeded():
    nx.config.backends.rustworkx.native_seeded_generators = True
    yield
    nx.config.backends.rustworkx.native_seeded_generators = False


def test_native_seeded_generators_defaults_off():
    assert nx.config.backends.rustworkx.native_seeded_generators is False


@pytest.mark.parametrize("name", RANDOM_NAMES)
def test_unseeded_runs_natively(name):
    G = getattr(generators, name)(30, 0.2 if "gnp" in name else 40, seed=_rng(None))
    assert isinstance(G, RustworkxGraph)
    assert G.number_of_nodes() == 30


@pytest.mark.parametrize("name", RANDOM_NAMES)
def test_seeded_raises_without_opt_in(name):
    with pytest.raises(NotImplementedError, match="native_seeded_generators"):
        getattr(generators, name)(30, 0.2 if "gnp" in name else 40, seed=_rng(42))


@pytest.mark.parametrize("name", RANDOM_NAMES)
def test_seeded_is_deterministic_with_opt_in(name, native_seeded):
    m_or_p = 0.3 if "gnp" in name else 60
    A = getattr(generators, name)(40, m_or_p, seed=_rng(42))
    B = getattr(generators, name)(40, m_or_p, seed=_rng(42))
    assert {tuple(sorted(e)) for e in A.edges} == {tuple(sorted(e)) for e in B.edges}
    assert A.number_of_nodes() == 40


def test_gnp_and_fast_gnp_share_a_kernel(native_seeded):
    A = generators.gnp_random_graph(40, 0.3, seed=_rng(42))
    B = generators.fast_gnp_random_graph(40, 0.3, seed=_rng(42))
    assert {tuple(sorted(e)) for e in A.edges} == {tuple(sorted(e)) for e in B.edges}


def test_gnm_produces_exactly_m_edges():
    for directed in (False, True):
        G = generators.gnm_random_graph(30, 80, seed=_rng(None), directed=directed)
        assert G.number_of_edges() == 80
        assert G.is_directed() is directed


def test_directed_gnp_runs_natively():
    G = generators.gnp_random_graph(30, 0.2, seed=_rng(None), directed=True)
    assert isinstance(G, RustworkxGraph)
    assert G.is_directed()


@pytest.mark.parametrize(
    "name,args",
    [
        ("gnp_random_graph", (5, 1.5)),
        ("gnp_random_graph", (5, 0.0)),
        ("gnp_random_graph", (5, -1.0)),
        ("fast_gnp_random_graph", (4, 2.0)),
        ("gnm_random_graph", (4, 100)),
        ("gnm_random_graph", (3, 100)),
        ("gnm_random_graph", (1, 3)),
        ("gnm_random_graph", (5, 0)),
        ("dense_gnm_random_graph", (4, 100)),
    ],
)
def test_random_boundaries_are_deterministic_and_exact(name, args):
    """p and m boundaries bypass sampling, so they must match NetworkX exactly."""
    got = getattr(generators, name)(*args, seed=_rng(None))
    expected = getattr(nx, name).orig_func(*args, seed=_rng(None))
    assert nx.utils.graphs_equal(rustworkx_graph_to_nx(got), expected)


def test_priority_dispatch_seeded_keeps_networkx_stream():
    """Seeded calls under priority fall back to NetworkX's sampler but still
    land in a native graph through empty_graph dispatch."""
    nx.config.backend_priority.generators = ["rustworkx"]
    try:
        G = nx.gnp_random_graph(30, 0.2, seed=42)
    finally:
        nx.config.backend_priority.generators = []
    expected = nx.gnp_random_graph(30, 0.2, seed=42)
    assert isinstance(G, RustworkxGraph)
    assert {tuple(sorted(e)) for e in G.edges} == {tuple(sorted(e)) for e in expected.edges()}


def test_priority_dispatch_unseeded_runs_kernel():
    nx.config.backend_priority.generators = ["rustworkx"]
    try:
        G = nx.gnp_random_graph(30, 0.2)
    finally:
        nx.config.backend_priority.generators = []
    assert isinstance(G, RustworkxGraph)


def test_explicit_backend_seeded_raises_with_opt_in_hint():
    with pytest.raises(NotImplementedError) as excinfo:
        nx.gnp_random_graph(30, 0.2, seed=42, backend="rustworkx")
    chain = str(excinfo.value) + str(excinfo.value.__cause__ or "")
    assert "native_seeded_generators" in chain


def test_explicit_backend_unseeded_returns_native():
    G = nx.gnp_random_graph(30, 0.2, backend="rustworkx")
    assert isinstance(G, RustworkxGraph)


def test_explicit_backend_seeded_with_opt_in(native_seeded):
    G = nx.gnp_random_graph(30, 0.2, seed=42, backend="rustworkx")
    assert isinstance(G, RustworkxGraph)
    H = nx.gnp_random_graph(30, 0.2, seed=42, backend="rustworkx")
    assert {tuple(sorted(e)) for e in G.edges} == {tuple(sorted(e)) for e in H.edges}


@pytest.mark.parametrize("name", RANDOM_NAMES)
def test_random_generators_decline_under_parity_harness(name):
    """NetworkX's test suite strict-compares generator output; random samples
    cannot match its RNG stream, so can_run must decline while it runs."""
    dispatchable = nx.utils.backends._dispatchable
    assert dispatchable._is_testing is False
    func = getattr(generators, name)
    dispatchable._is_testing = True
    try:
        assert func.can_run(30, 40) is not True
    finally:
        dispatchable._is_testing = False
    assert func.can_run(30, 40) is True


@pytest.mark.parametrize("name", RANDOM_NAMES)
def test_random_generators_decline_create_using(name):
    func = getattr(generators, name)
    assert func.can_run(30, 40, create_using=nx.Graph) is not True


def test_dense_gnm_declines_degenerate_arguments():
    assert generators.dense_gnm_random_graph.can_run(1, 5) is not True
    assert generators.dense_gnm_random_graph.can_run(10, 0) is not True
    assert generators.dense_gnm_random_graph.can_run(10, 2.5) is not True
    assert generators.dense_gnm_random_graph.can_run(10, 5) is True


# --- model-family random generators ----------------------------------------

# name -> (args, kwargs) for a representative sampling call.
MODEL_CALLS = {
    "random_regular_graph": ((3, 20), {}),
    "stochastic_block_model": (([5, 5], [[0.8, 0.1], [0.1, 0.8]]), {}),
    "random_geometric_graph": ((20, 0.4), {}),
    "barabasi_albert_graph": ((20, 3), {}),
}


@pytest.mark.parametrize("name", sorted(MODEL_CALLS))
def test_model_generators_unseeded_run_natively(name):
    args, kwargs = MODEL_CALLS[name]
    G = getattr(generators, name)(*args, seed=_rng(None), **kwargs)
    assert isinstance(G, RustworkxGraph)
    expected_nodes = 10 if name == "stochastic_block_model" else 20
    assert G.number_of_nodes() == expected_nodes


@pytest.mark.parametrize("name", sorted(MODEL_CALLS))
def test_model_generators_seeded_gate(name):
    args, kwargs = MODEL_CALLS[name]
    with pytest.raises(NotImplementedError, match="native_seeded_generators"):
        getattr(generators, name)(*args, seed=_rng(42), **kwargs)


@pytest.mark.parametrize("name", sorted(MODEL_CALLS))
def test_model_generators_deterministic_with_opt_in(name, native_seeded):
    args, kwargs = MODEL_CALLS[name]
    A = getattr(generators, name)(*args, seed=_rng(42), **kwargs)
    B = getattr(generators, name)(*args, seed=_rng(42), **kwargs)
    assert {tuple(sorted(e)) for e in A.edges} == {tuple(sorted(e)) for e in B.edges}


@pytest.mark.parametrize("name", sorted(MODEL_CALLS))
def test_model_generators_decline_under_parity_harness(name):
    args, kwargs = MODEL_CALLS[name]
    dispatchable = nx.utils.backends._dispatchable
    func = getattr(generators, name)
    dispatchable._is_testing = True
    try:
        assert func.can_run(*args, **kwargs) is not True
    finally:
        dispatchable._is_testing = False
    assert func.can_run(*args, **kwargs) is True


def test_random_regular_is_regular():
    G = generators.random_regular_graph(4, 30, seed=_rng(None))
    assert all(degree == 4 for _, degree in G.degree)


@pytest.mark.parametrize("d,n", [(3, 3), (-1, 5), (5, 4), (0, 0)])
def test_random_regular_rejects_like_networkx(d, n):
    assert_raises_like_networkx("random_regular_graph", d, n)


def test_random_regular_d_zero_gives_isolates():
    G = generators.random_regular_graph(0, 7, seed=_rng(None))
    assert G.number_of_nodes() == 7
    assert G.number_of_edges() == 0


def test_sbm_sets_networkx_attributes():
    G = generators.stochastic_block_model([3, 4], [[0.9, 0.2], [0.2, 0.8]], seed=_rng(None))
    assert G.graph["partition"] == [{0, 1, 2}, {3, 4, 5, 6}]
    assert G.graph["name"] == "stochastic_block_model"
    assert G.nodes[0]["block"] == 0
    assert G.nodes[5]["block"] == 1


def test_sbm_nodelist_and_deterministic_probabilities():
    G = generators.stochastic_block_model(
        [2, 2], [[1.0, 0.0], [0.0, 1.0]], nodelist=list("abcd"), seed=_rng(None)
    )
    assert G.graph["partition"] == [{"a", "b"}, {"c", "d"}]
    assert sorted(tuple(sorted(e)) for e in G.edges) == [("a", "b"), ("c", "d")]


def test_sbm_full_probability_matches_networkx_exactly():
    got = generators.stochastic_block_model([4], [[1.0]], seed=_rng(None), selfloops=True)
    expected = nx.stochastic_block_model.orig_func([4], [[1.0]], seed=_rng(1), selfloops=True)
    assert nx.utils.graphs_equal(rustworkx_graph_to_nx(got), expected)


def test_sbm_directed_accepts_asymmetric_p():
    G = generators.stochastic_block_model(
        [2, 3], [[0.5, 0.1], [0.9, 0.5]], seed=_rng(None), directed=True
    )
    assert G.is_directed()


@pytest.mark.parametrize(
    "args,kwargs",
    [
        (([2, 2], [[0.5, 0.1], [0.9, 0.5]]), {}),
        (([2], [[0.5], [0.5]]), {}),
        (([2, 2], [[0.5, 2.0], [2.0, 0.5]]), {}),
        (([2, 2], [[0.5, 0.1], [0.1, 0.5]]), {"nodelist": [1, 2, 3]}),
        (([2, 2], [[0.5, 0.1], [0.1, 0.5]]), {"nodelist": [1, 1, 2, 3]}),
    ],
)
def test_sbm_rejects_like_networkx(args, kwargs):
    assert_raises_like_networkx("stochastic_block_model", *args, **kwargs)


def test_geometric_stores_positions():
    G = generators.random_geometric_graph(15, 0.3, seed=_rng(None))
    assert len(G.nodes[0]["pos"]) == 2
    H = generators.random_geometric_graph(6, 0.4, dim=3, seed=_rng(None), pos_name="coords")
    assert len(H.nodes[0]["coords"]) == 3


def test_geometric_explicit_pos_falls_back():
    assert generators.random_geometric_graph.can_run(5, 0.5, pos={0: [0, 0]}) is not True
    with pytest.raises(NotImplementedError):
        generators.random_geometric_graph(5, 0.5, pos={0: [0, 0]}, seed=_rng(None))


@pytest.mark.parametrize("n,m", [(20, 2), (10, 3), (5, 1), (30, 5), (4, 3)])
def test_barabasi_albert_edge_count_matches_process(n, m):
    """The star seed fixes the edge count regardless of RNG."""
    got = generators.barabasi_albert_graph(n, m, seed=_rng(None))
    expected = nx.barabasi_albert_graph.orig_func(n, m, seed=_rng(1))
    assert got.number_of_nodes() == expected.number_of_nodes()
    assert got.number_of_edges() == expected.number_of_edges()


@pytest.mark.parametrize("n,m", [(5, 0), (5, 5), (3, 4)])
def test_barabasi_albert_rejects_like_networkx(n, m):
    assert_raises_like_networkx("barabasi_albert_graph", n, m)


def test_barabasi_albert_initial_graph_falls_back():
    assert generators.barabasi_albert_graph.can_run(10, 3, initial_graph=nx.Graph()) is not True
    with pytest.raises(NotImplementedError):
        generators.barabasi_albert_graph(10, 3, seed=_rng(None), initial_graph=nx.Graph())
